/** @odoo-module **/

import * as attendanceMenuModule from "@hr_attendance/components/attendance_menu/attendance_menu";
import { patch } from "@web/core/utils/patch";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Component, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";

function euclideanDistance(point1, point2) {
    return Math.sqrt(Math.pow(point1.x - point2.x, 2) + Math.pow(point1.y - point2.y, 2));
}

function getEAR(eye) {
    const v1 = euclideanDistance(eye[1], eye[5]);
    const v2 = euclideanDistance(eye[2], eye[4]);
    const h = euclideanDistance(eye[0], eye[3]);
    return (v1 + v2) / (2.0 * h);
}

let _faceApiScriptPromise = null;
let _faceApiModelsPromise = null;

async function preloadFaceApiScript() {
    if (window.faceapi) return;
    if (!_faceApiScriptPromise) {
        _faceApiScriptPromise = new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = '/attendance_planning/static/src/lib/face-api.js';
            script.onload = () => resolve();
            script.onerror = () => {
                _faceApiScriptPromise = null;
                reject(new Error("Failed to load face-api.js"));
            };
            document.head.appendChild(script);
        });
    }
    return _faceApiScriptPromise;
}

async function preloadFaceApiModels() {
    if (!_faceApiModelsPromise) {
        const modelPath = '/attendance_planning/static/src/models';
        _faceApiModelsPromise = Promise.all([
            faceapi.nets.tinyFaceDetector.loadFromUri(modelPath),
            faceapi.nets.faceLandmark68Net.loadFromUri(modelPath),
            faceapi.nets.faceRecognitionNet.loadFromUri(modelPath),
        ]).catch((e) => {
            _faceApiModelsPromise = null;
            throw e;
        });
    }
    return _faceApiModelsPromise;
}

export class FaceVerificationDialog extends Component {
    setup() {
        this.videoRef = useRef("videoElement");
        this.orm = useService("orm");

        this.state = useState({
            statusMessage: "Downloading AI Engine...",
            isProcessing: false,
        });

        this.stream = null;
        this.scanInterval = null;
        this.hasPunched = false;
        this._capturedPhotoBase64 = null;
        this._myDescriptorCache = null;
        this._lastMatchDistance = null;

        onMounted(async () => {
            // FIX #3: wrap the whole startup chain. If script/model load
            // or the camera itself throws unexpectedly (anything not
            // already caught inside startCamera()'s own try/catch), the
            // dialog must not sit open forever holding the punch lock.
            try {
                await this.injectFaceApiScript();
                await this.loadModels();
                await this.startCamera();
            } catch (e) {
                this.orm.call("hr.employee", "log_client_event",
                    ["checkin_checkout", "error", "Face verification dialog failed to start", { message: String(e) }]
                ).catch(() => {});
                this.state.statusMessage = "Something went wrong starting the camera. Please try again.";
                this.stopCamera();
                if (this.props.releaseLock) this.props.releaseLock();
                setTimeout(() => this.props.close(), 1500);
            }
        });

        onWillUnmount(() => {
            this.stopCamera();
            // FIX #3: release the punch lock on ANY dismissal path (user
            // closes the dialog manually, Escape key, clicking outside,
            // etc.), not just the paths that already call releaseLock()
            // explicitly below. Safe to call twice — it just clears a
            // timeout and flips a flag.
            if (this.props.releaseLock) this.props.releaseLock();
        });
    }

    async injectFaceApiScript() {
        return preloadFaceApiScript();
    }

    async loadModels() {
        this.state.statusMessage = "Loading AI Models...";
        await preloadFaceApiModels();
        this.state.statusMessage = "Ready. Please look at the camera.";
    }

