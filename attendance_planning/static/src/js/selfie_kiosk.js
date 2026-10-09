/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";

// ---> ADDITION 1: Math functions to measure the eye blink
function euclideanDistance(point1, point2) {
    return Math.sqrt(Math.pow(point1.x - point2.x, 2) + Math.pow(point1.y - point2.y, 2));
}

function getEAR(eye) {
    const v1 = euclideanDistance(eye[1], eye[5]);
    const v2 = euclideanDistance(eye[2], eye[4]);
    const h = euclideanDistance(eye[0], eye[3]);
    return (v1 + v2) / (2.0 * h);
}
// <--- END ADDITION 1

export class SelfieKiosk extends Component {
    setup() {
        this.videoRef = useRef("videoElement");
        this.canvasRef = useRef("canvasElement");
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            statusMessage: "Downloading AI Engine... Please wait.",
            successName: false,
            isProcessing: false, // Stops it from punching 10 times a second
            needsBlink: true // ---> ADDITION 2: Start by requiring a blink
        });

        this.stream = null;
        this.faceMatcher = null;
        this.scanInterval = null;
        this.isEyesClosed = false; // ---> ADDITION 3: Track if eyes are currently closed

        onMounted(async () => {
            await this.injectFaceApiScript(); // <-- WE ADDED THIS HERE!
            await this.loadModels();
            await this.loadEmployeeFaces();
            await this.startCamera();
        });

        onWillUnmount(() => {
            this.stopCamera();
        });
    }

    // <-- WE ADDED THE BYPASS INJECTOR HERE! -->
    async injectFaceApiScript() {
        return new Promise((resolve, reject) => {
            if (window.faceapi) return resolve();

            const script = document.createElement('script');
            script.src = '/attendance_planning/static/src/lib/face-api.js';
            script.onload = () => resolve();
            script.onerror = () => reject(new Error("Failed to load face-api.js"));
            document.head.appendChild(script);
        });
    }

    async loadModels() {
        const modelPath = '/attendance_planning/static/src/models';
        await faceapi.nets.ssdMobilenetv1.loadFromUri(modelPath);
        await faceapi.nets.faceLandmark68Net.loadFromUri(modelPath);
        await faceapi.nets.faceRecognitionNet.loadFromUri(modelPath);
    }

    async loadEmployeeFaces() {
        this.state.statusMessage = "Loading Employee Secure Data...";
        try {
            const employees = await this.orm.call("hr.employee", "get_all_face_descriptors", []);

            if (employees.length === 0) {
                this.state.statusMessage = "No faces registered in the system!";
                return;
            }

            const labeledDescriptors = employees.map(emp => {
                const arr = new Float32Array(JSON.parse(emp.descriptor));
                const label = `${emp.id}|${emp.name}`;
                return new faceapi.LabeledFaceDescriptors(label, [arr]);
            });

            this.faceMatcher = new faceapi.FaceMatcher(labeledDescriptors, 0.45);
            this.state.statusMessage = "System Ready. Step up to the camera.";

        } catch (error) {
            console.error(error);
            this.state.statusMessage = "Error connecting to database.";
        }
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
        if (!this.faceMatcher) return;

        // ---> ADDITION 4: Changed 1000 to 200 so it scans fast enough to catch a blink
        this.scanInterval = setInterval(async () => {
            if (this.state.isProcessing) return;

            const videoEl = this.videoRef.el;
            if (!videoEl || videoEl.readyState < 2 || !videoEl.videoWidth || !videoEl.videoHeight) {
                return;
            }

            // ---> ADDITION 5: Added .withFaceLandmarks() here
            let detection;
            try {
                detection = await faceapi.detectSingleFace(videoEl).withFaceLandmarks().withFaceDescriptor();
            } catch (e) {
                console.warn("Face detection skipped this frame:", e);
                return;
            }

            if (detection) {
                // ---> ADDITION 6: The core Blink Detection Logic
                if (this.state.needsBlink) {
                    const leftEye = detection.landmarks.getLeftEye();
                    const rightEye = detection.landmarks.getRightEye();

                    const leftEAR = getEAR(leftEye);
                    const rightEAR = getEAR(rightEye);
                    const avgEAR = (leftEAR + rightEAR) / 2.0;

                    const BLINK_THRESHOLD = 0.25;

                    if (avgEAR < BLINK_THRESHOLD) {
                        this.isEyesClosed = true;
                        this.state.statusMessage = "Blink detected! Verifying...";
                    } else if (this.isEyesClosed && avgEAR >= BLINK_THRESHOLD) {
                        this.isEyesClosed = false;
                        this.state.needsBlink = false; // Blink complete!
                        this.state.statusMessage = "Liveness verified. Matching face...";
                    } else {
                        this.state.statusMessage = "Please BLINK to verify liveness!";
                    }
                    return; // Stop here and wait for the next frame until they blink
                }
                // <--- END ADDITION 6

                const bestMatch = this.faceMatcher.findBestMatch(detection.descriptor);

                if (bestMatch.label !== "unknown") {
                    this.state.isProcessing = true;
                    this.state.statusMessage = "Face Verified! Logging attendance...";

                    const splitData = bestMatch.label.split('|');
                    const employeeId = parseInt(splitData[0]);
                    const employeeName = splitData[1];

                    await this.triggerPunch(employeeId, employeeName);
                }
            }
        }, 200); // <-- This used to be 1000
    }

    async triggerPunch(employeeId, employeeName) {
        try {
            // Trigger the Python punch
            await this.orm.call("hr.employee", "ai_attendance_manual", [employeeId]);

            this.state.statusMessage = "Please step away from the camera..."; // Tell them to move!
            this.state.successName = employeeName;

            // Increased to an 8-second cooldown to give them time to walk away
            setTimeout(() => {
                this.state.successName = false;
                this.state.statusMessage = "System Ready. Step up to the camera.";
                this.state.isProcessing = false; // Scanner turns back on here
                this.state.needsBlink = true; // ---> ADDITION 7: Reset blink for the next person
            }, 8000);

        } catch (error) {
            this.state.statusMessage = "Error logging attendance.";
            this.state.isProcessing = false;
            this.state.needsBlink = true; // ---> ADDITION 8: Reset blink if there is an error
        }
    }

    stopCamera() {
        if (this.scanInterval) clearInterval(this.scanInterval);
        if (this.stream) this.stream.getTracks().forEach(track => track.stop());
    }

    _onCloseClick() {
        // Bulletproof exit strategy: Force the browser back to the main Odoo dashboard
        window.location.href = '/odoo';
    }
}
SelfieKiosk.template = "attendance_planning.SelfieKioskScreen";
registry.category("actions").add("attendance_selfie_kiosk", SelfieKiosk);





