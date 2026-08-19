from odoo import models, fields
import logging
import pytz
from datetime import datetime, time

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

            # ---------------------------------------------------------
            # IMPORTANT:
            # Odoo stores datetime values in UTC.
            # Convert holiday datetime to the user's/local timezone
            # before extracting the actual calendar date.
            # ---------------------------------------------------------

            if not holiday.date_from:
                continue

            holiday_dt_utc = fields.Datetime.to_datetime(holiday.date_from)

            # Use employee/company/user timezone.
            # For your India setup, Asia/Kolkata is used.
            timezone_name = self.env.user.tz or 'Asia/Kolkata'

            try:
                local_tz = pytz.timezone(timezone_name)
            except Exception:
                local_tz = pytz.timezone('Asia/Kolkata')

            # Odoo datetime is naive UTC
            holiday_dt_utc = pytz.UTC.localize(holiday_dt_utc)

            # Convert UTC -> Local timezone
            holiday_dt_local = holiday_dt_utc.astimezone(local_tz)

            # Actual local Public Holiday date
            holiday_date = holiday_dt_local.date()

            _logger.info(
                "Holiday: %s | UTC: %s | Local: %s | Local Date: %s",
                holiday.name,
                holiday_dt_utc,
                holiday_dt_local,
                holiday_date,
            )

            # ---------------------------------------------------------
            # Local day boundaries
            # ---------------------------------------------------------

            local_start = local_tz.localize(
                datetime.combine(holiday_date, time.min)
            )

            local_end = local_tz.localize(
                datetime.combine(holiday_date, time.max)
            )

            # Convert local boundaries back to UTC
            utc_start = local_start.astimezone(pytz.UTC).replace(tzinfo=None)
            utc_end = local_end.astimezone(pytz.UTC).replace(tzinfo=None)

            _logger.info(
                "Holiday %s | Local Range: %s -> %s | UTC Range: %s -> %s",
                holiday_date,
                local_start,
                local_end,
                utc_start,
                utc_end,
            )

            for employee in employees:

                # ---------------------------------------------------------
                # Attendance search using CORRECT UTC range
                # corresponding to the employee's local holiday date
                # ---------------------------------------------------------

                attendances = self.env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', utc_start),
                    ('check_in', '<=', utc_end),
                ], order='check_in asc', limit=1)

                if not attendances:
                    continue

                attendance = attendances[0]

                _logger.info(
                    "Attendance found | Employee: %s | Check In UTC: %s | "
                    "Check Out UTC: %s | Holiday Local Date: %s",
                    employee.name,
                    attendance.check_in,
                    attendance.check_out,
                    holiday_date,
                )

                # Validation checks
                if not attendance.check_out:
                    _logger.info(
                        "Skipping %s - Check Out not found",
                        employee.name
                    )
                    continue

                if attendance.worked_hours <= 0:
                    _logger.info(
                        "Skipping %s - Worked hours <= 0",
                        employee.name
                    )
                    continue

                # ---------------------------------------------------------
                # Unique key
                # ---------------------------------------------------------

                unique_name = (
                    f"Comp Off - {holiday_date.strftime('%d/%m/%Y')}"
                )

                # Prevent duplicates
                existing = self.env['hr.leave.allocation'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('holiday_status_id', '=', comp_off_type.id),
                    ('name', '=', unique_name)
                ], limit=1)

                if existing:
                    _logger.info(
                        "Already exists for %s | %s",
                        employee.name,
                        unique_name
                    )
                    continue

                try:

                    # -----------------------------------------------------
                    # Create allocation
                    # -----------------------------------------------------

                    allocation = self.env['hr.leave.allocation'].sudo().create({
                        'name': unique_name,
                        'employee_id': employee.id,
                        'holiday_status_id': comp_off_type.id,
                        'number_of_days': 1,
                    })

                    _logger.info(
                        "Comp Off Created for %s | ID: %s | Holiday: %s",
                        employee.name,
                        allocation.id,
                        holiday_date,
                    )

                    # Odoo 19 safe validation
                    if hasattr(allocation, "action_validate"):
                        allocation.action_validate()

                    # -----------------------------------------------------
                    # Employee Mail
                    # -----------------------------------------------------

                    if employee.work_email:

                        self.env['mail.mail'].sudo().create({
                            'subject': 'Compensatory Off Eligibility',
                            'email_to': employee.work_email,
                            'body_html': f"""
                                <div>
                                    <p>Dear <b>{employee.name}</b>,</p>

                                    <p>
                                        You worked on Public Holiday
                                        <b>{holiday_date.strftime('%d/%m/%Y')}</b>.
                                    </p>

                <p>
                    You are eligible for
                    <b>Compensatory Off</b>.
                </p>

                                    <p>
                                        Regards,

                                        HR Team
                                    </p>
                                </div>
                            """
                        }).send()

                    # -----------------------------------------------------
                    # Manager Mail
                    # -----------------------------------------------------

                    manager = employee.parent_id

                    if manager and manager.work_email:

                        self.env['mail.mail'].sudo().create({
                            'subject': 'Compensatory Off Approval Required',
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
                    A <b>Compensatory Off</b> has been created against
                    the employee.
                </p>

                <p>
                    Kindly review and approve the Compensatory Off.
                </p>


                                    <p>
                                        Regards,

                                        HR Team
                                    </p>
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