    async startCamera() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
            if (this.videoRef.el) {
                this.videoRef.el.srcObject = this.stream;
                this.videoRef.el.addEventListener('play', () => this.startScanning());
            }
        } catch (err) {
            this.orm.call("hr.employee", "log_client_event",
                ["checkin_checkout", "error", "Camera access denied during punch", { name: err.name, message: err.message }]
            ).catch(() => {});
            this.state.statusMessage = "Camera access denied.";
            // FIX #3: this used to just set a status message and leave the
            // dialog open with the lock held for up to 60s. Now it closes
            // cleanly like every other failure path.
            this.stopCamera();
            if (this.props.releaseLock) this.props.releaseLock();
            setTimeout(() => this.props.close(), 1500);
        }
    }

    /**
     * Reads a small 50x50 sample of the current video frame and returns
     * an average brightness value from 0 (black) to 255 (white).
     * Used only for diagnostic logging on a failed match — cheap to run,
     * never blocks the scanning loop, and safely returns null on any error.
     */
    _estimateBrightness(videoEl) {
        try {
            const canvas = document.createElement('canvas');
            canvas.width = 50;
            canvas.height = 50;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(videoEl, 0, 0, 50, 50);
            const data = ctx.getImageData(0, 0, 50, 50).data;
            let total = 0;
            for (let i = 0; i < data.length; i += 4) {
                total += (data[i] + data[i + 1] + data[i + 2]) / 3;
            }
            return Math.round(total / (data.length / 4));
        } catch (e) {
            return null;
        }
    }

    async startScanning() {
        if (this.scanInterval) return;

        // Fetch the registered face descriptor ONCE, right when scanning
        // starts. It never changes during a scan, so we cache it here and
        // reuse it on every 200ms tick below, instead of re-fetching it
        // from the server on every single tick (which was hammering the
        // server on every failed match attempt).
        this._myDescriptorCache = await this.orm.call("hr.employee", "get_my_face_descriptor", []);

        if (!this._myDescriptorCache) {
            this.orm.call("hr.employee", "log_client_event",
                ["checkin_checkout", "warning", "Employee attempted punch with no face registered"]
            ).catch(() => {});
            this.state.statusMessage = "No face registered for your account. Please register your face first, or contact HR.";
            this.stopCamera();
            if (this.props.releaseLock) this.props.releaseLock();
            setTimeout(() => this.props.close(), 2000);
            return;
        }

        // The geo check runs independently, in parallel with face
        // scanning. Without this, if geo fails quickly, the face scanner
        // has no idea and keeps trying to match a face forever — wasting
        // the employee's time/battery and flooding the log with
        // "did not match" warnings for a punch that could never succeed
        // anyway. As soon as geo resolves as blocked, stop scanning
        // immediately instead of waiting for a (useless) face match first.
        this.props.geoCheckPromise.then((geoResult) => {
            if (this.hasPunched || this._geoFailHandled) return; // already handled via another path, ignore
            if (!geoResult || !geoResult.allowed) {
                this._geoFailHandled = true;
                this.orm.call("hr.employee", "log_client_event",
                    ["checkin_checkout", "warning", "Geo/location check blocked punch — stopped face scanning early",
                     { message: geoResult?.message }]
                ).catch(() => {});
                this.state.statusMessage = " " + (geoResult?.message || "You are outside the allowed office location.");
                this.stopCamera();
                if (this.props.releaseLock) this.props.releaseLock();
                setTimeout(() => this.props.close(), 1500);
            }
        }).catch(() => {});

        // This interval just watches the camera locally, 5 times a second,
        // to detect when a face appears in frame. This part is intentional
        // and lightweight — it does NOT call the server on every tick
        // (that part was removed above). Do not remove this interval.
        this.scanInterval = setInterval(async () => {
            if (this.state.isProcessing) return;

            const videoEl = this.videoRef.el;
            if (!videoEl || videoEl.readyState < 2 || !videoEl.videoWidth || !videoEl.videoHeight) {
                return;
            }

            let detection;
            try {
                detection = await faceapi.detectSingleFace(
                    videoEl,
                    new faceapi.TinyFaceDetectorOptions({ inputSize: 320, scoreThreshold: 0.5 })
                ).withFaceLandmarks().withFaceDescriptor();
            } catch (e) {
                console.warn("Face detection skipped this frame:", e);
                return;
            }

            if (detection) {
                this.state.isProcessing = true;
                this.state.statusMessage = "Face detected! Verifying...";

                const isMatch = await this.verifyWithDatabase(detection.descriptor);

                if (isMatch) {
                    if (!this.hasPunched) {
                        this.hasPunched = true;
                        this.state.isProcessing = true;
                        this.state.statusMessage = "Verifying location...";

                        this._capturedPhotoBase64 = this.capturePhotoBase64();

                        const geoResult = await this.props.geoCheckPromise;

                        if (!geoResult || !geoResult.allowed) {
                            this.state.statusMessage = "❌ " + (geoResult?.message || "You are outside the allowed office location.");
                            console.warn('Geo check failed:', geoResult?.message);
                            this.orm.call("hr.employee", "log_client_event",
                                ["checkin_checkout", "warning", "Geo/location check blocked punch",
                                 { message: geoResult?.message }]
                            ).catch(() => {});
                            this.stopCamera();
                            if (this.props.releaseLock) this.props.releaseLock();
                            setTimeout(() => this.props.close(), 1500);
                            return;
                        }

                        this.state.statusMessage = "✅ Identity Verified! Recording...";
                        this.stopCamera();

                        (async () => {
                            const photoBase64 = this._capturedPhotoBase64;

                            if (photoBase64) {
                                let staged = false;
                                for (let i = 0; i < 2 && !staged; i++) {
                                    try {
                                        await this.orm.call(
                                            'hr.employee',
                                            'stage_attendance_data',
                                            [photoBase64, geoResult.zone_id || false]
                                        );
                                        staged = true;
                                    } catch (e) {
                                        console.warn(`Stage attempt ${i + 1} failed:`, e);
                                    }
                                }

                                if (!staged) {
                                    console.error("❌ Critical: Failed to stage photo after 2 attempts.");
                                    this.orm.call("hr.employee", "log_client_event",
                                        ["checkin_checkout", "error", "Photo staging failed after 2 retries — punch may be missing photo"]
                                    ).catch(() => {});
                                }
                            }

                            if (this.props.onSuccess) {
                                await this.props.onSuccess();
                            }

                            if (this.props.releaseLock) this.props.releaseLock();
                            this.props.close();
                        })();
                    }
                    return;
                } else {
                    // Throttle this log to once every 3 seconds. The scan
                    // loop retries every ~200-400ms, so a genuine ongoing
                    // mismatch (bad lighting, wrong angle, still adjusting)
                    // would otherwise flood the log with 10-15 near-identical
                    // lines per attempt. One line every few seconds is
                    // enough to diagnose the issue without the noise.
                    const now = Date.now();
                    if (!this._lastMismatchLogAt || now - this._lastMismatchLogAt > 3000) {
                        this._lastMismatchLogAt = now;
                        const brightness = this._estimateBrightness(videoEl);
                        this.orm.call("hr.employee", "log_client_event",
                            ["checkin_checkout", "warning", "Live face did not match registered profile", {
                                distance: this._lastMatchDistance,
                                detectionConfidence: detection.detection.score,
                                faceBoxWidth: Math.round(detection.detection.box.width),
                                videoWidth: videoEl.videoWidth,
                                videoHeight: videoEl.videoHeight,
                                estimatedBrightness: brightness,
                            }]
                        ).catch(() => {});
                    }
                    this.state.statusMessage = "❌ Face does not match profile.";
                    this.state.isProcessing = false;
                }
            }
        }, 200);
    }

    async verifyWithDatabase(liveDescriptor) {
        try {
            const myDescriptor = this._myDescriptorCache;
            if (!myDescriptor) {
                // FIX: reset stale distance — otherwise the throttled
                // mismatch log above could report a distance value left
                // over from a previous tick/session as if it were current.
                this._lastMatchDistance = null;
                this.orm.call("hr.employee", "log_client_event",
                    ["checkin_checkout", "warning", "Employee attempted punch with no face registered"]
                ).catch(() => {});
                this.state.statusMessage = "No face registered for your account!";
                return false;
            }
            const arr = new Float32Array(JSON.parse(myDescriptor));
            const labeledDescriptors = [new faceapi.LabeledFaceDescriptors("CurrentUser", [arr])];
            const faceMatcher = new faceapi.FaceMatcher(labeledDescriptors, 0.55);

            const bestMatch = faceMatcher.findBestMatch(liveDescriptor);
            const isMatch = bestMatch.label === "CurrentUser";

            // Store the distance so the mismatch-logging block above can
            // read it. This is the actual number behind the pass/fail
            // decision (lower = more similar faces).
            this._lastMatchDistance = bestMatch.distance;

            // FIX #2: only log here on an actual SUCCESSFUL match (fires
            // once per session, since `hasPunched` gates further attempts).
            // The failure case used to log unconditionally on every single
            // ~200ms tick — duplicating the already-throttled "Live face
            // did not match registered profile" log above and defeating
            // the whole point of that 3-second throttle. Mismatches are
            // now only logged there.
            if (isMatch) {
                this.orm.call("hr.employee", "log_client_event",
                    ["checkin_checkout", "info", "Face match distance", { distance: bestMatch.distance, matched: true }]
                ).catch(() => {});
            }
            return isMatch;
        } catch (error) {
            // FIX: reset stale distance on this error path too.
            this._lastMatchDistance = null;
            this.orm.call("hr.employee", "log_client_event",
                ["checkin_checkout", "error", "Face verification against DB failed", { message: String(error) }]
            ).catch(() => {});
            return false;
        }
    }

    capturePhotoBase64() {
        try {
            const video = this.videoRef.el;
            if (!video || !video.videoWidth || !video.videoHeight) {
                return null;
            }
            const canvas = document.createElement('canvas');

            const maxWidth = 480;
            const scale = Math.min(1, maxWidth / video.videoWidth);
            canvas.width = Math.round(video.videoWidth * scale);
            canvas.height = Math.round(video.videoHeight * scale);

            canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
            const dataUrl = canvas.toDataURL('image/jpeg', 0.6);
            const base64 = dataUrl.split(',')[1];
            if (!base64 || base64.length < 100) {
                return null;
            }
            return base64;
        } catch (e) {
            return null;
        }
    }

    stopCamera() {
        if (this.scanInterval) clearInterval(this.scanInterval);
        if (this.stream) this.stream.getTracks().forEach(track => track.stop());
    }
}
FaceVerificationDialog.template = "attendance_planning.FaceVerificationPopup";
FaceVerificationDialog.components = { Dialog };

