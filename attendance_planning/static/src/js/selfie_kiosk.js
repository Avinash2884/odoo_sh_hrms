/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";

export class SelfieKiosk extends Component {
    setup() {
        this.videoRef = useRef("videoElement");
        this.canvasRef = useRef("canvasElement");
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            statusMessage: "Downloading AI Engine... Please wait.",
            successName: false,
            isProcessing: false // Stops it from punching 10 times a second
        });

        this.stream = null;
        this.faceMatcher = null;
        this.scanInterval = null;

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

        this.scanInterval = setInterval(async () => {
            if (this.state.isProcessing) return;

            const videoEl = this.videoRef.el;
            const detection = await faceapi.detectSingleFace(videoEl).withFaceLandmarks().withFaceDescriptor();

            if (detection) {
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
        }, 1000);
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
            }, 8000);

        } catch (error) {
            this.state.statusMessage = "Error logging attendance.";
            this.state.isProcessing = false;
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