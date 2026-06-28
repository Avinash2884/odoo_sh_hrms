const TEST_MODE = false;   //  CHANGE TO true FOR TESTING

console.log(" Late checkout JS loaded");

// ---> ADDITION 1: Math helpers for blink calculation
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

document.addEventListener("click", function (ev) {

    // Look for either the specific warning button OR Odoo's standard sign-out icon
    const btn = ev.target.closest("button.btn.btn-warning, .o_hr_attendance_sign_out_icon");
    if (!btn) return;

    // Flexible check: handle "Sign out", "Check out", or just the FontAwesome icon
    const text = btn.innerText.trim().toLowerCase();
    const hasSignOutIcon = btn.querySelector('.fa-sign-out');

    if (!text.includes("check out") && !text.includes("sign out") && !hasSignOutIcon) {
        return;
    }

    console.log(" Check out clicked");

    // Allow backend compute
    setTimeout(checkLateCheckout, 5000);
});

/* ===========================================================
   CHECK LATE CHECKOUT
=========================================================== */
async function checkLateCheckout() {

    try {
        console.log(" Checking latest attendance...");

        const attendance = await getLatestAttendance();

        if (!attendance) {
            console.warn(" No attendance found");
            return;
        }

        console.log(" Attendance received:", attendance);

        // ==============================
        //  TEST MODE
        // ==============================
        if (TEST_MODE) {
            console.warn(" TEST MODE ACTIVE – forcing popup");
            showLateCheckoutPopup(attendance);
            return;
        }

        // ==============================
        //  PRODUCTION MODE
        // ==============================
        if (attendance.extra_hours >= 1) {
            console.log(" Extra hours detected:", attendance.extra_hours);
            showLateCheckoutPopup(attendance);
        } else {
            console.log(" No extra hours – no popup");
        }

    } catch (err) {
        console.error(" Error checking late checkout:", err);
    }
}


/* ===========================================================
   FETCH LATEST ATTENDANCE
=========================================================== */
async function getLatestAttendance() {

    const res = await fetch('/web/dataset/call_kw', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            jsonrpc: '2.0',
            id: Date.now(),
            method: 'call',
            params: {
                model: 'hr.attendance',
                method: 'get_my_latest_attendance',
                args: [],
                kwargs: {}
            }
        })
    });

    const data = await res.json();

    console.log(" Server response:", data);

    return data.result || null;
}


