/* ===========================================================
   AUTO CHECKOUT REMINDER
   -----------------------------------------------------------
   PHASE 1 — 15 minutes after shift end, if the employee is still
   checked in, a popup asks every 1 minute: "Are you working extra
   hours?"
     - Yes            -> dismiss, move to PHASE 2 (below). No more
                         popups until the 4-hour OT cap.
     - No             -> checkout immediately right now
     - Ignored 15x     -> after 15 ignored popups (~15 min), the
                         system force-checks-out the employee AND
                         stamps the record "No Response" (NR) so it
                         is held out of automatic P/OT pay until a
                         manager reviews it.

   PHASE 2 — OT cap (only reached if they said "Yes" in phase 1).
   4 hours of extra time is the max. From (shift end + 4h):
     - Stays silent until the cap is hit (no nagging during normal OT).
     - After the cap is hit, stays silent for another 30 minutes.
     - Then a "please check out now" popup shows every 3 minutes, up to
       5 times.
     - If they check out themselves any time -> normal flow, extra_hours
       already >=4 so it lands in the EXISTING pending-manager-approval
       state (unchanged behavior, no new flag needed).
     - If still ignored after 5 nudges (~15 min) -> force checkout
       automatically. NOT flagged NR (they already responded once in
       phase 1) — it just lands in the same pending-approval state.

   PUSH NOTIFICATIONS — alongside every in-browser popup tick in both
   phases, a real phone push is also fired via send_checkout_push_reminder
   (fire-and-forget, never blocks the flow if it fails). This is what
   lets the reminder reach a closed/backgrounded Odoo mobile app instead
   of only working while this browser tab is open and visible.

   This file only ever READS attendance state and, for forced
   checkouts, calls one dedicated RPC to close the open session. It
   does not touch the existing post-checkout "late reason" popup
   (late_checkout_popup.js) or any other flow.
=========================================================== */

const AUTO_CO_POLL_MS = 60 * 1000;       // check every 1 minute
const AUTO_CO_GRACE_MS = 15 * 60 * 1000; // start nudging 15 min after shift end
const AUTO_CO_MAX_IGNORES = 15;          // force checkout after 15 ignored popups (~15 min)

// PHASE 2 — OT cap settings
const OT_CAP_MS = 4 * 60 * 60 * 1000;         // 4 hours of extra time allowed, counted from shift end
const OT_GRACE_MS = 30 * 60 * 1000;           // stay silent for 30 min AFTER hitting the cap, before nudging starts
const OT_POPUP_INTERVAL_MS = 3 * 60 * 1000;   // then nudge every 3 minutes
const OT_MAX_POPUPS = 5;                      // after 5 ignored nudges (~15 min), force checkout

// TEST MODE (mirrors the server's attendance_planning.auto_checkout_test_mode
// parameter): when the server says test_mode=true, use these instead, so the
// whole flow (nudge -> ignore -> force checkout) finishes in a couple minutes.
const TEST_GRACE_MS = 0;      // no wait after "shift end" (which is check_in + 1 min)
const TEST_MAX_IGNORES = 2;   // force checkout after just 2 ignored popups
const TEST_OT_CAP_MS = 60 * 1000;            // "4 hours" becomes 1 minute in test mode
const TEST_OT_GRACE_MS = 15 * 1000;          // "30 minutes" becomes 15 seconds
const TEST_OT_POPUP_INTERVAL_MS = 10 * 1000; // "3 minutes" becomes 10 seconds
const TEST_OT_MAX_POPUPS = 2;                // force checkout after just 2 ignored nudges

let _ignoreCount = 0;
let _popupOpenForAttendanceId = null;
let _mutedAttendanceId = null;   // set after employee taps "Yes" in phase 1
let _otPopupLastShownAt = 0;     // throttle for the phase-2 OT-limit popup
let _otPopupCount = 0;           // how many OT-limit popups shown/ignored so far

async function _rpc(model, method, args = []) {
    const res = await fetch('/web/dataset/call_kw', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            jsonrpc: '2.0',
            id: Date.now(),
            method: 'call',
            params: { model, method, args, kwargs: {} },
        }),
    });
    const data = await res.json();
    if (data.error) {
        // Surface the real Odoo error instead of failing silently.
        const msg = data.error.data?.message || data.error.message || 'Unknown server error';
        console.error('Auto checkout RPC error:', data.error);
        throw new Error(msg);
    }
    return data.result;
}

