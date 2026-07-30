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

// Standalone preload versions (no dependency on component `this.state`) so
// they can be safely called from the attendance menu on page load, before
// any FaceVerificationDialog instance exists.
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
//            needsBlink: true
        });

        this.stream = null;
        this.scanInterval = null;
        this.hasPunched = false;
        this.isEyesClosed = false;

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
        if (window.faceapi) return;
        if (!_faceApiScriptPromise) {
            _faceApiScriptPromise = new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = '/attendance_planning/static/src/lib/face-api.js';
                script.onload = () => resolve();
                script.onerror = () => {
                    console.error("❌ CRITICAL: Could not find face-api.js at", script.src);
                    console.error("Please verify the file exists in your static/src/lib folder and restart the Odoo server.");
                    _faceApiScriptPromise = null;
                    reject(new Error("Failed to load face-api.js"));
                };
                document.head.appendChild(script);
            });
        }
        return _faceApiScriptPromise;
    }

    // Models are only ever downloaded/initialized ONCE per page session now —
    // every dialog open after the first reuses the same cached promise, so the
    // camera opens instantly instead of reloading the AI models every click.
    async loadModels() {
        if (!_faceApiModelsPromise) {
            this.state.statusMessage = "Loading AI Models...";
            const modelPath = '/attendance_planning/static/src/models';
            _faceApiModelsPromise = Promise.all([
                faceapi.nets.tinyFaceDetector.loadFromUri(modelPath),
                faceapi.nets.faceLandmark68Net.loadFromUri(modelPath),
                faceapi.nets.faceRecognitionNet.loadFromUri(modelPath),
            ]).catch((e) => {
                _faceApiModelsPromise = null;
                throw e;
            });
        } else {
            this.state.statusMessage = "Loading AI Models...";
        }
        await _faceApiModelsPromise;
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
            const detection = await faceapi.detectSingleFace(videoEl, new faceapi.TinyFaceDetectorOptions({ inputSize: 224, scoreThreshold: 0.5 })).withFaceLandmarks().withFaceDescriptor();

            if (detection) {
//                // ---> BLINK DETECTION
//                if (this.state.needsBlink) {
//                    const leftEye = detection.landmarks.getLeftEye();
//                    const rightEye = detection.landmarks.getRightEye();
//                    const avgEAR = (getEAR(leftEye) + getEAR(rightEye)) / 2.0;
//                    const BLINK_THRESHOLD = 0.25;
//
//                    if (avgEAR < BLINK_THRESHOLD) {
//                        this.isEyesClosed = true;
//                        this.state.statusMessage = "Blink detected! Verifying...";
//                    } else if (this.isEyesClosed && avgEAR >= BLINK_THRESHOLD) {
//                        this.isEyesClosed = false;
//                        this.state.needsBlink = false;
//                        this.state.statusMessage = "Liveness verified. Matching face...";
//                    } else {
//                        this.state.statusMessage = "Please BLINK to verify liveness!";
//                    }
//                    return;
//                }

                this.state.isProcessing = true;
                this.state.statusMessage = "Face detected! Verifying...";

                const isMatch = await this.verifyWithDatabase(detection.descriptor);

                if (isMatch) {
                    if (!this.hasPunched) {
                        this.hasPunched = true;
                        this.state.isProcessing = true;
                        this.state.statusMessage = "Verifying location...";

                        // ---> FIX 1: Capture photo BEFORE stopping camera
                        const photoBase64 = this.capturePhotoBase64();

                        // Await the geo-check that started in the background
                        // when the popup opened. In almost every case this
                        // resolves instantly here since it's been running
                        // the whole time the camera/AI models were loading.
                        const geoResult = await this.props.geoCheckPromise;

                        if (!geoResult || !geoResult.allowed) {
                            this.state.statusMessage = "❌ " + (geoResult?.message || "You are outside the allowed office location.");
                            if (this.props.notificationService) {
                                this.props.notificationService.add(
                                    geoResult?.message || "You are outside the allowed office location.",
                                    { type: "danger", sticky: true }
                                );
                            }
                            this.stopCamera();
                            setTimeout(() => this.props.close(), 1500);
                            return;
                        }

                        this.state.statusMessage = "✅ Identity Verified!";

                        // NOW stop camera after photo captured
                        this.stopCamera();

                        setTimeout(async () => {
                            // 1. Do the actual punch
                            await this.props.onSuccess();

                            // 2. Save photo against the attendance record.
                            // NOTE: previously, if photoBase64 was falsy
                            // (capture silently failed), this whole block
                            // was skipped with NO warning at all — the punch
                            // succeeded but the photo vanished without a
                            // trace. That gap is now closed below.
                            if (!photoBase64) {
                                console.warn('❌ Photo capture returned empty — nothing to save.');
                                if (this.props.notificationService) {
                                    this.props.notificationService.add(
                                        "Your attendance was recorded, but the photo capture failed. Please inform admin.",
                                        { type: "warning", sticky: true }
                                    );
                                }
                            } else {
                                const punchType = this.props.attendanceState === 'checked_in'
                                    ? 'checkout'
                                    : 'checkin';

                                console.log("--- ATTEMPTING TO SAVE PHOTO AND GEO ID ---");
                                console.log("Punch Type:", punchType);
                                console.log("Geo Zone ID being sent:", geoResult.zone_id);

                                // Retry once on failure before giving up —
                                // covers a transient network blip (common
                                // cause of "works in local, fails in prod").
                                let saveResult = null;
                                let lastError = null;
                                for (let attempt = 1; attempt <= 2; attempt++) {
                                    try {
                                        saveResult = await this.orm.call(
                                            'hr.attendance',
                                            'save_attendance_photo',
                                            [photoBase64, punchType, geoResult.zone_id]
                                        );
                                        if (saveResult && saveResult.success) {
                                            console.log("✅ Photo and Geo ID saved successfully! (attempt " + attempt + ")");
                                            lastError = null;
                                            break;
                                        } else {
                                            lastError = saveResult && saveResult.error;
                                            console.warn('❌ Attendance photo save failed (attempt ' + attempt + '):', lastError);
                                        }
                                    } catch (e) {
                                        lastError = e;
                                        console.warn('❌ Attendance photo save threw (attempt ' + attempt + '):', e);
                                    }
                                }

                                if (lastError) {
                                    if (this.props.notificationService) {
                                        this.props.notificationService.add(
                                            "Your attendance was recorded, but the photo could not be saved after retrying. Please inform admin.",
                                            { type: "warning", sticky: true }
                                        );
                                    }
                                }
                            }

                            this.props.close();
                        }, 1000);
                    }
                    return;
                } else {
                    this.state.statusMessage = "❌ Face does not match profile.";
//                    this.state.needsBlink = true;
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

    // ---> Capture current video frame as JPEG base64
    capturePhotoBase64() {
        try {
            const video = this.videoRef.el;
            if (!video || !video.videoWidth || !video.videoHeight) {
                console.warn('Photo capture skipped: video element not ready (videoWidth/videoHeight is 0).');
                return null;
            }
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
            const base64 = dataUrl.split(',')[1];
            if (!base64 || base64.length < 100) {
                console.warn('Photo capture produced suspiciously small/empty data.');
                return null;
            }
            return base64;
        } catch (e) {
            console.warn('Photo capture failed:', e);
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

            // PRELOAD: start downloading face-api.js + the AI models the
            // moment this menu mounts (i.e. as soon as the page/session
            // loads), instead of waiting for the user's first click. This
            // uses the same module-level cached promises as the dialog, so
            // by the time the user actually clicks Check In, the models are
            // already downloaded and the camera opens instantly — even on
            // the very first punch of the day.
            (async () => {
                try {
                    await preloadFaceApiScript();
                    await preloadFaceApiModels();
                } catch (e) {
                    console.warn('Face-api preload failed (will retry on click):', e);
                }
            })();
        },

        // ---> FIX 2 (updated): Open popup INSTANTLY. Geo is checked in the
        // background while the camera/AI models are loading, instead of
        // blocking the popup from opening. By the time the user's face is
        // detected and matched, the geo result has almost always already
        // arrived — so there is no extra wait, just a different order.
        async signInOut() {
            // Hard stop re-entrancy: this is what actually fixes the
            // "hasn't checked out since ..." validation error. Ignore any
            // click while a punch from a previous click is still running.
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

            // Kick off geo-check in the BACKGROUND — do not await it here.
            // This promise resolves to { allowed, zone_id, message } and is
            // handed to the dialog, which awaits it only once a face match
            // is found (by then it's almost always already resolved).
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

                    console.log("--- LOCATION FETCHED ---");
                    console.log("Latitude:", latitude);
                    console.log("Longitude:", longitude);
                    console.log("Accuracy (meters):", position.coords.accuracy);
                    console.log("Timestamp:", new Date(position.timestamp).toLocaleString());
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

                    console.log("--- GEO CHECK RESULT FROM PYTHON ---");
                    console.log("Full Result Object:", result);

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
                        // Fallback just in case their python code returns 'id' instead of 'zone_id'
                        zoneId = result.id;
                    }

                    console.log("Extracted Geo Zone ID mapping to:", zoneId);
                    return { allowed: true, zone_id: zoneId };

                } catch (e) {
                    return {
                        allowed: false,
                        message: "Could not verify your location. Please try again.",
                    };
                }
            })();

            // Open face verification IMMEDIATELY — no waiting on geo.
            // Safety net: force-release the lock after 60s no matter what,
            // so the button can never get stuck until a page refresh even if
            // the user closes the dialog without completing it. We deliberately
            // do NOT pass a custom "close" prop into the dialog here — Odoo's
            // dialog service already auto-injects its own "close" function into
            // every dialog it opens, and defining our own "close" key collides
            // with that (this exact collision was the cause of an earlier
            // "stuck until refresh" bug), so we avoid it entirely.
            const safetyUnlock = setTimeout(() => {
                this._punchInProgress = false;
            }, 60000);

            this.dialogService.add(FaceVerificationDialog, {
                attendanceState: currentState,
                geoCheckPromise: geoCheckPromise, // dialog awaits this before punching
                notificationService: this.notificationService,
                onSuccess: async () => {
                    try {
                        await super.signInOut();

                        console.log("Checkout completed, currentState was:", currentState);

                        if (currentState === 'checked_in') {
                            if (typeof window.checkLateCheckout === 'function') {
                                console.log("Calling checkLateCheckout in 1s...");
                                setTimeout(window.checkLateCheckout, 1000);
                            } else {
                                console.error("checkLateCheckout is not available on window!");
                            }
                        }
                    } finally {
                        clearTimeout(safetyUnlock);
                        this._punchInProgress = false;
                    }
                },
            });
        }
    });
}






