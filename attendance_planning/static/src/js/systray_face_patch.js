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

export class FaceVerificationDialog extends Component {
    setup() {
        this.videoRef = useRef("videoElement");
        this.orm = useService("orm");

        this.state = useState({
            statusMessage: "Downloading AI Engine...",
            isProcessing: false,
            needsBlink: true
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
                faceapi.nets.ssdMobilenetv1.loadFromUri(modelPath),
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
            const detection = await faceapi.detectSingleFace(videoEl).withFaceLandmarks().withFaceDescriptor();

            if (detection) {
                // ---> BLINK DETECTION
                if (this.state.needsBlink) {
                    const leftEye = detection.landmarks.getLeftEye();
                    const rightEye = detection.landmarks.getRightEye();
                    const avgEAR = (getEAR(leftEye) + getEAR(rightEye)) / 2.0;
                    const BLINK_THRESHOLD = 0.25;

                    if (avgEAR < BLINK_THRESHOLD) {
                        this.isEyesClosed = true;
                        this.state.statusMessage = "Blink detected! Verifying...";
                    } else if (this.isEyesClosed && avgEAR >= BLINK_THRESHOLD) {
                        this.isEyesClosed = false;
                        this.state.needsBlink = false;
                        this.state.statusMessage = "Liveness verified. Matching face...";
                    } else {
                        this.state.statusMessage = "Please BLINK to verify liveness!";
                    }
                    return;
                }

                this.state.isProcessing = true;
                this.state.statusMessage = "Face detected! Verifying...";

                const isMatch = await this.verifyWithDatabase(detection.descriptor);

                if (isMatch) {
                    this.state.statusMessage = "✅ Identity Verified!";

                    if (!this.hasPunched) {
                        this.hasPunched = true;

                        // ---> FIX 1: Capture photo BEFORE stopping camera
                        const photoBase64 = this.capturePhotoBase64();

                        // NOW stop camera after photo captured
                        this.stopCamera();

                        setTimeout(async () => {
                            // 1. Do the actual punch
                            await this.props.onSuccess();

                            // 2. Save photo against the attendance record
                            if (photoBase64) {
                                const punchType = this.props.attendanceState === 'checked_in'
                                    ? 'checkout'
                                    : 'checkin';

                                console.log("--- ATTEMPTING TO SAVE PHOTO AND GEO ID ---");
                                console.log("Punch Type:", punchType);
                                console.log("Geo Zone ID being sent:", this.props.geoZoneId);

                                try {
                                    await this.orm.call(
                                        'hr.attendance',
                                        'save_attendance_photo',
                                        [photoBase64, punchType, this.props.geoZoneId]
                                    );
                                    console.log("✅ Photo and Geo ID saved successfully!");
                                } catch (e) {
                                    console.warn('❌ Attendance photo save failed:', e);
                                }
                            }

                            this.props.close();
                        }, 1000);
                    }
                    return;
                } else {
                    this.state.statusMessage = "❌ Face does not match profile.";
                    this.state.needsBlink = true;
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
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth || 400;
            canvas.height = video.videoHeight || 400;
            canvas.getContext('2d').drawImage(video, 0, 0);
            return canvas.toDataURL('image/jpeg', 0.8).split(',')[1];
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
            // Guard flag: this is the actual fix for the "hasn't checked out"
            // validation error. The old code had no protection against a
            // double-click (or a bubbled double-fire event) calling signInOut()
            // twice in quick succession — each call independently tried to
            // create an attendance record, and the second one collided with
            // the first, producing that error. This flag makes signInOut()
            // ignore any call while one is already in flight.
            this._punchInProgress = false;
        },

        // ---> FIX 2: Check geo BEFORE opening camera
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

            // Step 1: Get GPS coordinates
            let latitude = null;
            let longitude = null;
            let currentGeoZoneId = false;

            try {
                const position = await new Promise((resolve, reject) => {
                    navigator.geolocation.getCurrentPosition(resolve, reject, {
                        timeout: 10000,
                        enableHighAccuracy: true,
                    });
                });
                latitude = position.coords.latitude;
                longitude = position.coords.longitude;
            } catch (e) {
                this.notificationService.add(
                    "Location access is required for attendance. Please allow location and try again.",
                    { type: "danger", sticky: true }
                );
                this._punchInProgress = false;
                return;
            }

            // Step 2: Ask backend if employee is within allowed zone
            try {
                const result = await this.orm.call(
                    'hr.attendance',
                    'check_employee_geo_allowed',
                    [latitude, longitude]
                );

                console.log("--- GEO CHECK RESULT FROM PYTHON ---");
                console.log("Full Result Object:", result);

                if (!result || (typeof result === 'object' && !result.allowed) || result === false) {
                    this.notificationService.add(
                        (result && result.message) ? result.message : "You are outside the allowed office location.",
                        { type: "danger", sticky: true }
                    );
                    this._punchInProgress = false;
                    return;
                }

                // EXTRACT THE ID RETURNED BY THE BACKEND
                if (result && result.zone_id) {
                    currentGeoZoneId = result.zone_id;
                } else if (result && result.id) {
                    // Fallback just in case their python code returns 'id' instead of 'zone_id'
                    currentGeoZoneId = result.id;
                }

                console.log("Extracted Geo Zone ID mapping to:", currentGeoZoneId);

            } catch (e) {
                this.notificationService.add(
                    "Could not verify your location. Please try again.",
                    { type: "danger", sticky: true }
                );
                this._punchInProgress = false;
                return;
            }

            // Step 3: Geo passed — open face verification.
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
                geoZoneId: currentGeoZoneId, // PASS THE ID TO THE VERIFICATION DIALOG
                onSuccess: async () => {
                    try {
                        // Pure native call — this is what makes the button
                        // color and check-in/out location fields update
                        // automatically, exactly like your old working code.
                        await super.signInOut();
                    } finally {
                        clearTimeout(safetyUnlock);
                        this._punchInProgress = false;
                    }
                },
            });
        }
    });
}


