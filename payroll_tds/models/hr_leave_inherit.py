from odoo import models, api, fields
from odoo.exceptions import ValidationError
from datetime import timedelta


class HrLeave(models.Model):
    _inherit = "hr.leave"

    weekend_days = fields.Char(string="Weekend Days", readonly=True)
    public_holiday_days = fields.Char(string="Public Holidays", readonly=True)

    # -----------------------------
    # HR Admin Check
    # -----------------------------
    def _is_hr_admin(self):
        return self.env.user.has_group(
            'hr_holidays.group_hr_holidays_manager'
        )

    def _calendar_days(self, date_from, date_to):
        """Return total calendar days including weekends."""
        if not date_from or not date_to:
            return 0
        return (date_to - date_from).days + 1

    # ----------------------------------------
    # 🚫 SANDWICH LEAVE MONTHLY LIMIT
    # ----------------------------------------
    # ----------------------------------------
    # 🚫 PRIVILEGE LEAVE MONTHLY LIMIT
    # ----------------------------------------
    @api.constrains(
        'employee_id',
        'holiday_status_id',
        'request_date_from',
        'request_date_to',
        'number_of_days'
    )
    def _check_sandwich_leave_monthly_limit(self):

        if self._is_hr_admin():
            return

        for leave in self:

            if not leave.employee_id or not leave.holiday_status_id:
                continue

            # Run only for Privilege Leave
            if leave.holiday_status_id.name != 'Privilege Leave':
                continue

            if not leave.request_date_from or not leave.request_date_to:
                continue

            month_start = leave.request_date_from.replace(day=1)

            if leave.request_date_from.month == 12:
                month_end = leave.request_date_from.replace(
                    year=leave.request_date_from.year + 1,
                    month=1,
                    day=1
                ) - timedelta(days=1)
            else:
                month_end = leave.request_date_from.replace(
                    month=leave.request_date_from.month + 1,
                    day=1
                ) - timedelta(days=1)

            monthly_leaves = self.env['hr.leave'].search([
                ('employee_id', '=', leave.employee_id.id),
                ('holiday_status_id', '=', leave.holiday_status_id.id),
                ('state', 'not in', ['refuse', 'cancel']),
                ('id', '!=', leave.id),
                ('request_date_from', '>=', month_start),
                ('request_date_from', '<=', month_end),
            ])

            existing_days = sum(
                self._calendar_days(
                    l.request_date_from,
                    l.request_date_to
                )
                for l in monthly_leaves
            )

            current_leave_days = self._calendar_days(
                leave.request_date_from,
                leave.request_date_to
            )

            total_days = existing_days + current_leave_days

            if total_days > 7:
                raise ValidationError(
                    "You cannot apply more than 7 calendar days of Privilege Leave in a month."
                )

    @api.constrains(
        'employee_id',
        'holiday_status_id',
        'request_date_from',
        'number_of_days'
    )
    def _check_casual_leave_monthly_limit(self):

        if self._is_hr_admin():
            return

        for leave in self:

            if not leave.employee_id or not leave.holiday_status_id:
                continue

            # Casual Leave
            if leave.holiday_status_id.name != 'Casual Leave':
                continue

            month_start = leave.request_date_from.replace(day=1)

            if leave.request_date_from.month == 12:
                month_end = leave.request_date_from.replace(
                    year=leave.request_date_from.year + 1,
                    month=1,
                    day=1
                ) - timedelta(days=1)
            else:
                month_end = leave.request_date_from.replace(
                    month=leave.request_date_from.month + 1,
                    day=1
                ) - timedelta(days=1)

            monthly_leaves = self.env['hr.leave'].search([
                ('employee_id', '=', leave.employee_id.id),
                ('holiday_status_id', '=', leave.holiday_status_id.id),
                ('state', 'not in', ['refuse', 'cancel']),
                ('id', '!=', leave.id),
                ('request_date_from', '>=', month_start),
                ('request_date_from', '<=', month_end),
            ])

            total_days = sum(monthly_leaves.mapped('number_of_days')) + leave.number_of_days

            if total_days > 2:
                raise ValidationError(
                    "You cannot apply more than 2 days of Casual Leave in a month."
                )

    # ----------------------------------------
    # 🚫 PRIVILEGE LEAVE ADVANCE NOTICE
    # ----------------------------------------
    @api.constrains(
        'holiday_status_id',
        'request_date_from'
    )
    def _check_privilege_leave_advance_notice(self):

        if self._is_hr_admin():
            return

        for leave in self:

            if not leave.employee_id or not leave.holiday_status_id:
                continue

            # Apply only for Privilege Leave
            if leave.holiday_status_id.name != 'Privilege Leave':
                continue

            if not leave.request_date_from:
                continue

            today = fields.Date.today()

            days_difference = (leave.request_date_from - today).days

            if days_difference < 7:
                raise ValidationError(
                    "Privilege Leave must be applied at least 7 days before the leave start date."
                )

    # ----------------------------------------
    # 🚫 CASUAL LEAVE ADVANCE NOTICE
    # ----------------------------------------
    # @api.constrains(
    #     'holiday_status_id',
    #     'request_date_from'
    # )
    # def _check_casual_leave_advance_notice(self):
    #
    #     if self._is_hr_admin():
    #         return
    #
    #     for leave in self:
    #
    #         if not leave.employee_id or not leave.holiday_status_id:
    #             continue
    #
    #         if leave.holiday_status_id.name != 'Casual Leave':
    #             continue
    #
    #         if not leave.request_date_from:
    #             continue
    #
    #         today = fields.Date.today()
    #
    #         days_difference = (
    #                 leave.request_date_from - today
    #         ).days
    #
    #         if days_difference < 1:
    #             raise ValidationError(
    #                 "Casual Leave must be applied at least 1 day in advance."
    #             )

    # ----------------------------------------
    # 📅 ONCHANGE - NON WORKING DAYS
    # ----------------------------------------
    @api.onchange('request_date_from', 'request_date_to')
    def _onchange_dates_compute_non_working(self):

        if self._is_hr_admin():
            return

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

        if self._is_hr_admin():
            return

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
                        "You cannot club %(current)s with %(previous)s while applying for leave."
                        % {
                            'current': leave.holiday_status_id.display_name,
                            'previous': previous_leave.holiday_status_id.display_name,
                        }
                    )

    # ----------------------------------------
    # 📎 SUPPORTING DOCUMENT VALIDATION
    # ----------------------------------------
    @api.constrains('holiday_status_id', 'number_of_days', 'attachment_ids')
    def _check_support_document_required(self):
        if self._is_hr_admin():
            return

        for leave in self:
            if leave.holiday_status_id.support_document and leave.number_of_days > 2:
                if not leave.attachment_ids:
                    raise ValidationError(
                        "❌ Supporting Document is required for leave more than 2 days."
                    )

    # ----------------------------------------
    # 📧 LEAVE APPROVAL REMINDER MAIL
    # ----------------------------------------
    @api.model
    def send_leave_approval_reminder(self):

        print("REMINDER METHOD RUNNING")

        pending_leaves = self.search([
            ('state', '=', 'confirm'),
            ('create_date', '<=', fields.Datetime.now() - timedelta(minutes=1))
        ])

        template = self.env.ref(
            'payroll_tds.leave_approval_reminder_email_template',
            raise_if_not_found=False
        )

        for leave in pending_leaves:

            emails = []

            # Employee Email
            if leave.employee_id.work_email:
                emails.append(leave.employee_id.work_email)

            # Manager Email
            if leave.employee_id.parent_id.work_email:
                emails.append(leave.employee_id.parent_id.work_email)

            if template and emails:
                template.send_mail(
                    leave.id,
                    force_send=True,
                    email_values={
                        'email_to': ','.join(emails)
                    }
                )

    def action_print_leave(self):
        self.ensure_one()
        return self.env.ref('payroll_tds.action_report_leave').report_action(self)

    # ----------------------------------------
    # 📧 TIME OFF BALANCE APPROVAL MAIL
    # ----------------------------------------
    def write(self, vals):

        print("WRITE CALLED")
        print("VALS:", vals)

        res = super().write(vals)

        # Leave Approved
        if vals.get('state') in ['validate', 'validate1']:

            print("APPROVAL DETECTED")

            for leave in self:

                print("EMPLOYEE:", leave.employee_id.name)

                # Reporting Manager
                manager = leave.employee_id.parent_id

                print("MANAGER:", manager.name if manager else "NO MANAGER")

                # Check Payslip
                blocked_slip = self.env['hr.payslip'].search([
                    ('employee_id', '=', leave.employee_id.id),
                    ('state', '=', 'timeoff_balance')
                ])

                print("BLOCKED SLIP:", blocked_slip)

                if blocked_slip:
                    print("TIMEOFF BALANCE FOUND")

                if blocked_slip and manager and manager.user_id.email:
                    print("MAIL SENDING")

                    mail_values = {
                        'subject': 'Please Proceed with Payroll',
                        'body_html': f"""
                            <p>Dear {manager.name},</p>

                            <p>
                                Employee
                                <b>{leave.employee_id.name}</b>'s
                                leave request has been approved.
                            </p>

                            <p>
                                Please proceed with the payroll.
                            </p>



                            <p>Thanks</p>
                        """,
                        'email_to': manager.user_id.email,
                    }

                    self.env['mail.mail'].sudo().create(mail_values).send()

                    # Payroll Officer Users
                    payroll_group = self.env.ref(
                        'hr_payroll.group_hr_payroll_user'
                    )

                    payroll_users = self.env['res.users'].search([
                        ('groups_id', 'in', payroll_group.id)
                    ])

                    for user in payroll_users:

                        if user.email:
                            payroll_mail_values = {
                                'subject': 'Payroll Can Be Processed',
                                'body_html': f"""
                                    <p>Dear {user.name},</p>

                                    <p>
                                        Employee
                                        <b>{leave.employee_id.name}</b>'s
                                        leave request has been approved.
                                    </p>

                                    <p>
                                        The payslip in
                                        <b>Time Off Balance</b>
                                        can now be processed.
                                    </p>



                                    <p>Thanks</p>
                                """,
                                'email_to': user.email,
                            }

                            self.env['mail.mail'].sudo().create(
                                payroll_mail_values
                            ).send()

        return res
