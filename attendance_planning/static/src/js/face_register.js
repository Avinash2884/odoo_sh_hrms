/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";

// Increased to 45 seconds for mobile devices on slow 3G/4G networks
const MODEL_LOAD_TIMEOUT_MS = 45000;

export class FaceRegister extends Component {
    setup() {
        this.videoRef = useRef("videoElement");
        this.canvasRef = useRef("canvasElement");
        this.orm = useService("orm");
        this.action = useService("action");

        // We get the employee ID passed from the Python button
        this.employeeId = this.props.action.context.default_employee_id;

        this.state = useState({
            statusMessage: "Downloading AI Engine... Please wait.",
            isReady: false,
        });

        this.stream = null;

        onMounted(async () => {
            await this.injectFaceApiScript();
            const modelsOk = await this.loadModels();
            if (modelsOk) {
                await this.startCamera();
            }
        });

        onWillUnmount(() => {
            this.stopCamera();
        });
    }

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
        const modelPath = '/attendance_planning/static/src/models';
        const timeout = (ms) => new Promise((_, reject) =>
            setTimeout(() => reject(new Error("Timeout")), ms)
        );

        try {
            await Promise.race([
                (async () => {
                    await faceapi.nets.ssdMobilenetv1.loadFromUri(modelPath);
                    await faceapi.nets.faceLandmark68Net.loadFromUri(modelPath);
                    await faceapi.nets.faceRecognitionNet.loadFromUri(modelPath);
                })(),
                timeout(MODEL_LOAD_TIMEOUT_MS),
            ]);

            this.state.statusMessage = "AI Ready! Turning on camera...";
            return true;
        } catch (error) {
            console.error("Model load error:", error);
            this.state.statusMessage = "Network too slow to download AI models. Please use Wi-Fi and try again.";
            return false;
        }
    }

    async startCamera() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.state.statusMessage = "Camera blocked. Ensure you are using HTTPS and a standard browser (Safari/Chrome).";
            return;
        }
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
            if (this.videoRef.el) {
                this.videoRef.el.srcObject = this.stream;
                this.videoRef.el.addEventListener('play', () => {
                    // Instant unlock — no blinking required
                    this.state.isReady = true;
                    this.state.statusMessage = "Ready. Look at the camera and click Capture!";
                });
            }
        } catch (err) {
            console.error("Camera error:", err);
            this.state.statusMessage = "Camera access denied. Please allow permissions in your browser settings.";
        }
    }

    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }
    }

    async _onCaptureClick() {
        const videoEl = this.videoRef.el;

        // 1. FREEZE FRAME: Instantly pause the video and update the text
        videoEl.pause();
        this.state.statusMessage = " Snapshot taken! Analyzing face...";
        this.state.isReady = false;

        // 2. YIELD: Give the browser 50ms to actually render the freeze before the AI locks the CPU
        await new Promise(resolve => setTimeout(resolve, 50));

        let detection;
        try {
            detection = await faceapi.detectSingleFace(videoEl)
                                       .withFaceLandmarks()
                                       .withFaceDescriptor();
        } catch (e) {
            console.warn("Face capture failed:", e);
            this.state.statusMessage = "Hardware error reading camera. Please try again.";
            this.state.isReady = true;
            videoEl.play(); // UNFREEZE on error
            return;
        }

        if (!detection) {
            this.state.statusMessage = "No face detected! Make sure your face is clearly visible.";
            this.state.isReady = true;
            videoEl.play(); // UNFREEZE on error
            return;
        }

        const descriptorArray = Array.from(detection.descriptor);
        const descriptorString = JSON.stringify(descriptorArray);

        try {
            await this.orm.call("hr.employee", "sudo_save_face_by_id", [this.employeeId, descriptorString]);
            this.state.statusMessage = "✅ Face Successfully Saved!";

            setTimeout(() => {
                this._onCancelClick();
            }, 1500);

        } catch (error) {
            console.error("Database Error:", error);
            this.state.statusMessage = "Error saving to database.";
            this.state.isReady = true;
            videoEl.play(); // UNFREEZE on error
        }
    }


    _onCancelClick() {
        this.stopCamera();
        this.action.restore(); // Goes back to the employee form
    }
}

// ── TEMPLATE NAME UPDATED ──
FaceRegister.template = "attendance_planning.FaceRegisterScreen";
registry.category("actions").add("attendance_face_register", FaceRegister);