// Fire-and-forget real phone push. Never blocks or throws into the
// caller — a push failure must never interrupt the reminder/checkout flow.
function _sendPush(attendanceId, stage) {
    _rpc('hr.attendance', 'send_checkout_push_reminder', [attendanceId, stage])
        .catch((err) => console.error('Push reminder failed:', err));
}

async function pollAutoCheckoutReminder() {
    let testModeThisTick = false;
    try {
        const info = await _rpc('hr.attendance', 'get_open_session_reminder_info');

        if (!info) {
            // Not checked in (or already checked out) — reset and wait for next poll.
            _ignoreCount = 0;
            _popupOpenForAttendanceId = null;
            _mutedAttendanceId = null;
            _otPopupLastShownAt = 0;
            _otPopupCount = 0;
            closeReminderPopup();
            scheduleNextPoll(testModeThisTick);
            return;
        }

        testModeThisTick = !!info.test_mode;

        const shiftEnd = new Date(info.shift_end + 'Z');
        const serverNow = new Date(info.server_now + 'Z');

        if (_mutedAttendanceId === info.attendance_id) {
            // Phase 2: they already said "Yes" in phase 1 for this session.
            await handleOtCapPhase(info, shiftEnd, serverNow, testModeThisTick);
            scheduleNextPoll(testModeThisTick);
            return;
        }

        // ---- Phase 1 ----
        const graceMs = info.test_mode ? TEST_GRACE_MS : AUTO_CO_GRACE_MS;
        const maxIgnores = info.test_mode ? TEST_MAX_IGNORES : AUTO_CO_MAX_IGNORES;
        const dueAt = new Date(shiftEnd.getTime() + graceMs);

        if (serverNow < dueAt) {
            scheduleNextPoll(testModeThisTick);
            return; // still within shift / grace window, nothing to do yet
        }

        if (_popupOpenForAttendanceId !== info.attendance_id) {
            // New session hitting the window for the first time this run
            _ignoreCount = 0;
            _popupOpenForAttendanceId = info.attendance_id;
        }

        // Real phone push, once per poll tick (~1/min) — matches the popup's
        // own nagging cadence exactly. Fire-and-forget: never blocks the flow.
        _sendPush(info.attendance_id, 'shift_end');

        if (document.querySelector('.auto-co-overlay')) {
            // Popup already open from the previous tick — this tick counts as "ignored"
            _ignoreCount += 1;
        } else {
            showAutoCheckoutPopup(info.attendance_id);
        }

        if (_ignoreCount >= maxIgnores) {
            closeReminderPopup();
            try {
                const result = await _rpc('hr.attendance', 'force_auto_checkout_no_response', [info.attendance_id]);
                if (result && result.success) {
                    notifyForcedCheckout();
                }
            } catch (err) {
                console.error('Forced auto-checkout failed:', err);
            }
            _ignoreCount = 0;
            _popupOpenForAttendanceId = null;
        }
    } catch (err) {
        console.error('Auto checkout reminder error:', err);
    }
    scheduleNextPoll(testModeThisTick);
}

// PHASE 2: employee already said "Yes" — enforce the 4-hour OT cap.
// Stay fully silent for 30 min after hitting the cap, THEN nudge every
// 3 min, up to 5 times; if still ignored, force checkout (no NR — they
// already responded once in phase 1).
async function handleOtCapPhase(info, shiftEnd, serverNow, testMode) {
    const otCapMs = testMode ? TEST_OT_CAP_MS : OT_CAP_MS;
    const otGraceMs = testMode ? TEST_OT_GRACE_MS : OT_GRACE_MS;
    const otPopupIntervalMs = testMode ? TEST_OT_POPUP_INTERVAL_MS : OT_POPUP_INTERVAL_MS;
    const otMaxPopups = testMode ? TEST_OT_MAX_POPUPS : OT_MAX_POPUPS;

    const otCapAt = new Date(shiftEnd.getTime() + otCapMs);
    if (serverNow < otCapAt) {
        return; // still within the 4-hour OT allowance — stay silent
    }

    const otNudgeStartAt = new Date(otCapAt.getTime() + otGraceMs);
    if (serverNow < otNudgeStartAt) {
        return; // cap hit, but still inside the 30-min silent grace — no popup yet
    }

    const now = Date.now();
    if (document.querySelector('.ot-limit-overlay')) {
        // Popup still open/unanswered — once the interval has elapsed,
        // this counts as one more ignored nudge.
        if (now - _otPopupLastShownAt >= otPopupIntervalMs) {
            _otPopupCount += 1;
            _otPopupLastShownAt = now;
            _sendPush(info.attendance_id, 'ot_cap');
        }
    } else {
        _otPopupCount += 1;
        _otPopupLastShownAt = now;
        showOtLimitPopup(info.attendance_id);
        _sendPush(info.attendance_id, 'ot_cap');
    }

    if (_otPopupCount >= otMaxPopups) {
        // Fully ignored — force checkout. Lands in the normal pending-
        // OT-approval state since extra_hours is already >= 4.
        closeOtLimitPopup();
        try {
            const result = await _rpc('hr.attendance', 'checkout_now_explicit_no', [info.attendance_id]);
            if (result && result.success) {
                notifyOtLimitCheckout();
            }
        } catch (err) {
            console.error('OT-limit forced checkout failed:', err);
        }
        _mutedAttendanceId = null;
        _otPopupLastShownAt = 0;
        _otPopupCount = 0;
    }
}

