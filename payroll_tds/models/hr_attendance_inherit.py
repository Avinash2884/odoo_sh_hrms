from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    def cron_generate_comp_off(self):

        _logger.info("========== COMP OFF CRON STARTED ==========")

        # Leave Type
        comp_off_type = self.env['hr.leave.type'].sudo().search([
            ('name', '=', 'Compensatory Days')
        ], limit=1)

        if not comp_off_type:
            _logger.info("Compensatory Days Leave Type not found.")
            return

        # Public Holidays
        holidays = self.env['resource.calendar.leaves'].sudo().search([
            ('resource_id', '=', False)
        ])

        _logger.info("Total Holidays: %s", len(holidays))

        # Employees
        employees = self.env['hr.employee'].sudo().search([])

        for holiday in holidays:

            holiday_date = fields.Date.to_date(holiday.date_from)

            # Day range (IMPORTANT FIX for timezone issue)
            start = f"{holiday_date} 00:00:00"
            end = f"{holiday_date} 23:59:59"

            _logger.info("Processing Holiday: %s", holiday_date)

            for employee in employees:

                # IMPORTANT FIX: proper time range search
                attendances = self.env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', start),
                    ('check_in', '<=', end),
                ], limit=1)

                if not attendances:
                    continue

                attendance = attendances[0]

                # Validation checks
                if not attendance.check_out:
                    continue

                if attendance.worked_hours <= 0:
                    continue

                # Unique key (no duplicates)
                unique_name = f"Comp Off - {holiday_date.strftime('%d/%m/%Y')}"

                # Prevent duplicates
                existing = self.env['hr.leave.allocation'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('holiday_status_id', '=', comp_off_type.id),
                    ('name', '=', unique_name)
                ], limit=1)

                if existing:
                    _logger.info("Already exists for %s", employee.name)
                    continue

                try:
                    # Create allocation
                    allocation = self.env['hr.leave.allocation'].sudo().create({
                        'name': unique_name,
                        'employee_id': employee.id,
                        'holiday_status_id': comp_off_type.id,
                        'number_of_days': 1,
                    })

                    _logger.info(
                        "Comp Off Created for %s | ID: %s",
                        employee.name,
                        allocation.id
                    )

                    # Odoo 19 safe validation
                    if hasattr(allocation, "action_validate"):
                        allocation.action_validate()

                    # ---------------- Employee Mail ----------------
                    if employee.work_email:
                        self.env['mail.mail'].sudo().create({
                            'subject': 'Compensatory Off Credited',
                            'email_to': employee.work_email,
                            'body_html': f"""
                                <div>
                                    <p>Dear <b>{employee.name}</b>,</p>

                                    <p>
                                        You worked on Public Holiday
                                        <b>{holiday_date.strftime('%d/%m/%Y')}</b>.
                                    </p>

                                    <p>
                                        <b>1 Compensatory Off</b> has been credited.
                                    </p>

                                    <p>Regards,
HR Team</p>
                                </div>
                            """
                        }).send()

                    # ---------------- Manager Mail ----------------
                    manager = employee.parent_id

                    if manager and manager.work_email:
                        self.env['mail.mail'].sudo().create({
                            'subject': 'Employee Comp Off Credited',
                            'email_to': manager.work_email,
                            'body_html': f"""
                                <div>
                                    <p>Dear <b>{manager.name}</b>,</p>

                                    <p>
                                        Employee <b>{employee.name}</b>
                                        worked on Public Holiday
                                        <b>{holiday_date.strftime('%d/%m/%Y')}</b>.
                                    </p>

                                    <p>
                                        Comp Off has been credited.
                                    </p>

                                    <p>Regards,
HR Team</p>
                                </div>
                            """
                        }).send()

                except Exception as e:
                    _logger.exception(
                        "Comp Off failed for %s : %s",
                        employee.name,
                        str(e)
                    )

        _logger.info("========== COMP OFF CRON COMPLETED ==========")