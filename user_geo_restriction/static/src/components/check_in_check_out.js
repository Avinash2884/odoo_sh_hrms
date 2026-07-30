/** @odoo-module **/

import { CheckInOut } from "@hr_attendance/components/check_in_out/check_in_out";
import { patch } from "@web/core/utils/patch";

patch(CheckInOut.prototype, {

    async signInOut() {
        console.log("🟢 Custom CheckInOut Triggered");

        if (!this.props.employeeId) {
            console.log("❌ No employeeId found");
            return;
        }

        const position = await new Promise((resolve) => {
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    console.log("✅ GPS:", pos.coords.latitude, pos.coords.longitude);
                    resolve(pos);
                },
                (err) => {
                    console.log("❌ GPS ERROR:", err.message);
                    resolve(null);
                },
                { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
            );
        });

        const latitude = position ? position.coords.latitude : false;
        const longitude = position ? position.coords.longitude : false;

        if (!position) {
            this.notification.add("Location access denied", { type: "warning" });
        }

        console.log("📍 Sending:", latitude, longitude);

        await this.orm.call("hr.employee", "update_last_position", [
            [this.props.employeeId],
            latitude,
            longitude
        ]);

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