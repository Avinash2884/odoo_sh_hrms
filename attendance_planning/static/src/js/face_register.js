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

export class FaceRegister extends Component {
    setup() {
        this.videoRef = useRef("videoElement");
        this.canvasRef = useRef("canvasElement");
        this.orm = useService("orm");
        this.action = useService("action");

        // We get the employee ID passed from the Python button
        this.employeeId = this.props.action.context.default_employee_id;

        this.state = useState({
            statusMessage: "Loading AI Models... Please wait.",
            isReady: false,
            needsBlink: true // ---> ADDITION 2: Require blink to unlock the capture button
        });

        this.stream = null;
        this.scanInterval = null; // ---> ADDITION 3: To hold our scanner loop
        this.isEyesClosed = false; // ---> ADDITION 4: Track blink state

        onMounted(async () => {
            await this.injectFaceApiScript();
            await this.loadModels();
            await this.startCamera();
        });

        onWillUnmount(() => {
            this.stopCamera();
        });
    }

    // ADD THIS NEW FUNCTION TO FORCE-LOAD THE SCRIPT
    async injectFaceApiScript() {
        return new Promise((resolve, reject) => {
            if (window.faceapi) {
                return resolve(); // Already loaded!
            }
            this.state.statusMessage = "Downloading AI Engine...";
            const script = document.createElement('script');
            // Bypass the bundler and load the file directly from the server
            script.src = '/attendance_planning/static/src/lib/face-api.js';
            script.onload = () => resolve();
            script.onerror = () => {
                this.state.statusMessage = "Failed to inject face-api.js!";
                reject();
            };
            document.head.appendChild(script);
        });
    }

    async loadModels() {
        try {
            // NOTE: Change 'your_module' to your actual module folder name!
            const modelPath = '/attendance_planning/static/src/models';
            await faceapi.nets.ssdMobilenetv1.loadFromUri(modelPath);
            await faceapi.nets.faceLandmark68Net.loadFromUri(modelPath);
            await faceapi.nets.faceRecognitionNet.loadFromUri(modelPath);

            this.state.statusMessage = "AI Ready! Please BLINK at the camera to unlock."; // Updated message
        } catch (error) {
            console.error(error);
            this.state.statusMessage = "Error loading AI models. Check console.";
        }
    }

    async startCamera() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
            if (this.videoRef.el) {
                this.videoRef.el.srcObject = this.stream;
                // ---> ADDITION 5: Start looking for the blink once video plays
                this.videoRef.el.addEventListener('play', () => this.startLivenessScanner());
            }
        } catch (err) {
            this.state.statusMessage = "Camera access denied or unavailable.";
        }
    }

    // ---> ADDITION 6: The Continuous Liveness Scanner
    startLivenessScanner() {
        this.scanInterval = setInterval(async () => {
            if (!this.state.needsBlink) return; // Stop scanning once they blink

            const videoEl = this.videoRef.el;
            const detection = await faceapi.detectSingleFace(videoEl).withFaceLandmarks();

            if (detection) {
                const leftEye = detection.landmarks.getLeftEye();
                const rightEye = detection.landmarks.getRightEye();

                const leftEAR = getEAR(leftEye);
                const rightEAR = getEAR(rightEye);
                const avgEAR = (leftEAR + rightEAR) / 2.0;

                const BLINK_THRESHOLD = 0.25;

                if (avgEAR < BLINK_THRESHOLD) {
                    this.isEyesClosed = true;
                    this.state.statusMessage = "Blink detected! Unlocking...";
                } else if (this.isEyesClosed && avgEAR >= BLINK_THRESHOLD) {
                    // Blink complete!
                    this.isEyesClosed = false;
                    this.state.needsBlink = false;
                    this.state.isReady = true; // Unlock the capture button
                    this.state.statusMessage = "Liveness verified. Click Capture to save face!";
                    clearInterval(this.scanInterval); // Turn off the scanner to save memory
                }
            }
        }, 200);
    }
    // <--- END ADDITION 6

    stopCamera() {
        if (this.scanInterval) clearInterval(this.scanInterval); // Stop scanner on exit
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }
    }

    async _onCaptureClick() {
        this.state.statusMessage = "Scanning face... Hold still!";
        this.state.isReady = false;

        const videoEl = this.videoRef.el;

        // 1. Tell the AI to find the face and extract the math (descriptor)
        const detection = await faceapi.detectSingleFace(videoEl)
                                       .withFaceLandmarks()
                                       .withFaceDescriptor();

        if (!detection) {
            this.state.statusMessage = "No face detected! Make sure your face is clearly visible.";
            this.state.isReady = true;
            return;
        }

        // 2. Convert the 128 numbers into a string so Python can save it
        const descriptorArray = Array.from(detection.descriptor);
        const descriptorString = JSON.stringify(descriptorArray);

        // 3. Send it to Python via RPC (USING THE SECRET BYPASS)
        try {
            // THE CRITICAL LINE: Make sure it says sudo_save_face_by_id AND passes this.employeeId
            await this.orm.call("hr.employee", "sudo_save_face_by_id", [this.employeeId, descriptorString]);

            this.state.statusMessage = "Face Successfully Saved!";

            // Wait 1.5 seconds, then close the camera and go back
            setTimeout(() => {
                this._onCancelClick();
            }, 1500);

        } catch (error) {
            // If it fails, it prints the real error to your browser console
            console.error("Database Error:", error);
            this.state.statusMessage = "Error saving to database.";
            this.state.isReady = true;
        }
    }

    _onCancelClick() {
        this.stopCamera();
        this.action.restore(); // Goes back to the employee form
    }
}

