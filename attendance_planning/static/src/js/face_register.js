/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";

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
            isReady: false
        });

        this.stream = null;

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

            this.state.statusMessage = "AI Ready! Please look at the camera.";
            this.state.isReady = true;
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
            }
        } catch (err) {
            this.state.statusMessage = "Camera access denied or unavailable.";
        }
    }

    stopCamera() {
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

        // 3. Send it to Python via RPC
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