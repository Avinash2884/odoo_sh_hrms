import logging
import pytz

from datetime import timedelta

from odoo import fields, models

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    def cron_generate_comp_off(self):

        print("")
        print("====================================================", flush=True)
        print("========== COMP OFF CRON STARTED ==========", flush=True)
        print("====================================================", flush=True)

        _logger.warning("====================================================")
        _logger.warning("========== COMP OFF CRON STARTED ==========")
        _logger.warning("====================================================")

        # ---------------------------------------------------------
        # 1. Get Compensatory Off Leave Type
        # ---------------------------------------------------------
        print(
            "STEP 1: Searching Compensatory Days Leave Type...",
            flush=True,
        )

        comp_off_type = self.env["hr.leave.type"].sudo().search(
            [
                ("name", "=", "Compensatory Days"),
            ],
            limit=1,
        )

        if not comp_off_type:

            print(
                "ERROR: Compensatory Days Leave Type NOT FOUND!",
                flush=True,
            )

            _logger.error(
                "Compensatory Days Leave Type NOT FOUND!"
            )

            return

        print(
            "COMP OFF TYPE FOUND | ID:",
            comp_off_type.id,
            "| NAME:",
            comp_off_type.name,
            flush=True,
        )

        # ---------------------------------------------------------
        # 2. Get Public Holidays
        # ---------------------------------------------------------
        print(
            "STEP 2: Searching Public Holidays...",
            flush=True,
        )

        holidays = self.env["resource.calendar.leaves"].sudo().search(
            [
                ("resource_id", "=", False),
            ]
        )

        print(
            "TOTAL PUBLIC HOLIDAYS FOUND:",
            len(holidays),
            flush=True,
        )

        _logger.warning(
            "TOTAL PUBLIC HOLIDAYS FOUND: %s",
            len(holidays),
        )

        # ---------------------------------------------------------
        # 3. Get Employees
        # ---------------------------------------------------------
        print(
            "STEP 3: Searching Employees...",
            flush=True,
        )

        employees = self.env["hr.employee"].sudo().search([])

        print(
            "TOTAL EMPLOYEES FOUND:",
            len(employees),
            flush=True,
        )

        # ---------------------------------------------------------
        # 4. Process Each Public Holiday
        # ---------------------------------------------------------
        for holiday in holidays:

            print("")
            print(
                "====================================================",
                flush=True,
            )

            print(
                "PROCESSING PUBLIC HOLIDAY:",
                holiday.name,
                flush=True,
            )

            print(
                "HOLIDAY ID:",
                holiday.id,
                flush=True,
            )

            print(
                "HOLIDAY DATE FROM:",
                holiday.date_from,
                flush=True,
            )

            print(
                "HOLIDAY DATE TO:",
                holiday.date_to,
                flush=True,
            )

            print(
                "====================================================",
                flush=True,
            )

            _logger.warning(
                "PROCESSING PUBLIC HOLIDAY | "
                "ID=%s | NAME=%s | DATE FROM=%s | DATE TO=%s",
                holiday.id,
                holiday.name,
                holiday.date_from,
                holiday.date_to,
            )

            # -----------------------------------------------------
            # 5. Process Each Employee
            # -----------------------------------------------------
            for employee in employees:

                print("")
                print(
                    "----------------------------------------------------",
                    flush=True,
                )

                print(
                    "CHECKING EMPLOYEE:",
                    employee.name,
                    "| ID:",
                    employee.id,
                    flush=True,
                )

                # -------------------------------------------------
                # 5A. Employee Timezone
                # -------------------------------------------------
                employee_timezone = (
                    employee.user_id.tz
                    or self.env.user.tz
                    or "UTC"
                )

                print(
                    "EMPLOYEE TIMEZONE:",
                    employee_timezone,
                    flush=True,
                )

                try:
                    employee_tz = pytz.timezone(
                        employee_timezone
                    )
                except Exception:

                    print(
                        "INVALID TIMEZONE:",
                        employee_timezone,
                        "| USING UTC",
                        flush=True,
                    )

                    employee_tz = pytz.UTC

                # -------------------------------------------------
                # 5B. Get Public Holiday Local Date
                # -------------------------------------------------
                holiday_utc_datetime = fields.Datetime.to_datetime(
                    holiday.date_from
                )

                # Odoo datetime is stored in UTC.
                if holiday_utc_datetime.tzinfo:
                    holiday_utc_datetime = (
                        holiday_utc_datetime.astimezone(
                            pytz.UTC
                        )
                    )
                else:
                    holiday_utc_datetime = pytz.UTC.localize(
                        holiday_utc_datetime
                    )

                holiday_local_datetime = (
                    holiday_utc_datetime.astimezone(
                        employee_tz
                    )
                )

                holiday_date = (
                    holiday_local_datetime.date()
                )

                print(
                    "PUBLIC HOLIDAY LOCAL DATE:",
                    holiday_date,
                    flush=True,
                )

                _logger.warning(
                    "PUBLIC HOLIDAY LOCAL DATE | "
                    "Employee=%s | Timezone=%s | Date=%s",
                    employee.name,
                    employee_timezone,
                    holiday_date,
                )

                # -------------------------------------------------
                # 5C. Public Holiday Local Day Range
                # -------------------------------------------------
                local_start = employee_tz.localize(
                    holiday_local_datetime.replace(
                        hour=0,
                        minute=0,
                        second=0,
                        microsecond=0,
                        tzinfo=None,
                    )
                )

                local_end = employee_tz.localize(
                    holiday_local_datetime.replace(
                        hour=23,
                        minute=59,
                        second=59,
                        microsecond=999999,
                        tzinfo=None,
                    )
                )

                print(
                    "PUBLIC HOLIDAY LOCAL RANGE:",
                    local_start,
                    "->",
                    local_end,
                    flush=True,
                )

                # -------------------------------------------------
                # 5D. Convert Holiday Range to UTC
                # -------------------------------------------------
                utc_start = (
                    local_start.astimezone(
                        pytz.UTC
                    ).replace(
                        tzinfo=None
                    )
                )

                utc_end = (
                    local_end.astimezone(
                        pytz.UTC
                    ).replace(
                        tzinfo=None
                    )
                )

                print(
                    "PUBLIC HOLIDAY UTC RANGE:",
                    utc_start,
                    "->",
                    utc_end,
                    flush=True,
                )

                # -------------------------------------------------
                # 6. Search Attendance
                #
                # IMPORTANT:
                #
                # Both Check-In AND Check-Out must be on
                # the Public Holiday date.
                #
                # Example:
                #
                # 14-Aug 08:00 PM -> 15-Aug 11:00 PM
                #       ❌ NO COMP OFF
                #
                # 15-Aug 08:00 AM -> 15-Aug 08:00 PM
                #       ✅ COMP OFF
                #
                # 15-Aug 10:00 PM -> 16-Aug 02:00 AM
                #       ❌ NO COMP OFF
                # -------------------------------------------------
                print(
                    "STEP 6: SEARCHING VALID ATTENDANCE...",
                    flush=True,
                )

                attendance = self.env[
                    "hr.attendance"
                ].sudo().search(
                    [
                        (
                            "employee_id",
                            "=",
                            employee.id,
                        ),

                        # Check-In must be on holiday
                        (
                            "check_in",
                            ">=",
                            utc_start,
                        ),
                        (
                            "check_in",
                            "<=",
                            utc_end,
                        ),

                        # Check-Out must ALSO be on holiday
                        (
                            "check_out",
                            ">=",
                            utc_start,
                        ),
                        (
                            "check_out",
                            "<=",
                            utc_end,
                        ),
                    ],
                    order="check_in desc",
                    limit=1,
                )

                # -------------------------------------------------
                # 7. No Attendance
                # -------------------------------------------------
                if not attendance:

                    print(
                        "NO VALID ATTENDANCE FOUND FOR:",
                        employee.name,
                        "| Holiday:",
                        holiday_date,
                        flush=True,
                    )

                    _logger.warning(
                        "NO VALID ATTENDANCE | "
                        "Employee=%s | Holiday=%s",
                        employee.name,
                        holiday_date,
                    )

                    continue

                # -------------------------------------------------
                # 8. Attendance Found
                # -------------------------------------------------
                print("")
                print(
                    "************ VALID ATTENDANCE FOUND ************",
                    flush=True,
                )

                print(
                    "Attendance ID:",
                    attendance.id,
                    flush=True,
                )

                print(
                    "Employee:",
                    employee.name,
                    flush=True,
                )

                print(
                    "Check In UTC:",
                    attendance.check_in,
                    flush=True,
                )

                print(
                    "Check Out UTC:",
                    attendance.check_out,
                    flush=True,
                )

                print(
                    "Worked Hours:",
                    attendance.worked_hours,
                    flush=True,
                )

                print(
                    "Public Holiday:",
                    holiday_date,
                    flush=True,
                )

                print(
                    "************************************************",
                    flush=True,
                )

                # -------------------------------------------------
                # 9. Validate Attendance
                # -------------------------------------------------
                if not attendance.check_out:

                    print(
                        "SKIPPING:",
                        employee.name,
                        "| Check Out not found.",
                        flush=True,
                    )

                    continue

                if attendance.worked_hours <= 0:

                    print(
                        "SKIPPING:",
                        employee.name,
                        "| Worked Hours is 0.",
                        flush=True,
                    )

                    continue

                # -------------------------------------------------
                # 10. Unique Comp-Off Allocation Name
                # -------------------------------------------------
                unique_name = (
                    f"Comp Off - "
                    f"{holiday_date.strftime('%d/%m/%Y')}"
                )

                print(
                    "COMP OFF NAME:",
                    unique_name,
                    flush=True,
                )

                # -------------------------------------------------
                # 11. Prevent Duplicate Allocation
                # -------------------------------------------------
                existing = self.env[
                    "hr.leave.allocation"
                ].sudo().search(
                    [
                        (
                            "employee_id",
                            "=",
                            employee.id,
                        ),
                        (
                            "holiday_status_id",
                            "=",
                            comp_off_type.id,
                        ),
                        (
                            "name",
                            "=",
                            unique_name,
                        ),
                    ],
                    limit=1,
                )

                if existing:
                    print(
                        "COMP OFF ALREADY EXISTS |",
                        employee.name,
                        "| Allocation ID:",
                        existing.id,
                        "| State:",
                        existing.state,
                        flush=True,
                    )

                    continue

                # -------------------------------------------------
                # 12. Calculate Validity Period
                # -------------------------------------------------
                #
                # Public Holiday:
                # 15-Aug-2026
                #
                # Validity Start:
                # 16-Aug-2026
                #
                # 16-Aug = Day 1
                #
                # 60th Day:
                # 14-Oct-2026
                #
                # Therefore:
                #
                # date_from = 16-Aug-2026
                # date_to   = 14-Oct-2026
                #
                # -------------------------------------------------

            validity_start_date = (
                    holiday_date + timedelta(days=1)
            )

            validity_end_date = (
                    validity_start_date
                    + timedelta(days=59)
            )

            print("")
            print(
                "************ VALIDITY PERIOD ************",
                flush=True,
            )

            print(
                "Public Holiday Date:",
                holiday_date,
                flush=True,
            )

            print(
                "Validity Start Date:",
                validity_start_date,
                flush=True,
            )

            print(
                "Validity End Date:",
                validity_end_date,
                flush=True,
            )

            print(
                "Total Validity Days:",
                (
                        validity_end_date
                        - validity_start_date
                ).days + 1,
                flush=True,
            )

            print(
                "******************************************",
                flush=True,
            )

            _logger.warning(
                "COMP OFF VALIDITY | "
                "Employee=%s | Holiday=%s | "
                "Start=%s | End=%s | Days=%s",
                employee.name,
                holiday_date,
                validity_start_date,
                validity_end_date,
                (
                        validity_end_date
                        - validity_start_date
                ).days + 1,
            )

            # -------------------------------------------------
            # 13. Create Comp-Off Allocation
            # -------------------------------------------------
            try:

                print("")
                print(
                    "STEP 13: CREATING COMP OFF...",
                    flush=True,
                )

                allocation = self.env[
                    "hr.leave.allocation"
                ].sudo().create(
                    {
                        "name": unique_name,

                        "employee_id": employee.id,

                        "holiday_status_id":
                            comp_off_type.id,

                        "number_of_days": 1,

                        # Validity starts next day
                        "date_from":
                            validity_start_date,

                        # 60th day
                        "date_to":
                            validity_end_date,
                    }
                )

                print("")
                print(
                    "####################################################",
                    flush=True,
                )

                print(
                    "************ COMP OFF CREATED ************",
                    flush=True,
                )

                print(
                    "Employee:",
                    employee.name,
                    flush=True,
                )

                print(
                    "Allocation ID:",
                    allocation.id,
                    flush=True,
                )

                print(
                    "Allocation Name:",
                    allocation.name,
                    flush=True,
                )

                print(
                    "State BEFORE APPROVAL:",
                    allocation.state,
                    flush=True,
                )

                print(
                    "Validity Start:",
                    allocation.date_from,
                    flush=True,
                )

                print(
                    "Validity End:",
                    allocation.date_to,
                    flush=True,
                )

                print(
                    "####################################################",
                    flush=True,
                )

                # -------------------------------------------------
                # 14. Automatically Approve Allocation
                # -------------------------------------------------
                print(
                    "STEP 14: AUTO APPROVING COMP OFF...",
                    flush=True,
                )

                _logger.warning(
                    "AUTO APPROVAL STARTED | "
                    "Allocation ID=%s | "
                    "Current State=%s",
                    allocation.id,
                    allocation.state,
                )

                try:

                    allocation.sudo()._action_validate()

                    allocation.invalidate_recordset()

                    print(
                        "AUTO APPROVAL COMPLETED.",
                        flush=True,
                    )

                    print(
                        "STATE AFTER APPROVAL:",
                        allocation.state,
                        flush=True,
                    )

                    print(
                        "VALIDITY START:",
                        allocation.date_from,
                        flush=True,
                    )

                    print(
                        "VALIDITY END:",
                        allocation.date_to,
                        flush=True,
                    )

                    _logger.warning(
                        "AUTO APPROVAL COMPLETED | "
                        "Allocation ID=%s | "
                        "State=%s | "
                        "Start=%s | End=%s",
                        allocation.id,
                        allocation.state,
                        allocation.date_from,
                        allocation.date_to,
                    )

                except Exception as approval_error:

                    print(
                        "AUTO APPROVAL FAILED:",
                        str(approval_error),
                        flush=True,
                    )

                    _logger.exception(
                        "AUTO APPROVAL FAILED | "
                        "Allocation ID=%s | Error=%s",
                        allocation.id,
                        str(approval_error),
                    )

                # -------------------------------------------------
                # 15. Employee Email
                # -------------------------------------------------
                if employee.work_email:
                    self.env[
                        "mail.mail"
                    ].sudo().create(
                        {
                            "subject":
                                "Compensatory Off Credited",

                            "email_to":
                                employee.work_email,

                            "body_html": f"""
                                                <div>
                                                    <p>
                                                        Dear
                                                        <b>{employee.name}</b>,
                                                    </p>

                                                    <p>
                                                        You worked on Public Holiday
                                                        <b>
                                                            {
                            holiday_date.strftime(
                                '%d/%m/%Y'
                            )
                            }
                                                        </b>.
                                                    </p>

                                                    <p>
                                                        <b>
                                                            1 Compensatory Off
                                                        </b>
                                                        has been credited to your
                                                        account.
                                                    </p>

                                                    <p>
                                                        Compensatory Off Validity:
                                                        <b>
                                                            {
                            validity_start_date.strftime(
                                '%d/%m/%Y'
                            )
                            }
                                                        </b>
                                                        to
                                                        <b>
                                                            {
                            validity_end_date.strftime(
                                '%d/%m/%Y'
                            )
                            }
                                                        </b>
                                                    </p>

                                                    <p>
                                                        Regards,

                                                        HR Team
                                                    </p>
                                                </div>
                                            """,
                        }
                    ).send()

                    print(
                        "Employee email sent to:",
                        employee.work_email,
                        flush=True,
                    )

                # -------------------------------------------------
                # 16. Manager Email
                # -------------------------------------------------
                manager = employee.parent_id

                if manager and manager.work_email:
                    self.env[
                        "mail.mail"
                    ].sudo().create(
                        {
                            "subject":
                                "Employee Comp Off Credited",

                            "email_to":
                                manager.work_email,

                            "body_html": f"""
                                                <div>
                                                    <p>
                                                        Dear
                                                        <b>{manager.name}</b>,
                                                    </p>

                                                    <p>
                                                        Employee
                                                        <b>{employee.name}</b>
                                                        worked on Public Holiday
                                                        <b>
                                                            {
                            holiday_date.strftime(
                                '%d/%m/%Y'
                            )
                            }
                                                        </b>.
                                                    </p>

                                                    <p>
                                                        <b>
                                                            1 Compensatory Off
                                                        </b>
                                                        has been credited to the
                                                        employee.
                                                    </p>

                                                    <p>
                                                        Compensatory Off Validity:
                                                        <b>
                                                            {
                            validity_start_date.strftime(
                                '%d/%m/%Y'
                            )
                            }
                                                        </b>
                                                        to
                                                        <b>
                                                            {
                            validity_end_date.strftime(
                                '%d/%m/%Y'
                            )
                            }
                                                        </b>
                                                    </p>

                                                    <p>
                                                        Regards,

                                                        HR Team
                                                    </p>
                                                </div>
                                            """,
                        }
                    ).send()

                    print(
                        "Manager email sent to:",
                        manager.work_email,
                        flush=True,
                    )

            except Exception as e:

                print("")
                print(
                    "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!",
                    flush=True,
                )

                print(
                    "COMP OFF CREATION FAILED",
                    flush=True,
                )

                print(
                    "Employee:",
                    employee.name,
                    flush=True,
                )

                print(
                    "Holiday:",
                    holiday_date,
                    flush=True,
                )

                print(
                    "ERROR:",
                    str(e),
                    flush=True,
                )

                print(
                    "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!",
                    flush=True,
                )

                _logger.exception(
                    "COMP OFF FAILED for %s: %s",
                    employee.name,
                    str(e),
                )

            # ---------------------------------------------------------
            # 17. Cron Completed
            # ---------------------------------------------------------
        print("")
        print(
            "====================================================",
            flush=True,
        )

        print(
            "========== COMP OFF CRON COMPLETED ==========",
            flush=True,
        )

        print(
            "====================================================",
            flush=True,
        )

        _logger.warning(
            "========== COMP OFF CRON COMPLETED =========="
        )