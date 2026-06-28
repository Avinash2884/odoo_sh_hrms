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
        return new Promise((resolve, reject) => {
            if (window.faceapi) return resolve();
            const script = document.createElement('script');
            script.src = '/attendance_planning/static/src/lib/face-api.js';
            script.onload = () => resolve();
            script.onerror = () => {
                console.error("❌ CRITICAL: Could not find face-api.js at", script.src);
                console.error("Please verify the file exists in your static/src/lib folder and restart the Odoo server.");
                reject(new Error("Failed to load face-api.js"));
            };
            document.head.appendChild(script);
        });
    }

    async loadModels() {
        this.state.statusMessage = "Loading AI Models...";
        const modelPath = '/attendance_planning/static/src/models';
        await faceapi.nets.ssdMobilenetv1.loadFromUri(modelPath);
        await faceapi.nets.faceLandmark68Net.loadFromUri(modelPath);
        await faceapi.nets.faceRecognitionNet.loadFromUri(modelPath);
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
        },

        // ---> FIX 2: Check geo BEFORE opening camera
        async signInOut() {
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
                return;
            }

            // Step 3: Geo passed — open face verification
            this.dialogService.add(FaceVerificationDialog, {
                attendanceState: currentState,
                geoZoneId: currentGeoZoneId, // PASS THE ID TO THE VERIFICATION DIALOG
                onSuccess: async () => {
                    await super.signInOut();
                }
            });
        }
    });
}





