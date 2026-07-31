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
        ]).then(async () => {
            // ---> WARM-UP: run one throwaway detection on a blank canvas.
            // The very FIRST time face-api actually runs inference, the
            // WASM backend has to JIT-compile its kernels — this is often
            // several seconds, completely separate from model download
            // time, and normally happens silently during the user's real
            // first face scan (making it feel slow). Forcing it here,
            // during background preload, means that cost is already paid
            // by the time the user actually opens the camera.
            try {
                const warmupCanvas = document.createElement('canvas');
                warmupCanvas.width = 64;
                warmupCanvas.height = 64;
                await faceapi.detectSingleFace(
                    warmupCanvas,
                    new faceapi.TinyFaceDetectorOptions({ inputSize: 224, scoreThreshold: 0.5 })
                );
            } catch (e) {
                // Warm-up failure is non-fatal — real detection will just
                // pay the JIT cost on first real use instead.
            }
        }).catch((e) => {
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

                        this._capturedPhotoBase64 = this.capturePhotoBase64();

                        // Await BOTH background promises that started the
                        // instant the popup opened (geo check + open-session
                        // snapshot) — by now, after the camera + AI models
                        // loaded and the face was scanned, these have almost
                        // always already finished. This is what keeps the
                        // popup opening instantly regardless of network speed.
                        const [geoResult, openIdBefore] = await Promise.all([
                            this.props.geoCheckPromise,
                            this.props.openIdBeforePromise,
                        ]);

                        if (!geoResult || !geoResult.allowed) {
                            this.state.statusMessage = "❌ " + (geoResult?.message || "You are outside the allowed office location.");
                            console.warn('Geo check failed:', geoResult?.message);
                            this.stopCamera();
                            if (this.props.releaseLock) this.props.releaseLock();
                            setTimeout(() => this.props.close(), 1500);
                            return;
                        }

                        this.state.statusMessage = "✅ Identity Verified!";
                        this.stopCamera();

                        (async () => {
                            // 1. Do the actual punch in Odoo core.
                            await this.props.onSuccess();

                            // Small buffer for odoo.sh multi-worker replication lag.
                            await new Promise(resolve => setTimeout(resolve, 400));

                            // ---> DETERMINISTIC RECORD MATCH (no searching
                            // by "latest"). openIdBefore was snapshotted
                            // BEFORE this punch happened (in parallel, non-
                            // blocking). If there WAS an open session, this
                            // punch just closed it -> checkout. If not, a
                            // new session was just opened -> checkin.
                            let attendanceId, punchType;
                            if (openIdBefore) {
                                attendanceId = openIdBefore;
                                punchType = 'checkout';
                            } else {
                                attendanceId = await this.orm.call(
                                    'hr.attendance', 'get_open_attendance_id', []
                                );
                                punchType = 'checkin';
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

            // ---> FIX: this used to be `await`ed here, which blocked the
            // popup from opening until this RPC finished — reintroducing
            // the exact "slow to open" bug we fixed earlier. Now it just
            // starts the request and hands the PROMISE to the dialog,
            // which awaits it later (in parallel with camera/AI loading
            // and the geo check), exactly like geoCheckPromise already
            // does. The popup now opens instantly regardless of network
            // speed — this is very likely why some employees ("not
            // waiting patiently") were experiencing a real delay before
            // the camera even appeared.
            const openIdBeforePromise = this.orm
                .call('hr.attendance', 'get_open_attendance_id', [])
                .catch(() => false);

            const geoCheckPromise = (async () => {
                // ---> Check bypass status FIRST — this is instant (no
                // GPS needed). If the employee is flagged "Allow Check-in
                // Anywhere", skip the GPS fetch entirely instead of
                // spending up to 5 seconds waiting on
                // navigator.geolocation only to discover afterward it
                // wasn't even needed.
                try {
                    const isBypassed = await this.orm.call(
                        'hr.attendance', 'is_geo_bypass_employee', []
                    );
                    if (isBypassed) {
                        return { allowed: true, zone_id: false };
                    }
                } catch (e) {
                    // if this check itself fails, fall through to the
                    // normal GPS-based flow below
                }

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

            const safetyUnlock = setTimeout(() => {
                this._punchInProgress = false;
            }, 60000);

            const releaseLock = () => {
                clearTimeout(safetyUnlock);
                this._punchInProgress = false;
            };

            // Popup opens IMMEDIATELY — both promises above are still
            // in-flight and get handed straight to the dialog.
            this.dialogService.add(FaceVerificationDialog, {
                attendanceState: currentState,
                geoCheckPromise: geoCheckPromise,
                openIdBeforePromise: openIdBeforePromise,
                notificationService: this.notificationService,
                releaseLock: releaseLock,
                onSuccess: async () => {
                    await super.signInOut();

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

