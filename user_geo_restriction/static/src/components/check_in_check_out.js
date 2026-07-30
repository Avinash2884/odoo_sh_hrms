import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

export class CheckInOut extends Component {
    static template = "hr_attendance.CheckInOut";
    static props = {
        checkedIn: Boolean,
        employeeId: Number,
        nextAction: String,
    };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.onClickSignInOut = useDebounced(this.signInOut, 200, { immediate: true });
    }

    async signInOut() {
        console.log("🟢 signInOut STARTED - custom JS loaded");

        const position = await new Promise((resolve) => {
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    console.log("✅ GPS SUCCESS:", pos.coords.latitude, pos.coords.longitude);
                    resolve(pos);
                },
                (err) => {
                    console.log("❌ GPS ERROR:", err.message, "code:", err.code);
                    resolve(null);
                },
                { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
            );
        });

        const latitude = position ? position.coords.latitude : false;
        const longitude = position ? position.coords.longitude : false;

        console.log("📍 Final coords being sent:", latitude, longitude);

        await this.orm.call("hr.employee", "update_last_position", [
            [this.props.employeeId],
            latitude,
            longitude
        ]);

        console.log("✅ update_last_position DONE, now calling attendance_manual");

        const result = await this.orm.call("hr.employee", "attendance_manual", [
            [this.props.employeeId],
            this.props.nextAction,
        ]);
        if (result.action) {
            this.actionService.doAction(result.action);
        } else if (result.warning) {
            this.notification.add(result.warning, {type: "danger"});
        }
    }
}