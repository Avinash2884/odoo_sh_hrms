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
            if (!videoEl || videoEl.readyState < 2 || !videoEl.videoWidth || !videoEl.videoHeight) {
                return;
            }

            let detection;
            try {
                detection = await faceapi.detectSingleFace(
                    videoEl,
                    new faceapi.TinyFaceDetectorOptions({ inputSize: 224, scoreThreshold: 0.5 })
                ).withFaceLandmarks().withFaceDescriptor();
            } catch (e) {
                console.warn("Face detection skipped this frame:", e);
                return;
            }

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

                        const geoResult = await this.props.geoCheckPromise;

                        if (!geoResult || !geoResult.allowed) {
                            this.state.statusMessage = "❌ " + (geoResult?.message || "You are outside the allowed office location.");
                            console.warn('Geo check failed:', geoResult?.message);
                            this.stopCamera();
                            if (this.props.releaseLock) this.props.releaseLock();
                            setTimeout(() => this.props.close(), 1500);
                            return;
                        }

                        this.state.statusMessage = "✅ Identity Verified! Recording...";
                        this.stopCamera();

                        (async () => {
                            const photoBase64 = this._capturedPhotoBase64;

                            if (photoBase64) {
                                let staged = false;
                                for (let i = 0; i < 2 && !staged; i++) {
                                    try {
                                        await this.orm.call(
                                            'hr.employee',
                                            'stage_attendance_data',
                                            [photoBase64, geoResult.zone_id || false]
                                        );
                                        staged = true;
                                    } catch (e) {
                                        console.warn(`Stage attempt ${i + 1} failed:`, e);
                                    }
                                }

                                if (!staged) {
                                    console.error("❌ Critical: Failed to stage photo after 2 attempts.");
                                }
                            }

                            if (this.props.onSuccess) {
                                await this.props.onSuccess();
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

            // ── DATABASE SYNC 1: Read actual status before punch ──
            try {
                if (this.employee && this.employee.id) {
                    const [fresh] = await this.orm.read(
                        "hr.employee",
                        [this.employee.id],
                        ["attendance_state", "last_attendance_id"]
                    );
                    if (fresh) {
                        Object.assign(this.employee, fresh);
                    }
                }
            } catch (e) {
                console.warn("Could not refresh employee attendance state before punch:", e);
            }

            let currentState = 'checked_out';
            if (this.employee && this.employee.attendance_state) {
                currentState = this.employee.attendance_state;
            } else if (this.attendanceService && this.attendanceService.isCheckedIn) {
                currentState = 'checked_in';
            } else if (this.attendance && this.attendance.attendance_state) {
                currentState = this.attendance.attendance_state;
            }

            const geoCheckPromise = (async () => {
                try {
                    const isBypass = await this.orm.call('hr.attendance', 'is_geo_bypass_employee', []);
                    if (isBypass) {
                        return { allowed: true, zone_id: false };
                    }
                } catch (e) {
                    console.warn("Could not fetch bypass status, proceeding with normal GPS check.");
                }

                let latitude = null;
                let longitude = null;

                try {
                    const position = await new Promise((resolve, reject) => {
                        navigator.geolocation.getCurrentPosition(resolve, reject, {
                            timeout: 15000,
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

            this.dialogService.add(FaceVerificationDialog, {
                attendanceState: currentState,
                geoCheckPromise: geoCheckPromise,
                notificationService: this.notificationService,
                releaseLock: releaseLock,
                onSuccess: async () => {
                    // Trigger Native Punch securely
                    try {
                        await super.signInOut();
                    } catch (e) {
                        console.error("Native punch failed:", e);
                        if (this.notificationService) {
                            this.notificationService.add(
                                "Couldn't record your attendance — your session may already be open. Please refresh the page and try again.",
                                { type: "danger" }
                            );
                        }
                        throw e;
                    }

                    // ── DATABASE SYNC 2: Force UI to update color immediately after punch ──
                    try {
                        if (this.employee && this.employee.id) {
                            const [fresh] = await this.orm.read(
                                "hr.employee",
                                [this.employee.id],
                                ["attendance_state", "last_attendance_id"]
                            );
                            if (fresh) {
                                Object.assign(this.employee, fresh);
                            }
                        }
                    } catch (e) {
                        console.warn("Could not refresh employee attendance state after punch:", e);
                    }

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