const ActualAttendanceMenu = attendanceMenuModule.systrayAttendance?.Component || attendanceMenuModule.systrayAttendance;

if (ActualAttendanceMenu) {
    patch(ActualAttendanceMenu.prototype, {
        setup() {
            super.setup(...arguments);
            this.dialogService = useService("dialog");
            this.orm = useService("orm");
            this.notificationService = useService("notification");
            this._punchInProgress = false;

            (async () => {
                try {
                    await preloadFaceApiScript();
                    await preloadFaceApiModels();
                } catch (e) {
                }
            })();
        },

        async signInOut() {
            if (this._punchInProgress) {
                this.orm.call("hr.employee", "log_client_event",
                    ["checkin_checkout", "warning", "Button clicked again while a punch was already in progress — ignored"]
                ).catch(() => {});
                return;
            }
            this._punchInProgress = true;

            const stateBeforeClick = (this.employee && this.employee.attendance_state) || 'unknown';
            this.orm.call("hr.employee", "log_client_event",
                ["checkin_checkout", "info", "Check-in/Check-out button clicked",
                 { state_before_click: stateBeforeClick }]
            ).catch(() => {});

            // ── DATABASE SYNC 1: Read actual status before punch ──
            try {
                if (this.employee && this.employee.id) {
                    const [fresh] = await this.orm.read(
                        "hr.employee",
                        [this.employee.id],
                        ["attendance_state", "last_attendance_id"]
                    );
                    if (fresh) {
                        Object.assign(this.employee, fresh);
                    }
                }
            } catch (e) {
                console.warn("Could not refresh employee attendance state before punch:", e);
            }

            let currentState = 'checked_out';
            if (this.employee && this.employee.attendance_state) {
                currentState = this.employee.attendance_state;
            } else if (this.attendanceService && this.attendanceService.isCheckedIn) {
                currentState = 'checked_in';
            } else if (this.attendance && this.attendance.attendance_state) {
                currentState = this.attendance.attendance_state;
            }

            const geoCheckPromise = (async () => {
                try {
                    const isBypass = await this.orm.call('hr.attendance', 'is_geo_bypass_employee', []);
                    if (isBypass) {
                        return { allowed: true, zone_id: false };
                    }
                } catch (e) {
                    console.warn("Could not fetch bypass status, proceeding with normal GPS check.");
                }

                let latitude = null;
                let longitude = null;

                try {
                    const position = await new Promise((resolve, reject) => {
                        navigator.geolocation.getCurrentPosition(resolve, reject, {
                            timeout: 15000,
                            enableHighAccuracy: false,
                            maximumAge: 30000,
                        });
                    });
                    latitude = position.coords.latitude;
                    longitude = position.coords.longitude;
                } catch (e) {
                    this.orm.call("hr.employee", "log_client_event",
                        ["checkin_checkout", "warning", "Browser location/GPS denied or timed out",
                         { code: e.code, message: e.message }]
                    ).catch(() => {});
                    return {
                        allowed: false,
                        message: "Location access is required for attendance. Please allow location and try again.",
                    };
                }

                try {
                    const result = await this.orm.call(
                        'hr.attendance',
                        'check_employee_geo_allowed',
                        [latitude, longitude]
                    );

                    if (!result || (typeof result === 'object' && !result.allowed) || result === false) {
                        return {
                            allowed: false,
                            message: (result && result.message) ? result.message : "You are outside the allowed office location.",
                        };
                    }

                    let zoneId = false;
                    if (result && result.zone_id) {
                        zoneId = result.zone_id;
                    } else if (result && result.id) {
                        zoneId = result.id;
                    }

                    return { allowed: true, zone_id: zoneId };
                } catch (e) {
                    this.orm.call("hr.employee", "log_client_event",
                        ["checkin_checkout", "error", "check_employee_geo_allowed RPC call failed",
                         { message: String(e) }]
                    ).catch(() => {});
                    return {
                        allowed: false,
                        message: "Could not verify your location. Please try again.",
                    };
                }
            })();

            const safetyUnlock = setTimeout(() => {
                this._punchInProgress = false;
            }, 60000);

            const releaseLock = () => {
                clearTimeout(safetyUnlock);
                this._punchInProgress = false;
            };

            this.dialogService.add(FaceVerificationDialog, {
                attendanceState: currentState,
                geoCheckPromise: geoCheckPromise,
                notificationService: this.notificationService,
                releaseLock: releaseLock,
                onSuccess: async () => {
                    // Trigger Native Punch securely
                    try {
                        await super.signInOut();
                        this.orm.call("hr.employee", "log_client_event",
                            ["checkin_checkout", "info", "Punch completed successfully",
                             { previous_state: currentState }]
                        ).catch(() => {});
                    } catch (e) {
                        console.error("Native punch failed:", e);
                        this.orm.call("hr.employee", "log_client_event",
                            ["checkin_checkout", "error", "Native attendance punch (super.signInOut) failed",
                             { message: String(e) }]
                        ).catch(() => {});
                        if (this.notificationService) {
                            this.notificationService.add(
                                "Couldn't record your attendance — your session may already be open. Please refresh the page and try again.",
                                { type: "danger" }
                            );
                        }
                        throw e;
                    }

                    // ── DATABASE SYNC 2: Force UI to update color immediately after punch ──
                    try {
                        if (this.employee && this.employee.id) {
                            const [fresh] = await this.orm.read(
                                "hr.employee",
                                [this.employee.id],
                                ["attendance_state", "last_attendance_id"]
                            );
                            if (fresh) {
                                Object.assign(this.employee, fresh);
                            }
                        }
                    } catch (e) {
                        console.warn("Could not refresh employee attendance state after punch:", e);
                    }

                    if (currentState === 'checked_in') {
                        if (typeof window.checkLateCheckout === 'function') {
                            setTimeout(window.checkLateCheckout, 1000);
                        }
                    }
                },
            });
        }
    });
}