FaceRegister.template = "your_module.FaceRegisterScreen";
registry.category("actions").add("attendance_face_register", FaceRegister);






///** @odoo-module **/
//
//import { registry } from "@web/core/registry";
//import { useService } from "@web/core/utils/hooks";
//import { Component, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";
//
//export class FaceRegister extends Component {
//    setup() {
//        this.videoRef = useRef("videoElement");
//        this.canvasRef = useRef("canvasElement");
//        this.orm = useService("orm");
//        this.action = useService("action");
//
//        // We get the employee ID passed from the Python button
//        this.employeeId = this.props.action.context.default_employee_id;
//
//        this.state = useState({
//            statusMessage: "Loading AI Models... Please wait.",
//            isReady: false
//        });
//
//        this.stream = null;
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
//    // ADD THIS NEW FUNCTION TO FORCE-LOAD THE SCRIPT
//    async injectFaceApiScript() {
//        return new Promise((resolve, reject) => {
//            if (window.faceapi) {
//                return resolve(); // Already loaded!
//            }
//            this.state.statusMessage = "Downloading AI Engine...";
//            const script = document.createElement('script');
//            // Bypass the bundler and load the file directly from the server
//            script.src = '/attendance_planning/static/src/lib/face-api.js';
//            script.onload = () => resolve();
//            script.onerror = () => {
//                this.state.statusMessage = "Failed to inject face-api.js!";
//                reject();
//            };
//            document.head.appendChild(script);
//        });
//    }
//
//    async loadModels() {
//        try {
//            // NOTE: Change 'your_module' to your actual module folder name!
//            const modelPath = '/attendance_planning/static/src/models';
//            await faceapi.nets.ssdMobilenetv1.loadFromUri(modelPath);
//            await faceapi.nets.faceLandmark68Net.loadFromUri(modelPath);
//            await faceapi.nets.faceRecognitionNet.loadFromUri(modelPath);
//
//            this.state.statusMessage = "AI Ready! Please look at the camera.";
//            this.state.isReady = true;
//        } catch (error) {
//            console.error(error);
//            this.state.statusMessage = "Error loading AI models. Check console.";
//        }
//    }
//
//    async startCamera() {
//        try {
//            this.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
//            if (this.videoRef.el) {
//                this.videoRef.el.srcObject = this.stream;
//            }
//        } catch (err) {
//            this.state.statusMessage = "Camera access denied or unavailable.";
//        }
//    }
//
//    stopCamera() {
//        if (this.stream) {
//            this.stream.getTracks().forEach(track => track.stop());
//        }
//    }
//
//    async _onCaptureClick() {
//        this.state.statusMessage = "Scanning face... Hold still!";
//        this.state.isReady = false;
//
//        const videoEl = this.videoRef.el;
//
//        // 1. Tell the AI to find the face and extract the math (descriptor)
//        const detection = await faceapi.detectSingleFace(videoEl)
//                                       .withFaceLandmarks()
//                                       .withFaceDescriptor();
//
//        if (!detection) {
//            this.state.statusMessage = "No face detected! Make sure your face is clearly visible.";
//            this.state.isReady = true;
//            return;
//        }
//
//        // 2. Convert the 128 numbers into a string so Python can save it
//        const descriptorArray = Array.from(detection.descriptor);
//        const descriptorString = JSON.stringify(descriptorArray);
//
//        // 3. Send it to Python via RPC
//        // 3. Send it to Python via RPC (USING THE SECRET BYPASS)
//        try {
//            // THE CRITICAL LINE: Make sure it says sudo_save_face_by_id AND passes this.employeeId
//            await this.orm.call("hr.employee", "sudo_save_face_by_id", [this.employeeId, descriptorString]);
//
//            this.state.statusMessage = "Face Successfully Saved!";
//
//            // Wait 1.5 seconds, then close the camera and go back
//            setTimeout(() => {
//                this._onCancelClick();
//            }, 1500);
//
//        } catch (error) {
//            // If it fails, it prints the real error to your browser console
//            console.error("Database Error:", error);
//            this.state.statusMessage = "Error saving to database.";
//            this.state.isReady = true;
//        }
//    }
//
//    _onCancelClick() {
//        this.stopCamera();
//        this.action.restore(); // Goes back to the employee form
//    }
//}
//
//FaceRegister.template = "your_module.FaceRegisterScreen";
//registry.category("actions").add("attendance_face_register", FaceRegister);