//worked old code

///** @odoo-module **/
//
//import { registry } from "@web/core/registry";
//import { useService } from "@web/core/utils/hooks";
//import { Component, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";
//
//export class SelfieKiosk extends Component {
//    setup() {
//        this.videoRef = useRef("videoElement");
//        this.canvasRef = useRef("canvasElement");
//        this.orm = useService("orm");
//        this.action = useService("action");
//
//        this.state = useState({
//            statusMessage: "Downloading AI Engine... Please wait.",
//            successName: false,
//            isProcessing: false // Stops it from punching 10 times a second
//        });
//
//        this.stream = null;
//        this.faceMatcher = null;
//        this.scanInterval = null;
//
//        onMounted(async () => {
//            await this.injectFaceApiScript(); // <-- WE ADDED THIS HERE!
//            await this.loadModels();
//            await this.loadEmployeeFaces();
//            await this.startCamera();
//        });
//
//        onWillUnmount(() => {
//            this.stopCamera();
//        });
//    }
//
//    // <-- WE ADDED THE BYPASS INJECTOR HERE! -->
//    async injectFaceApiScript() {
//        return new Promise((resolve, reject) => {
//            if (window.faceapi) return resolve();
//
//            const script = document.createElement('script');
//            script.src = '/attendance_planning/static/src/lib/face-api.js';
//            script.onload = () => resolve();
//            script.onerror = () => reject(new Error("Failed to load face-api.js"));
//            document.head.appendChild(script);
//        });
//    }
//
//    async loadModels() {
//        const modelPath = '/attendance_planning/static/src/models';
//        await faceapi.nets.ssdMobilenetv1.loadFromUri(modelPath);
//        await faceapi.nets.faceLandmark68Net.loadFromUri(modelPath);
//        await faceapi.nets.faceRecognitionNet.loadFromUri(modelPath);
//    }
//
//    async loadEmployeeFaces() {
//        this.state.statusMessage = "Loading Employee Secure Data...";
//        try {
//            const employees = await this.orm.call("hr.employee", "get_all_face_descriptors", []);
//
//            if (employees.length === 0) {
//                this.state.statusMessage = "No faces registered in the system!";
//                return;
//            }
//
//            const labeledDescriptors = employees.map(emp => {
//                const arr = new Float32Array(JSON.parse(emp.descriptor));
//                const label = `${emp.id}|${emp.name}`;
//                return new faceapi.LabeledFaceDescriptors(label, [arr]);
//            });
//
//            this.faceMatcher = new faceapi.FaceMatcher(labeledDescriptors, 0.45);
//            this.state.statusMessage = "System Ready. Step up to the camera.";
//
//        } catch (error) {
//            console.error(error);
//            this.state.statusMessage = "Error connecting to database.";
//        }
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
//        if (!this.faceMatcher) return;
//
//        this.scanInterval = setInterval(async () => {
//            if (this.state.isProcessing) return;
//
//            const videoEl = this.videoRef.el;
//            const detection = await faceapi.detectSingleFace(videoEl).withFaceLandmarks().withFaceDescriptor();
//
//            if (detection) {
//                const bestMatch = this.faceMatcher.findBestMatch(detection.descriptor);
//
//                if (bestMatch.label !== "unknown") {
//                    this.state.isProcessing = true;
//                    this.state.statusMessage = "Face Verified! Logging attendance...";
//
//                    const splitData = bestMatch.label.split('|');
//                    const employeeId = parseInt(splitData[0]);
//                    const employeeName = splitData[1];
//
//                    await this.triggerPunch(employeeId, employeeName);
//                }
//            }
//        }, 1000);
//    }
//
//    async triggerPunch(employeeId, employeeName) {
//        try {
//            // Trigger the Python punch
//            await this.orm.call("hr.employee", "ai_attendance_manual", [employeeId]);
//
//            this.state.statusMessage = "Please step away from the camera..."; // Tell them to move!
//            this.state.successName = employeeName;
//
//            // Increased to an 8-second cooldown to give them time to walk away
//            setTimeout(() => {
//                this.state.successName = false;
//                this.state.statusMessage = "System Ready. Step up to the camera.";
//                this.state.isProcessing = false; // Scanner turns back on here
//            }, 8000);
//
//        } catch (error) {
//            this.state.statusMessage = "Error logging attendance.";
//            this.state.isProcessing = false;
//        }
//    }
//
//    stopCamera() {
//        if (this.scanInterval) clearInterval(this.scanInterval);
//        if (this.stream) this.stream.getTracks().forEach(track => track.stop());
//    }
//
//    _onCloseClick() {
//        // Bulletproof exit strategy: Force the browser back to the main Odoo dashboard
//        window.location.href = '/odoo';
//    }
//}
//SelfieKiosk.template = "attendance_planning.SelfieKioskScreen";
//registry.category("actions").add("attendance_selfie_kiosk", SelfieKiosk);