function scheduleNextPoll(testMode) {
    const delay = testMode ? (15 * 1000) : AUTO_CO_POLL_MS;
    setTimeout(pollAutoCheckoutReminder, delay);
}

function closeReminderPopup() {
    const overlay = document.querySelector('.auto-co-overlay');
    if (overlay) overlay.remove();
}

function closeOtLimitPopup() {
    const overlay = document.querySelector('.ot-limit-overlay');
    if (overlay) overlay.remove();
}

function showAutoCheckoutPopup(attendanceId) {
    if (document.querySelector('.auto-co-overlay')) return;

    const overlay = document.createElement('div');
    overlay.className = 'late-overlay auto-co-overlay';

    const popup = document.createElement('div');
    popup.className = 'late-popup auto-co-popup';

    popup.innerHTML = `
        <div class="late-popup-header auto-co-header">
            <h3>You haven't checked out</h3>
        </div>
        <div class="late-popup-body">
            <p>Your shift has ended. Are you working extra hours?</p>
            <div class="late-popup-actions" style="margin-top: 15px;">
                <button id="auto_co_no">No, check me out</button>
                <button id="auto_co_yes">Yes, still working</button>
            </div>
        </div>
    `;

    overlay.appendChild(popup);
    document.body.appendChild(overlay);

    document.getElementById('auto_co_yes').onclick = async () => {
        const btn = document.getElementById('auto_co_yes');
        btn.disabled = true;
        try {
            await _rpc('hr.attendance', 'keep_working_ping', [attendanceId]);
            _mutedAttendanceId = attendanceId; // move to phase 2 (OT cap) for this session
            _ignoreCount = 0;
            _otPopupCount = 0;
            _otPopupLastShownAt = 0;
            closeReminderPopup();
        } catch (err) {
            btn.disabled = false;
            alert('Could not record your response: ' + err.message + '\nPlease try again.');
        }
    };

    document.getElementById('auto_co_no').onclick = async () => {
        const btn = document.getElementById('auto_co_no');
        btn.disabled = true;
        try {
            // Explicit "No" is a real answer -> plain checkout, no NR flag.
            const result = await _rpc('hr.attendance', 'checkout_now_explicit_no', [attendanceId]);
            if (!result || !result.success) {
                throw new Error((result && result.error) || 'Checkout failed for an unknown reason.');
            }
            closeReminderPopup();
            _ignoreCount = 0;
            _popupOpenForAttendanceId = null;
            _mutedAttendanceId = null;
            window.location.reload(); // refresh so Check-In/status widgets update immediately
        } catch (err) {
            btn.disabled = false;
            alert('Could not check you out automatically: ' + err.message +
                  '\nPlease use the Check Out button instead.');
        }
    };
}

function notifyForcedCheckout() {
    const note = document.createElement('div');
    note.className = 'auto-co-toast';
    note.textContent = 'You were automatically checked out after not responding. Your manager will review this entry.';
    document.body.appendChild(note);
    // Give the employee a couple seconds to actually read the toast,
    // then refresh so the Check-In/status widgets reflect the new state.
    setTimeout(() => window.location.reload(), 2500);
}

// ---- Phase 2 UI: OT-limit popup + toast ----

