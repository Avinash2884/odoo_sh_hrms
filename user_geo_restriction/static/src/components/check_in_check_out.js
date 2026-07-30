/** @odoo-module **/

import { CheckInOut } from "@hr_attendance/components/check_in_out/check_in_out";
import { patch } from "@web/core/utils/patch";

patch(CheckInOut.prototype, {

    async signInOut() {
        await this.orm.call("hr.employee", "debug_log_from_js", ["🟢 Custom CheckInOut Triggered"]);

        if (!this.props.employeeId) {
            await this.orm.call("hr.employee", "debug_log_from_js", ["❌ No employeeId found"]);
            return;
        }

        const position = await new Promise((resolve) => {
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    resolve(pos);
                },
                (err) => {
                    resolve({ __error: err.message, __code: err.code });
                },
                { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
            );
        });

        if (position && position.__error) {
            await this.orm.call("hr.employee", "debug_log_from_js", [
                `❌ GPS ERROR: ${position.__error} (code ${position.__code})`
            ]);
        } else if (position) {
            await this.orm.call("hr.employee", "debug_log_from_js", [
                `✅ GPS SUCCESS: lat=${position.coords.latitude}, lon=${position.coords.longitude}, accuracy=${position.coords.accuracy}m`
            ]);
        }

        const latitude = (position && position.coords) ? position.coords.latitude : false;
        const longitude = (position && position.coords) ? position.coords.longitude : false;

        if (!position || position.__error) {
            this.notification.add("Location access denied", { type: "warning" });
        }

        await this.orm.call("hr.employee", "debug_log_from_js", [
            `📍 Sending to update_last_position: lat=${latitude}, lon=${longitude}`
        ]);

        await this.orm.call("hr.employee", "update_last_position", [
            [this.props.employeeId],
            latitude,
            longitude
        ]);

        await this.orm.call("hr.employee", "debug_log_from_js", ["✅ update_last_position DONE, calling attendance_manual"]);

        const result = await this.orm.call("hr.employee", "attendance_manual", [
            [this.props.employeeId],
            this.props.nextAction,
        ]);

        if (result.action) {
            this.actionService.doAction(result.action);
        } else if (result.warning) {
            this.notification.add(result.warning, { type: "danger" });
        }
    },

});