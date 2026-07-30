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
        const position = await new Promise((resolve) => {
            navigator.geolocation.getCurrentPosition(
                (pos) => resolve(pos),
                (err) => resolve(null),
                { enableHighAccuracy: true, timeout: 8000 }
            );
        });
        console.log("hello from siginout")
        const latitude = position ? position.coords.latitude : false;
        const longitude = position ? position.coords.longitude : false;

        await this.orm.call("hr.employee", "update_last_position", [
            [this.props.employeeId], latitude, longitude
        ]);

        const result = await this.orm.call("hr.employee", "attendance_manual", [
            [this.props.employeeId], this.props.nextAction,
        ]);

        if (result.action) {
            this.actionService.doAction(result.action);
        } else if (result.warning) {
            this.notification.add(result.warning, { type: "danger" });
        }
    }
}