function showOtLimitPopup(attendanceId) {
    if (document.querySelector('.ot-limit-overlay')) return;

    const overlay = document.createElement('div');
    overlay.className = 'late-overlay ot-limit-overlay';

    const popup = document.createElement('div');
    popup.className = 'late-popup ot-limit-popup';

    popup.innerHTML = `
        <div class="late-popup-header auto-co-header">
            <h3>Maximum extra hours reached</h3>
        </div>
        <div class="late-popup-body">
            <p>You've reached the 4-hour extra-time limit. Please check out now.</p>
            <div class="late-popup-actions" style="margin-top: 15px;">
                <button id="ot_limit_checkout">Check out now</button>
            </div>
        </div>
    `;

    overlay.appendChild(popup);
    document.body.appendChild(overlay);

    document.getElementById('ot_limit_checkout').onclick = async () => {
        const btn = document.getElementById('ot_limit_checkout');
        btn.disabled = true;
        try {
            const result = await _rpc('hr.attendance', 'checkout_now_explicit_no', [attendanceId]);
            if (!result || !result.success) {
                throw new Error((result && result.error) || 'Checkout failed for an unknown reason.');
            }
            closeOtLimitPopup();
            _mutedAttendanceId = null;
            _otPopupLastShownAt = 0;
            _otPopupCount = 0;
            window.location.reload();
        } catch (err) {
            btn.disabled = false;
            alert('Could not check you out automatically: ' + err.message +
                  '\nPlease use the Check Out button instead.');
        }
    };
}

function notifyOtLimitCheckout() {
    const note = document.createElement('div');
    note.className = 'auto-co-toast';
    note.textContent = 'You were automatically checked out after reaching the 4-hour extra-time limit. Your manager will review the extra hours for approval.';
    document.body.appendChild(note);
    setTimeout(() => window.location.reload(), 2500);
}

setTimeout(pollAutoCheckoutReminder, 5000);

window.pollAutoCheckoutReminder = pollAutoCheckoutReminder;











