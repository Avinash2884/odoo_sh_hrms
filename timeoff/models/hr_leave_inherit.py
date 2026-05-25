from odoo import models, api, fields
from odoo.exceptions import ValidationError
from datetime import timedelta


class HrLeave(models.Model):
    _inherit = "hr.leave"

    weekend_days = fields.Char(string="Weekend Days", readonly=True)
    public_holiday_days = fields.Char(string="Public Holidays", readonly=True)

    # ----------------------------------------
    # 📅 ONCHANGE - NON WORKING DAYS
    # ----------------------------------------
    @api.onchange('request_date_from', 'request_date_to')
    def _onchange_dates_compute_non_working(self):
        for rec in self:

            if not rec.request_date_from or not rec.request_date_to:
                rec.weekend_days = False
                rec.public_holiday_days = False
                continue

            start_date = fields.Date.to_date(rec.request_date_from)
            end_date = fields.Date.to_date(rec.request_date_to)

            weekend_list = []
            holiday_list = []

            current_date = start_date

            while current_date <= end_date:

                day_name = current_date.strftime('%A')

                # ✅ Weekend (Saturday + Sunday)
                if current_date.weekday() in (5, 6):
                    weekend_list.append(f"{current_date} ({day_name})")

                # ✅ Public Holiday
                holiday = self.env['resource.calendar.leaves'].search([
                    ('date_from', '<=', current_date),
                    ('date_to', '>=', current_date),
                    ('resource_id', '=', False)
                ], limit=1)

                # 👉 Avoid duplicate if holiday falls on weekend
                if holiday and current_date.weekday() not in (5, 6):
                    holiday_list.append(f"{current_date} ({day_name} - {holiday.name})")

                current_date += timedelta(days=1)

            rec.weekend_days = ', '.join(weekend_list)
            rec.public_holiday_days = ', '.join(holiday_list)

    # ----------------------------------------
    # 🚫 RESTRICT MIXED LEAVE TYPES
    # ----------------------------------------
    @api.constrains('employee_id', 'request_date_from', 'holiday_status_id')
    def _check_mixed_leave_types(self):
        for leave in self:

            if not leave.employee_id or not leave.request_date_from:
                continue

            previous_leave = self.env['hr.leave'].search([
                ('employee_id', '=', leave.employee_id.id),
                ('id', '!=', leave.id),
                ('state', 'in', ['confirm', 'validate1', 'validate']),
                ('request_date_to', '<=', leave.request_date_from),
            ], order='request_date_to desc', limit=1)

            if not previous_leave:
                continue

            prev_date = previous_leave.request_date_to
            curr_date = leave.request_date_from

            gap_days = (curr_date - prev_date).days

            if gap_days > 3:
                continue

            check_date = prev_date + timedelta(days=1)
            only_non_working = True

            while check_date < curr_date:

                is_working = self._l10n_in_is_working(
                    check_date,
                    {},
                    leave.employee_id.resource_calendar_id
                )

                if is_working:
                    only_non_working = False
                    break

                check_date += timedelta(days=1)

            if (gap_days <= 1 or only_non_working):
                if previous_leave.holiday_status_id.id != leave.holiday_status_id.id:
                    raise ValidationError(
                        "❌ You cannot apply different leave types continuously. "
                        "Please use the same leave type."
                    )

    # ----------------------------------------
    # 📎 SUPPORTING DOCUMENT VALIDATION
    # ----------------------------------------
    @api.constrains('holiday_status_id', 'number_of_days')
    def _check_support_document_required(self):
        for leave in self:

            # ✅ skip unsaved record
            if not leave.id:
                continue

            # ✅ skip incomplete form
            if not leave.holiday_status_id or not leave.number_of_days:
                continue

            # ✅ condition
            if leave.holiday_status_id.support_document and leave.number_of_days > 2:

                # ✅ skip draft (user still editing / demo data)
                if leave.state == 'draft':
                    continue

                # ✅ check attachment
                attachment_count = self.env['ir.attachment'].search_count([
                    ('res_model', '=', 'hr.leave'),
                    ('res_id', '=', leave.id)
                ])

                if attachment_count == 0:
                    raise ValidationError(
                        "❌ Supporting Document is required for leave more than 2 days."
                    )

    def action_print_leave(self):
        self.ensure_one()
        return self.env.ref(
            'timeoff.action_report_leave'
        ).sudo().report_action(self.sudo())