/* ===========================================================
   POPUP UI
=========================================================== */
function showLateCheckoutPopup(attendance) {

    if (document.querySelector(".late-overlay")) {
        console.warn("️ Popup already open");
        return;
    }

    console.log(" Showing late checkout popup");

    const overlay = document.createElement("div");
    overlay.className = "late-overlay";

    const popup = document.createElement("div");
    popup.className = "late-popup";

    // ---> ADDITION 2: Added a camera container and disabled the Submit button by default
    popup.innerHTML = `
        <div class="late-popup-header">
            <h3> Late Checkout</h3>
        </div>

        <div class="late-popup-body">
            <p>
                You worked
                <b>${attendance.extra_hours?.toFixed(2) || "0.00"} hours</b> extra.
                Please mention the reason:
            </p>

            <textarea id="late_reason"
                placeholder="Client call, urgent task, deployment..."
                rows="4"></textarea>

            <div id="late_liveness_container" style="text-align: center; margin-top: 10px;">
                <p id="late_liveness_status" style="font-weight: bold; color: #e67e22;">Initializing Camera...</p>
                <video id="late_liveness_video" autoplay muted playsinline style="width: 100%; max-width: 200px; border-radius: 8px; display: none; margin: 0 auto;"></video>
            </div>

            <div class="late-popup-actions" style="margin-top: 15px;">
                <button id="late_skip">Skip</button>
                <button id="late_submit" disabled style="opacity: 0.5; cursor: not-allowed;">Submit (Awaiting Blink)</button>
            </div>
        </div>
    `;

    overlay.appendChild(popup);
    document.body.appendChild(overlay);

    // ---> ADDITION 3: Camera management variables
    let stream = null;
    let scanInterval = null;

    const stopCamera = () => {
        if (scanInterval) clearInterval(scanInterval);
        if (stream) stream.getTracks().forEach(track => track.stop());
        const videoEl = document.getElementById("late_liveness_video");
        if (videoEl) videoEl.style.display = "none";
    };

    // ===== SKIP =====
    document.getElementById("late_skip").onclick = () => {
        console.log(" Late checkout skipped");
        stopCamera(); // Turn off camera on exit
        document.body.removeChild(overlay);
    };


    // ===== SUBMIT =====
    document.getElementById("late_submit").onclick = async () => {

        const reason = document.getElementById("late_reason").value.trim();

        if (!reason) {
            alert("Please enter a reason before submitting.");
            return;
        }

        console.log(" Submitting late reason:", reason);

        try {
            await fetch('/web/dataset/call_kw', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    id: Date.now(),
                    method: 'call',
                    params: {
                        model: 'hr.attendance',
                        method: 'save_late_reason',
                        args: [reason],
                        kwargs: {}
                    }
                })
            });

            console.log(" Late checkout reason saved");
            stopCamera(); // Turn off camera on successful submit
            document.body.removeChild(overlay);

        } catch (err) {
            console.error(" Failed to save reason:", err);
        }
    };

    // ---> ADDITION 4: Boot up the liveness scanner and unlock the submit button upon blink
    const initLivenessScanner = async () => {
        const statusText = document.getElementById("late_liveness_status");
        const videoEl = document.getElementById("late_liveness_video");
        const submitBtn = document.getElementById("late_submit");

        try {
            if (!window.faceapi) {
                statusText.innerText = "Downloading AI Engine...";
                await new Promise((resolve, reject) => {
                    const script = document.createElement('script');
                    script.src = '/attendance_planning/static/src/lib/face-api.js';
                    script.onload = resolve;
                    script.onerror = reject;
                    document.head.appendChild(script);
                });
            }

            statusText.innerText = "Loading Liveness AI...";
            const modelPath = '/attendance_planning/static/src/models';

            // Only loading detection and landmarks. Recognition is not needed for a simple blink!
            await faceapi.nets.ssdMobilenetv1.loadFromUri(modelPath);
            await faceapi.nets.faceLandmark68Net.loadFromUri(modelPath);

            stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
            videoEl.srcObject = stream;
            videoEl.style.display = "block";

            statusText.innerText = "Please BLINK to unlock Submit button!";

            videoEl.addEventListener('play', () => {
                let isEyesClosed = false;

                scanInterval = setInterval(async () => {
                    const detection = await faceapi.detectSingleFace(videoEl).withFaceLandmarks();

                    if (detection) {
                        const leftEye = detection.landmarks.getLeftEye();
                        const rightEye = detection.landmarks.getRightEye();

                        const avgEAR = (getEAR(leftEye) + getEAR(rightEye)) / 2.0;

                        if (avgEAR < 0.25) {
                            isEyesClosed = true;
                            statusText.innerText = "Blink detected! Unlocking...";
                        } else if (isEyesClosed && avgEAR >= 0.25) {
                            // Blink complete! Unlock the system.
                            clearInterval(scanInterval);
                            isEyesClosed = false;

                            statusText.innerText = "✅ Liveness Verified!";
                            statusText.style.color = "#27ae60"; // Green

                            // Enable the submit button
                            submitBtn.disabled = false;
                            submitBtn.style.opacity = "1";
                            submitBtn.style.cursor = "pointer";
                            submitBtn.innerText = "Submit";

                            // Turn off the camera to get it out of the way
                            setTimeout(stopCamera, 1000);
                        }
                    }
                }, 200);
            });

        } catch (err) {
            console.error("Camera/AI error:", err);
            statusText.innerText = "Liveness check unavailable. Proceed manually.";
            // Fallback: unlock it anyway if their webcam breaks so they aren't stuck
            submitBtn.disabled = false;
            submitBtn.style.opacity = "1";
            submitBtn.style.cursor = "pointer";
            submitBtn.innerText = "Submit";
        }
    };

    initLivenessScanner();
    // <--- END ADDITION 4
}