///* ===========================================================
//   AUTO CHECKOUT REMINDER
//   -----------------------------------------------------------
//   PHASE 1 — 15 minutes after shift end, if the employee is still
//   checked in, a popup asks every 1 minute: "Are you working extra
//   hours?"
//     - Yes            -> dismiss, move to PHASE 2 (below). No more
//                         popups until the 4-hour OT cap.
//     - No             -> checkout immediately right now
//     - Ignored 15x     -> after 15 ignored popups (~15 min), the
//                         system force-checks-out the employee AND
//                         stamps the record "No Response" (NR) so it
//                         is held out of automatic P/OT pay until a
//                         manager reviews it.
//
//   PHASE 2 — OT cap (only reached if they said "Yes" in phase 1).
//   4 hours of extra time is the max. From (shift end + 4h):
//     - Stays silent until the cap is hit (no nagging during normal OT).
//     - Once the 4h cap is hit, a "please check out now" popup shows
//       every 3 minutes, up to 5 times.
//     - If they check out themselves any time -> normal flow, extra_hours
//       already >=4 so it lands in the EXISTING pending-manager-approval
//       state (unchanged behavior, no new flag needed).
//     - If still ignored after 5 nudges (~15 min) -> force checkout
//       automatically. NOT flagged NR (they already responded once in
//       phase 1) — it just lands in the same pending-approval state.
//
//   PUSH NOTIFICATIONS — alongside every in-browser popup tick in both
//   phases, a real phone push is also fired via send_checkout_push_reminder
//   (fire-and-forget, never blocks the flow if it fails). This is what
//   lets the reminder reach a closed/backgrounded Odoo mobile app instead
//   of only working while this browser tab is open and visible.
//
//   This file only ever READS attendance state and, for forced
//   checkouts, calls one dedicated RPC to close the open session. It
//   does not touch the existing post-checkout "late reason" popup
//   (late_checkout_popup.js) or any other flow.
//=========================================================== */
//
//const AUTO_CO_POLL_MS = 60 * 1000;       // check every 1 minute
//const AUTO_CO_GRACE_MS = 15 * 60 * 1000; // start nudging 15 min after shift end
//const AUTO_CO_MAX_IGNORES = 15;          // force checkout after 15 ignored popups (~15 min)
//
//// PHASE 2 — OT cap settings
//const OT_CAP_MS = 4 * 60 * 60 * 1000;         // 4 hours of extra time allowed, counted from shift end
//const OT_POPUP_INTERVAL_MS = 3 * 60 * 1000;   // nudge every 3 minutes once the cap is hit
//const OT_MAX_POPUPS = 5;                      // after 5 ignored nudges (~15 min), force checkout
//
//// TEST MODE (mirrors the server's attendance_planning.auto_checkout_test_mode
//// parameter): when the server says test_mode=true, use these instead, so the
//// whole flow (nudge -> ignore -> force checkout) finishes in a couple minutes.
//const TEST_GRACE_MS = 0;      // no wait after "shift end" (which is check_in + 1 min)
//const TEST_MAX_IGNORES = 2;   // force checkout after just 2 ignored popups
//const TEST_OT_CAP_MS = 60 * 1000;            // "4 hours" becomes 1 minute in test mode
//const TEST_OT_POPUP_INTERVAL_MS = 10 * 1000; // "3 minutes" becomes 10 seconds
//const TEST_OT_MAX_POPUPS = 2;                // force checkout after just 2 ignored nudges
//
//let _ignoreCount = 0;
//let _popupOpenForAttendanceId = null;
//let _mutedAttendanceId = null;   // set after employee taps "Yes" in phase 1
//let _otPopupLastShownAt = 0;     // throttle for the phase-2 OT-limit popup
//let _otPopupCount = 0;           // how many OT-limit popups shown/ignored so far
//
//async function _rpc(model, method, args = []) {
//    const res = await fetch('/web/dataset/call_kw', {
//        method: 'POST',
//        headers: { 'Content-Type': 'application/json' },
//        body: JSON.stringify({
//            jsonrpc: '2.0',
//            id: Date.now(),
//            method: 'call',
//            params: { model, method, args, kwargs: {} },
//        }),
//    });
//    const data = await res.json();
//    if (data.error) {
//        // Surface the real Odoo error instead of failing silently.
//        const msg = data.error.data?.message || data.error.message || 'Unknown server error';
//        console.error('Auto checkout RPC error:', data.error);
//        throw new Error(msg);
//    }
//    return data.result;
//}
//
//// Fire-and-forget real phone push. Never blocks or throws into the
//// caller — a push failure must never interrupt the reminder/checkout flow.
//function _sendPush(attendanceId, stage) {
//    _rpc('hr.attendance', 'send_checkout_push_reminder', [attendanceId, stage])
//        .catch((err) => console.error('Push reminder failed:', err));
//}
//
//async function pollAutoCheckoutReminder() {
//    let testModeThisTick = false;
//    try {
//        const info = await _rpc('hr.attendance', 'get_open_session_reminder_info');
//
//        if (!info) {
//            // Not checked in (or already checked out) — reset and wait for next poll.
//            _ignoreCount = 0;
//            _popupOpenForAttendanceId = null;
//            _mutedAttendanceId = null;
//            _otPopupLastShownAt = 0;
//            _otPopupCount = 0;
//            closeReminderPopup();
//            scheduleNextPoll(testModeThisTick);
//            return;
//        }
//
//        testModeThisTick = !!info.test_mode;
//
//        const shiftEnd = new Date(info.shift_end + 'Z');
//        const serverNow = new Date(info.server_now + 'Z');
//
//        if (_mutedAttendanceId === info.attendance_id) {
//            // Phase 2: they already said "Yes" in phase 1 for this session.
//            await handleOtCapPhase(info, shiftEnd, serverNow, testModeThisTick);
//            scheduleNextPoll(testModeThisTick);
//            return;
//        }
//
//        // ---- Phase 1 ----
//        const graceMs = info.test_mode ? TEST_GRACE_MS : AUTO_CO_GRACE_MS;
//        const maxIgnores = info.test_mode ? TEST_MAX_IGNORES : AUTO_CO_MAX_IGNORES;
//        const dueAt = new Date(shiftEnd.getTime() + graceMs);
//
//        if (serverNow < dueAt) {
//            scheduleNextPoll(testModeThisTick);
//            return; // still within shift / grace window, nothing to do yet
//        }
//
//        if (_popupOpenForAttendanceId !== info.attendance_id) {
//            // New session hitting the window for the first time this run
//            _ignoreCount = 0;
//            _popupOpenForAttendanceId = info.attendance_id;
//        }
//
//        // Real phone push, once per poll tick (~1/min) — matches the popup's
//        // own nagging cadence exactly. Fire-and-forget: never blocks the flow.
//        _sendPush(info.attendance_id, 'shift_end');
//
//        if (document.querySelector('.auto-co-overlay')) {
//            // Popup already open from the previous tick — this tick counts as "ignored"
//            _ignoreCount += 1;
//        } else {
//            showAutoCheckoutPopup(info.attendance_id);
//        }
//
//        if (_ignoreCount >= maxIgnores) {
//            closeReminderPopup();
//            try {
//                const result = await _rpc('hr.attendance', 'force_auto_checkout_no_response', [info.attendance_id]);
//                if (result && result.success) {
//                    notifyForcedCheckout();
//                }
//            } catch (err) {
//                console.error('Forced auto-checkout failed:', err);
//            }
//            _ignoreCount = 0;
//            _popupOpenForAttendanceId = null;
//        }
//    } catch (err) {
//        console.error('Auto checkout reminder error:', err);
//    }
//    scheduleNextPoll(testModeThisTick);
//}
//
//// PHASE 2: employee already said "Yes" — enforce the 4-hour OT cap.
//// After the cap, nudge every 3 min, up to 5 times; if still ignored,
//// force checkout (no NR — they already responded once in phase 1).
//async function handleOtCapPhase(info, shiftEnd, serverNow, testMode) {
//    const otCapMs = testMode ? TEST_OT_CAP_MS : OT_CAP_MS;
//    const otPopupIntervalMs = testMode ? TEST_OT_POPUP_INTERVAL_MS : OT_POPUP_INTERVAL_MS;
//    const otMaxPopups = testMode ? TEST_OT_MAX_POPUPS : OT_MAX_POPUPS;
//
//    const otCapAt = new Date(shiftEnd.getTime() + otCapMs);
//    if (serverNow < otCapAt) {
//        return; // still within the 4-hour OT allowance — stay silent
//    }
//
//    const now = Date.now();
//    if (document.querySelector('.ot-limit-overlay')) {
//        // Popup still open/unanswered — once the interval has elapsed,
//        // this counts as one more ignored nudge.
//        if (now - _otPopupLastShownAt >= otPopupIntervalMs) {
//            _otPopupCount += 1;
//            _otPopupLastShownAt = now;
//            _sendPush(info.attendance_id, 'ot_cap');
//        }
//    } else {
//        _otPopupCount += 1;
//        _otPopupLastShownAt = now;
//        showOtLimitPopup(info.attendance_id);
//        _sendPush(info.attendance_id, 'ot_cap');
//    }
//
//    if (_otPopupCount >= otMaxPopups) {
//        // Fully ignored — force checkout. Lands in the normal pending-
//        // OT-approval state since extra_hours is already >= 4.
//        closeOtLimitPopup();
//        try {
//            const result = await _rpc('hr.attendance', 'checkout_now_explicit_no', [info.attendance_id]);
//            if (result && result.success) {
//                notifyOtLimitCheckout();
//            }
//        } catch (err) {
//            console.error('OT-limit forced checkout failed:', err);
//        }
//        _mutedAttendanceId = null;
//        _otPopupLastShownAt = 0;
//        _otPopupCount = 0;
//    }
//}
//
//function scheduleNextPoll(testMode) {
//    const delay = testMode ? (15 * 1000) : AUTO_CO_POLL_MS;
//    setTimeout(pollAutoCheckoutReminder, delay);
//}
//
//function closeReminderPopup() {
//    const overlay = document.querySelector('.auto-co-overlay');
//    if (overlay) overlay.remove();
//}
//
//function closeOtLimitPopup() {
//    const overlay = document.querySelector('.ot-limit-overlay');
//    if (overlay) overlay.remove();
//}
//
//function showAutoCheckoutPopup(attendanceId) {
//    if (document.querySelector('.auto-co-overlay')) return;
//
//    const overlay = document.createElement('div');
//    overlay.className = 'late-overlay auto-co-overlay';
//
//    const popup = document.createElement('div');
//    popup.className = 'late-popup auto-co-popup';
//
//    popup.innerHTML = `
//        <div class="late-popup-header auto-co-header">
//            <h3>You haven't checked out</h3>
//        </div>
//        <div class="late-popup-body">
//            <p>Your shift has ended. Are you working extra hours?</p>
//            <div class="late-popup-actions" style="margin-top: 15px;">
//                <button id="auto_co_no">No, check me out</button>
//                <button id="auto_co_yes">Yes, still working</button>
//            </div>
//        </div>
//    `;
//
//    overlay.appendChild(popup);
//    document.body.appendChild(overlay);
//
//    document.getElementById('auto_co_yes').onclick = async () => {
//        const btn = document.getElementById('auto_co_yes');
//        btn.disabled = true;
//        try {
//            await _rpc('hr.attendance', 'keep_working_ping', [attendanceId]);
//            _mutedAttendanceId = attendanceId; // move to phase 2 (OT cap) for this session
//            _ignoreCount = 0;
//            _otPopupCount = 0;
//            _otPopupLastShownAt = 0;
//            closeReminderPopup();
//        } catch (err) {
//            btn.disabled = false;
//            alert('Could not record your response: ' + err.message + '\nPlease try again.');
//        }
//    };
//
//    document.getElementById('auto_co_no').onclick = async () => {
//        const btn = document.getElementById('auto_co_no');
//        btn.disabled = true;
//        try {
//            // Explicit "No" is a real answer -> plain checkout, no NR flag.
//            const result = await _rpc('hr.attendance', 'checkout_now_explicit_no', [attendanceId]);
//            if (!result || !result.success) {
//                throw new Error((result && result.error) || 'Checkout failed for an unknown reason.');
//            }
//            closeReminderPopup();
//            _ignoreCount = 0;
//            _popupOpenForAttendanceId = null;
//            _mutedAttendanceId = null;
//            window.location.reload(); // refresh so Check-In/status widgets update immediately
//        } catch (err) {
//            btn.disabled = false;
//            alert('Could not check you out automatically: ' + err.message +
//                  '\nPlease use the Check Out button instead.');
//        }
//    };
//}
//
//function notifyForcedCheckout() {
//    const note = document.createElement('div');
//    note.className = 'auto-co-toast';
//    note.textContent = 'You were automatically checked out after not responding. Your manager will review this entry.';
//    document.body.appendChild(note);
//    // Give the employee a couple seconds to actually read the toast,
//    // then refresh so the Check-In/status widgets reflect the new state.
//    setTimeout(() => window.location.reload(), 2500);
//}
//
//// ---- Phase 2 UI: OT-limit popup + toast ----
//
//function showOtLimitPopup(attendanceId) {
//    if (document.querySelector('.ot-limit-overlay')) return;
//
//    const overlay = document.createElement('div');
//    overlay.className = 'late-overlay ot-limit-overlay';
//
//    const popup = document.createElement('div');
//    popup.className = 'late-popup ot-limit-popup';
//
//    popup.innerHTML = `
//        <div class="late-popup-header auto-co-header">
//            <h3>Maximum extra hours reached</h3>
//        </div>
//        <div class="late-popup-body">
//            <p>You've reached the 4-hour extra-time limit. Please check out now.</p>
//            <div class="late-popup-actions" style="margin-top: 15px;">
//                <button id="ot_limit_checkout">Check out now</button>
//            </div>
//        </div>
//    `;
//
//    overlay.appendChild(popup);
//    document.body.appendChild(overlay);
//
//    document.getElementById('ot_limit_checkout').onclick = async () => {
//        const btn = document.getElementById('ot_limit_checkout');
//        btn.disabled = true;
//        try {
//            const result = await _rpc('hr.attendance', 'checkout_now_explicit_no', [attendanceId]);
//            if (!result || !result.success) {
//                throw new Error((result && result.error) || 'Checkout failed for an unknown reason.');
//            }
//            closeOtLimitPopup();
//            _mutedAttendanceId = null;
//            _otPopupLastShownAt = 0;
//            _otPopupCount = 0;
//            window.location.reload();
//        } catch (err) {
//            btn.disabled = false;
//            alert('Could not check you out automatically: ' + err.message +
//                  '\nPlease use the Check Out button instead.');
//        }
//    };
//}
//
//function notifyOtLimitCheckout() {
//    const note = document.createElement('div');
//    note.className = 'auto-co-toast';
//    note.textContent = 'You were automatically checked out after reaching the 4-hour extra-time limit. Your manager will review the extra hours for approval.';
//    document.body.appendChild(note);
//    setTimeout(() => window.location.reload(), 2500);
//}
//
//setTimeout(pollAutoCheckoutReminder, 5000);
//
//window.pollAutoCheckoutReminder = pollAutoCheckoutReminder;