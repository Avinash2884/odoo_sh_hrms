// ===========================================================
// Late Checkout JS
// ===========================================================

const TEST_MODE = true;   // 🔥 CHANGE TO true FOR TESTING

console.log("🚀 Late checkout JS loaded");


document.addEventListener("click", function (ev) {

    const btn = ev.target.closest("button.btn.btn-warning");
    if (!btn) return;

    if (btn.innerText.trim() !== "Check out") return;

    console.log("✅ Check out clicked");

    // Allow backend compute
    setTimeout(checkLateCheckout, 5000);
});


/* ===========================================================
   CHECK LATE CHECKOUT
=========================================================== */
async function checkLateCheckout() {

    try {
        console.log("🔎 Checking latest attendance...");

        const attendance = await getLatestAttendance();

        if (!attendance) {
            console.warn("⚠️ No attendance found");
            return;
        }

        console.log("📊 Attendance received:", attendance);

        // ==============================
        // 🔥 TEST MODE
        // ==============================
        if (TEST_MODE) {
            console.warn("⚠️ TEST MODE ACTIVE – forcing popup");
            showLateCheckoutPopup(attendance);
            return;
        }

        // ==============================
        // ✅ PRODUCTION MODE
        // ==============================
        if (attendance.extra_hours > 0) {
            console.log("🕒 Extra hours detected:", attendance.extra_hours);
            showLateCheckoutPopup(attendance);
        } else {
            console.log("🟢 No extra hours – no popup");
        }

    } catch (err) {
        console.error("❌ Error checking late checkout:", err);
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

    console.log("📡 Server response:", data);

    return data.result || null;
}


/* ===========================================================
   POPUP UI
=========================================================== */
function showLateCheckoutPopup(attendance) {

    if (document.querySelector(".late-overlay")) {
        console.warn("⚠️ Popup already open");
        return;
    }

    console.log("📢 Showing late checkout popup");

    const overlay = document.createElement("div");
    overlay.className = "late-overlay";

    const popup = document.createElement("div");
    popup.className = "late-popup";

    popup.innerHTML = `
        <div class="late-popup-header">
            <h3>🕒 Late Checkout</h3>
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

            <div class="late-popup-actions">
                <button id="late_skip">Skip</button>
                <button id="late_submit">Submit</button>
            </div>
        </div>
    `;

    overlay.appendChild(popup);
    document.body.appendChild(overlay);


    // ===== SKIP =====
    document.getElementById("late_skip").onclick = () => {
        console.log("⏭️ Late checkout skipped");
        document.body.removeChild(overlay);
    };


    // ===== SUBMIT =====
    document.getElementById("late_submit").onclick = async () => {

        const reason = document.getElementById("late_reason").value.trim();

        if (!reason) {
            alert("Please enter a reason before submitting.");
            return;
        }

        console.log("📤 Submitting late reason:", reason);

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

            console.log("✅ Late checkout reason saved");
            document.body.removeChild(overlay);

        } catch (err) {
            console.error("❌ Failed to save reason:", err);
        }
    };
}



