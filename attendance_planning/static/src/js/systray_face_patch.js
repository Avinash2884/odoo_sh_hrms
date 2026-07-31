/** @odoo-module **/

import * as attendanceMenuModule from "@hr_attendance/components/attendance_menu/attendance_menu";
import { patch } from "@web/core/utils/patch";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Component, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";

// ---> Math functions to measure the eye blink
function euclideanDistance(point1, point2) {
    return Math.sqrt(Math.pow(point1.x - point2.x, 2) + Math.pow(point1.y - point2.y, 2));
}

function getEAR(eye) {
    const v1 = euclideanDistance(eye[1], eye[5]);
    const v2 = euclideanDistance(eye[2], eye[4]);
    const h = euclideanDistance(eye[0], eye[3]);
    return (v1 + v2) / (2.0 * h);
}

// Module-level cache so the face-api script + AI models are only ever
// loaded ONCE per page session, not on every single click.
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
        this.isEyesClosed = false;

        // ---> Stores the captured photo so the async save step (which runs
        // after the camera is already stopped) can still access it.
        this._capturedPhotoBase64 = null;

        onMounted(async () => {
            await this.injectFaceApiScript();
            await this.loadModels();
            await this.startCamera();
        });

        onWillUnmount(() => {
            this.stopCamera();
        });
    }

    async injectFaceApiScript() {
        return preloadFaceApiScript();
    }

    async loadModels() {
        if (!_faceApiModelsPromise) {
            this.state.statusMessage = "Loading AI Models...";
        } else {
            this.state.statusMessage = "Loading AI Models...";
        }
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
            this.state.statusMessage = "Camera access denied.";
        }
    }

    startScanning() {
        if (this.scanInterval) return;

        this.scanInterval = setInterval(async () => {
            if (this.state.isProcessing) return;

            const videoEl = this.videoRef.el;
            const detection = await faceapi.detectSingleFace(
                videoEl,
                new faceapi.TinyFaceDetectorOptions({ inputSize: 224, scoreThreshold: 0.5 })
            ).withFaceLandmarks().withFaceDescriptor();

            if (detection) {
                this.state.isProcessing = true;
                this.state.statusMessage = "Face detected! Verifying...";

                const isMatch = await this.verifyWithDatabase(detection.descriptor);

                if (isMatch) {
                    if (!this.hasPunched) {
                        this.hasPunched = true;
                        this.state.isProcessing = true;
                        this.state.statusMessage = "Verifying location...";

                        // Capture photo BEFORE stopping camera
                        this._capturedPhotoBase64 = this.capturePhotoBase64();

                        // Await the geo-check that started in the background
                        // when the popup opened.
                        const geoResult = await this.props.geoCheckPromise;

                        if (!geoResult || !geoResult.allowed) {
                            this.state.statusMessage = "❌ " + (geoResult?.message || "You are outside the allowed office location.");
                            console.warn('Geo check failed:', geoResult?.message);
                            this.stopCamera();
                            // Release the lock here too — punch never happened.
                            if (this.props.releaseLock) this.props.releaseLock();
                            setTimeout(() => this.props.close(), 1500);
                            return;
                        }

                        this.state.statusMessage = "✅ Identity Verified!";
                        this.stopCamera();

                        (async () => {
                            // 1. Do the actual punch in Odoo core.
                            // onSuccess returns { openIdBefore } captured
                            // BEFORE this punch happened, so we can
                            // deterministically figure out which record
                            // this exact punch touched.
                            const punchInfo = await this.props.onSuccess();
                            const openIdBefore = punchInfo ? punchInfo.openIdBefore : false;

                            // Small buffer for odoo.sh multi-worker replication lag.
                            await new Promise(resolve => setTimeout(resolve, 400));

                            // ---> DETERMINISTIC RECORD MATCH (no searching by
                            // "latest"). If there WAS an open session before
                            // this punch, this punch just closed it ->
                            // checkout. If there was NONE, this punch just
                            // created a new open session -> checkin. Safe
                            // because only one punch cycle can be in flight
                            // at a time (lock held until we finish here).
                            let attendanceId, punchType;
                            if (openIdBefore) {
                                attendanceId = openIdBefore;
                                punchType = 'checkout';
                            } else {
                                // ---> RETRY LOOP: a checkin is a brand-new
                                // row (create()), which on odoo.sh's multi-
                                // worker setup can take slightly longer to
                                // become visible to the very next request
                                // than a checkout's write() on an existing
                                // row does. A single 400ms buffer wasn't
                                // consistently enough — retry a few times
                                // with short waits instead of giving up
                                // after one attempt.
                                punchType = 'checkin';
                                attendanceId = false;
                                for (let i = 0; i < 5 && !attendanceId; i++) {
                                    attendanceId = await this.orm.call(
                                        'hr.attendance', 'get_open_attendance_id', []
                                    );
                                    if (!attendanceId) {
                                        await new Promise(resolve => setTimeout(resolve, 400));
                                    }
                                }
                            }

                            const photoBase64 = this._capturedPhotoBase64;

                            if (!photoBase64) {
                                console.warn('❌ Photo capture returned empty — nothing to save.');
                            } else if (!attendanceId) {
                                console.warn('❌ Could not determine attendance record id — nothing to save.');
                            } else {
                                console.log("--- ATTEMPTING TO SAVE PHOTO ---");
                                console.log("Attendance ID:", attendanceId, "Punch Type:", punchType);
                                console.log("Geo Zone ID being sent:", geoResult.zone_id);

                                let saveResult = null;
                                let lastError = null;
                                for (let attempt = 1; attempt <= 2; attempt++) {
                                    try {
                                        saveResult = await this.orm.call(
                                            'hr.attendance',
                                            'save_attendance_photo',
                                            [attendanceId, photoBase64, punchType, geoResult.zone_id]
                                        );
                                        if (saveResult && saveResult.success) {
                                            console.log("✅ Photo saved successfully to attendance_id " + saveResult.attendance_id + " (attempt " + attempt + ")");
                                            lastError = null;
                                            break;
                                        } else {
                                            lastError = saveResult && saveResult.error;
                                            console.warn('❌ Attendance photo save failed (attempt ' + attempt + '):', lastError);
                                        }
                                    } catch (e) {
                                        lastError = e;
                                        console.error('❌ Attendance photo save threw (attempt ' + attempt + '):', e);
                                    }
                                }

                                if (lastError) {
                                    console.error('❌ Photo save gave up after retry. Employee attendance was still recorded successfully.');
                                }
                            }

                            // ---> Release the punch lock ONLY NOW, after the
                            // photo save has fully finished (success or not).
                            // This is the actual fix for rapid check-in/out
                            // cycles crossing wires — no second punch can
                            // start until this entire cycle is done.
                            if (this.props.releaseLock) this.props.releaseLock();

                            this.props.close();
                        })();
                    }
                    return;
                } else {
                    this.state.statusMessage = "❌ Face does not match profile.";
                    this.state.isProcessing = false;
                }
            }
        }, 200);
    }

    async verifyWithDatabase(liveDescriptor) {
        try {
            const myDescriptor = await this.orm.call("hr.employee", "get_my_face_descriptor", []);
            if (!myDescriptor) {
                this.state.statusMessage = "No face registered for your account!";
                return false;
            }
            const arr = new Float32Array(JSON.parse(myDescriptor));
            const labeledDescriptors = [new faceapi.LabeledFaceDescriptors("CurrentUser", [arr])];
            const faceMatcher = new faceapi.FaceMatcher(labeledDescriptors, 0.45);
            const bestMatch = faceMatcher.findBestMatch(liveDescriptor);
            return bestMatch.label === "CurrentUser";
        } catch (error) {
            return false;
        }
    }

    // ---> Capture current video frame as JPEG base64 (downscaled)
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
            // Hard stop re-entrancy. This lock now stays held for the
            // ENTIRE punch-to-photo-saved lifecycle (released inside the
            // dialog's releaseLock callback below) — not just until
            // super.signInOut() resolves. This is the core fix: it
            // guarantees only one punch cycle (punch + its photo save)
            // can ever be in flight at a time, so rapid check-in/out/in
            // clicks can never cross wires with each other.
            if (this._punchInProgress) {
                return;
            }
            this._punchInProgress = true;

            let currentState = 'checked_out';

            if (this.employee && this.employee.attendance_state) {
                currentState = this.employee.attendance_state;
            } else if (this.attendanceService && this.attendanceService.isCheckedIn) {
                currentState = 'checked_in';
            } else if (this.attendance && this.attendance.attendance_state) {
                currentState = this.attendance.attendance_state;
            }

            // ---> Snapshot the currently open session id BEFORE the punch.
            // This is what lets us later determine EXACTLY which record
            // this specific punch touched, deterministically — no search,
            // no "latest record" guessing.
            let openIdBefore = false;
            try {
                openIdBefore = await this.orm.call('hr.attendance', 'get_open_attendance_id', []);
            } catch (e) {
                openIdBefore = false;
            }

            const geoCheckPromise = (async () => {
                let latitude = null;
                let longitude = null;

                try {
                    const position = await new Promise((resolve, reject) => {
                        navigator.geolocation.getCurrentPosition(resolve, reject, {
                            timeout: 5000,
                            enableHighAccuracy: false,
                            maximumAge: 30000,
                        });
                    });
                    latitude = position.coords.latitude;
                    longitude = position.coords.longitude;
                } catch (e) {
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
                    return {
                        allowed: false,
                        message: "Could not verify your location. Please try again.",
                    };
                }
            })();

            // Safety net: force-release the lock after 60s no matter what.
            const safetyUnlock = setTimeout(() => {
                this._punchInProgress = false;
            }, 60000);

            // releaseLock is called by the dialog itself, only after the
            // photo save has fully completed — NOT right after signInOut.
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
                    // NOTE: lock is intentionally NOT released here anymore.
                    await super.signInOut();

                    if (currentState === 'checked_in') {
                        if (typeof window.checkLateCheckout === 'function') {
                            setTimeout(window.checkLateCheckout, 1000);
                        }
                    }

                    // Hand back the pre-punch snapshot so the dialog can
                    // deterministically identify its own record.
                    return { openIdBefore };
                },
            });
        }
    });
}