//
//
//const TEST_MODE = false;   //  CHANGE TO true FOR TESTING
//
//console.log(" Late checkout JS loaded");
//
//
//document.addEventListener("click", function (ev) {
//
//    // Look for either the specific warning button OR Odoo's standard sign-out icon
//    const btn = ev.target.closest("button.btn.btn-warning, .o_hr_attendance_sign_out_icon");
//    if (!btn) return;
//
//    // Flexible check: handle "Sign out", "Check out", or just the FontAwesome icon
//    const text = btn.innerText.trim().toLowerCase();
//    const hasSignOutIcon = btn.querySelector('.fa-sign-out');
//
//    if (!text.includes("check out") && !text.includes("sign out") && !hasSignOutIcon) {
//        return;
//    }
//
//    console.log(" Check out clicked");
//
//    // Allow backend compute
//    setTimeout(checkLateCheckout, 5000);
//});
//
///* ===========================================================
//   CHECK LATE CHECKOUT
//=========================================================== */
//async function checkLateCheckout() {
//
//    try {
//        console.log(" Checking latest attendance...");
//
//        const attendance = await getLatestAttendance();
//
//        if (!attendance) {
//            console.warn(" No attendance found");
//            return;
//        }
//
//        console.log(" Attendance received:", attendance);
//
//        // ==============================
//        //  TEST MODE
//        // ==============================
//        if (TEST_MODE) {
//            console.warn(" TEST MODE ACTIVE – forcing popup");
//            showLateCheckoutPopup(attendance);
//            return;
//        }
//
//        // ==============================
//        //  PRODUCTION MODE
//        // ==============================
//        if (attendance.extra_hours >= 1) {
//            console.log(" Extra hours detected:", attendance.extra_hours);
//            showLateCheckoutPopup(attendance);
//        } else {
//            console.log(" No extra hours – no popup");
//        }
//
//    } catch (err) {
//        console.error(" Error checking late checkout:", err);
//    }
//}
//
//
///* ===========================================================
//   FETCH LATEST ATTENDANCE
//=========================================================== */
//async function getLatestAttendance() {
//
//    const res = await fetch('/web/dataset/call_kw', {
//        method: 'POST',
//        headers: { 'Content-Type': 'application/json' },
//        body: JSON.stringify({
//            jsonrpc: '2.0',
//            id: Date.now(),
//            method: 'call',
//            params: {
//                model: 'hr.attendance',
//                method: 'get_my_latest_attendance',
//                args: [],
//                kwargs: {}
//            }
//        })
//    });
//
//    const data = await res.json();
//
//    console.log(" Server response:", data);
//
//    return data.result || null;
//}
//
//
///* ===========================================================
//   POPUP UI
//=========================================================== */
//function showLateCheckoutPopup(attendance) {
//
//    if (document.querySelector(".late-overlay")) {
//        console.warn("️ Popup already open");
//        return;
//    }
//
//    console.log(" Showing late checkout popup");
//
//    const overlay = document.createElement("div");
//    overlay.className = "late-overlay";
//
//    const popup = document.createElement("div");
//    popup.className = "late-popup";
//
//    popup.innerHTML = `
//        <div class="late-popup-header">
//            <h3> Late Checkout</h3>
//        </div>
//
//        <div class="late-popup-body">
//            <p>
//                You worked
//                <b>${attendance.extra_hours?.toFixed(2) || "0.00"} hours</b> extra.
//                Please mention the reason:
//            </p>
//
//            <textarea id="late_reason"
//                placeholder="Client call, urgent task, deployment..."
//                rows="4"></textarea>
//
//            <div class="late-popup-actions">
//                <button id="late_skip">Skip</button>
//                <button id="late_submit">Submit</button>
//            </div>
//        </div>
//    `;
//
//    overlay.appendChild(popup);
//    document.body.appendChild(overlay);
//
//
//    // ===== SKIP =====
//    document.getElementById("late_skip").onclick = () => {
//        console.log(" Late checkout skipped");
//        document.body.removeChild(overlay);
//    };
//
//
//    // ===== SUBMIT =====
//    document.getElementById("late_submit").onclick = async () => {
//
//        const reason = document.getElementById("late_reason").value.trim();
//
//        if (!reason) {
//            alert("Please enter a reason before submitting.");
//            return;
//        }
//
//        console.log(" Submitting late reason:", reason);
//
//        try {
//            await fetch('/web/dataset/call_kw', {
//                method: 'POST',
//                headers: { 'Content-Type': 'application/json' },
//                body: JSON.stringify({
//                    jsonrpc: '2.0',
//                    id: Date.now(),
//                    method: 'call',
//                    params: {
//                        model: 'hr.attendance',
//                        method: 'save_late_reason',
//                        args: [reason],
//                        kwargs: {}
//                    }
//                })
//            });
//
//            console.log(" Late checkout reason saved");
//            document.body.removeChild(overlay);
//
//        } catch (err) {
//            console.error(" Failed to save reason:", err);
//        }
//    };
//}
//
//
//