///** @odoo-module **/
//
//import * as attendanceMenuModule from "@hr_attendance/components/attendance_menu/attendance_menu";
//import { patch } from "@web/core/utils/patch";
//import { Dialog } from "@web/core/dialog/dialog";
//import { useService } from "@web/core/utils/hooks";
//import { Component, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";
//
//// ---> ADDITION 1: Math functions to measure the eye blink
//function euclideanDistance(point1, point2) {
//    return Math.sqrt(Math.pow(point1.x - point2.x, 2) + Math.pow(point1.y - point2.y, 2));
//}
//
//function getEAR(eye) {
//    const v1 = euclideanDistance(eye[1], eye[5]);
//    const v2 = euclideanDistance(eye[2], eye[4]);
//    const h = euclideanDistance(eye[0], eye[3]);
//    return (v1 + v2) / (2.0 * h);
//}
//// <--- END ADDITION 1
//
//export class FaceVerificationDialog extends Component {
//    setup() {
//        this.videoRef = useRef("videoElement");
//        this.orm = useService("orm");
//
//        this.state = useState({
//            statusMessage: "Downloading AI Engine...",
//            isProcessing: false,
//            needsBlink: true // ---> ADDITION 2: Require blink in the backend popup too
//        });
//
//        this.stream = null;
//        this.scanInterval = null;
//        this.hasPunched = false; // <-- THE MASTER LOCK
//        this.isEyesClosed = false; // ---> ADDITION 3: Track if eyes are currently closed
//
//        onMounted(async () => {
//            await this.injectFaceApiScript();
//            await this.loadModels();
//            await this.startCamera();
//        });
//
//        onWillUnmount(() => {
//            this.stopCamera();
//        });
//    }
//
//    async injectFaceApiScript() {
//        return new Promise((resolve, reject) => {
//            if (window.faceapi) return resolve();
//            const script = document.createElement('script');
//            script.src = '/attendance_planning/static/src/lib/face-api.js';
//            script.onload = () => resolve();
//            script.onerror = () => reject(new Error("Failed to load face-api.js"));
//            document.head.appendChild(script);
//        });
//    }
//
//    async loadModels() {
//        this.state.statusMessage = "Loading AI Models...";
//        const modelPath = '/attendance_planning/static/src/models';
//        await faceapi.nets.ssdMobilenetv1.loadFromUri(modelPath);
//        await faceapi.nets.faceLandmark68Net.loadFromUri(modelPath); // <-- Added Landmark Model
//        await faceapi.nets.faceRecognitionNet.loadFromUri(modelPath);
//        this.state.statusMessage = "Ready. Please look at the camera.";
//    }
//
//    async startCamera() {
//        try {
//            this.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
//            if (this.videoRef.el) {
//                this.videoRef.el.srcObject = this.stream;
//                this.videoRef.el.addEventListener('play', () => this.startScanning());
//            }
//        } catch (err) {
//            this.state.statusMessage = "Camera access denied.";
//        }
//    }
//
//    startScanning() {
//        if (this.scanInterval) return;
//
//        // ---> ADDITION 4: Changed to 200ms to catch fast blinks
//        this.scanInterval = setInterval(async () => {
//            if (this.state.isProcessing) return;
//
//            const videoEl = this.videoRef.el;
//
//            // ---> ADDITION 5: Added .withFaceLandmarks()
//            const detection = await faceapi.detectSingleFace(videoEl).withFaceLandmarks().withFaceDescriptor();
//
//            if (detection) {
//                // ---> ADDITION 6: The core Blink Detection Logic
//                if (this.state.needsBlink) {
//                    const leftEye = detection.landmarks.getLeftEye();
//                    const rightEye = detection.landmarks.getRightEye();
//
//                    const leftEAR = getEAR(leftEye);
//                    const rightEAR = getEAR(rightEye);
//                    const avgEAR = (leftEAR + rightEAR) / 2.0;
//
//                    const BLINK_THRESHOLD = 0.25;
//
//                    if (avgEAR < BLINK_THRESHOLD) {
//                        this.isEyesClosed = true;
//                        this.state.statusMessage = "Blink detected! Verifying...";
//                    } else if (this.isEyesClosed && avgEAR >= BLINK_THRESHOLD) {
//                        this.isEyesClosed = false;
//                        this.state.needsBlink = false; // Blink complete!
//                        this.state.statusMessage = "Liveness verified. Matching face...";
//                    } else {
//                        this.state.statusMessage = "Please BLINK to verify liveness!";
//                    }
//                    return; // Stop here and wait for the next frame until they blink
//                }
//                // <--- END ADDITION 6
//
//                // Lock processing to prevent spamming the database while verifying
//                this.state.isProcessing = true;
//                this.state.statusMessage = "Face detected! Verifying...";
//
//                const isMatch = await this.verifyWithDatabase(detection.descriptor);
//
//                if (isMatch) {
//                    this.state.statusMessage = "✅ Identity Verified!";
//                    this.stopCamera();
//
//                    if (!this.hasPunched) {
//                        this.hasPunched = true;
//
//                        // ---> CAPTURE PHOTO at the exact blink+verify moment
//                        const photoBase64 = this.capturePhotoBase64();
//
//                        setTimeout(async () => {
//                            // 1. Do the actual punch first
//                            await this.props.onSuccess();
//
//                            // 2. Then save the photo against that record
//                            if (photoBase64) {
//                                const punchType = this.props.attendanceState === 'checked_in'
//                                    ? 'checkout'
//                                    : 'checkin';
//                                await this.orm.call(
//                                    'hr.attendance',
//                                    'save_attendance_photo',
//                                    [photoBase64, punchType]
//                                );
//                            }
//
//                            this.props.close();
//                        }, 1000);
//                    }
//                    return;
//                } else {
//                    this.state.statusMessage = "❌ Face does not match profile.";
//                    this.state.needsBlink = true; // ---> ADDITION 7: Reset blink if someone else's face is shown
//                    this.state.isProcessing = false; // Unlock to scan again
//                }
//            }
//        }, 200); // <-- This used to be 1000
//    }
//
//    async verifyWithDatabase(liveDescriptor) {
//        try {
//            const myDescriptor = await this.orm.call("hr.employee", "get_my_face_descriptor", []);
//            if (!myDescriptor) {
//                this.state.statusMessage = "No face registered for your account!";
//                return false;
//            }
//
//            const arr = new Float32Array(JSON.parse(myDescriptor));
//            const labeledDescriptors = [new faceapi.LabeledFaceDescriptors("CurrentUser", [arr])];
//            const faceMatcher = new faceapi.FaceMatcher(labeledDescriptors, 0.45);
//            const bestMatch = faceMatcher.findBestMatch(liveDescriptor);
//
//            return bestMatch.label === "CurrentUser";
//        } catch (error) {
//            return false;
//        }
//    }
//
//    stopCamera() {
//        if (this.scanInterval) clearInterval(this.scanInterval);
//        if (this.stream) this.stream.getTracks().forEach(track => track.stop());
//    }
//}
//FaceVerificationDialog.template = "attendance_planning.FaceVerificationPopup";
//FaceVerificationDialog.components = { Dialog };
//
//const ActualAttendanceMenu = attendanceMenuModule.systrayAttendance?.Component || attendanceMenuModule.systrayAttendance;
//
//if (ActualAttendanceMenu) {
//    patch(ActualAttendanceMenu.prototype, {
//        setup() {
//            super.setup(...arguments);
//            this.dialogService = useService("dialog");
//        },
//        async signInOut() {
//            this.dialogService.add(FaceVerificationDialog, {
//                onSuccess: async () => {
//                    await super.signInOut();
//                }
//            });
//        }
//    });
//}
//
//
//
//
//
//
//
