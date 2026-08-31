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

        holidays = self.env[
            "resource.calendar.leaves"
        ].sudo().search(
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

        employees = self.env[
            "hr.employee"
        ].sudo().search([])

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
                # BOTH Check-In AND Check-Out must be on
                # the Public Holiday date.
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
                    "Odoo Worked Hours:",
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
                # 9. Validate Check-Out
                # -------------------------------------------------
                if not attendance.check_out:

                    print(
                        "SKIPPING:",
                        employee.name,
                        "| Check Out not found.",
                        flush=True,
                    )

                    continue

                # -------------------------------------------------
                # 10. ACTUAL CHECK-IN / CHECK-OUT HOURS
                #
                # IMPORTANT:
                #
                # Calculate directly from Check-In and Check-Out.
                #
                # 5:59 hours  -> NO
                # 6:00 hours  -> YES
                # 6:01 hours  -> YES
                # 8:00 hours  -> YES
                # -------------------------------------------------

                actual_worked_seconds = (
                    attendance.check_out
                    - attendance.check_in
                ).total_seconds()

                actual_worked_hours = (
                    actual_worked_seconds / 3600.0
                )

                print("")
                print(
                    "************ 6 HOUR VALIDATION ************",
                    flush=True,
                )

                print(
                    "Check In:",
                    attendance.check_in,
                    flush=True,
                )

                print(
                    "Check Out:",
                    attendance.check_out,
                    flush=True,
                )

                print(
                    "Odoo Worked Hours:",
                    attendance.worked_hours,
                    flush=True,
                )

                print(
                    "ACTUAL WORKED HOURS:",
                    round(actual_worked_hours, 4),
                    flush=True,
                )

                print(
                    "MINIMUM REQUIRED HOURS: 6.0",
                    flush=True,
                )

                print(
                    "********************************************",
                    flush=True,
                )

                _logger.warning(
                    "COMP OFF HOURS CHECK | "
                    "Employee=%s | Holiday=%s | "
                    "CheckIn=%s | CheckOut=%s | "
                    "OdooWorkedHours=%s | ActualWorkedHours=%s",
                    employee.name,
                    holiday_date,
                    attendance.check_in,
                    attendance.check_out,
                    attendance.worked_hours,
                    actual_worked_hours,
                )

                # -------------------------------------------------
                # 11. Minimum 6 Hours Condition
                # -------------------------------------------------
                if actual_worked_hours < 6.0:

                    print("")
                    print(
                        "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!",
                        flush=True,
                    )

                    print(
                        "COMP OFF NOT CREATED",
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
                        "Actual Worked Hours:",
                        round(actual_worked_hours, 4),
                        flush=True,
                    )

                    print(
                        "Reason: Employee worked LESS THAN 6 HOURS.",
                        flush=True,
                    )

                    print(
                        "Minimum Required: 6 HOURS",
                        flush=True,
                    )

                    print(
                        "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!",
                        flush=True,
                    )

                    _logger.warning(
                        "COMP OFF SKIPPED | "
                        "Employee=%s | Holiday=%s | "
                        "Actual Worked Hours=%s | "
                        "Minimum Required=6",
                        employee.name,
                        holiday_date,
                        actual_worked_hours,
                    )

                    continue

                # -------------------------------------------------
                # 12. 6 Hours Condition Passed
                # -------------------------------------------------
                print("")
                print(
                    "********************************************",
                    flush=True,
                )

                print(
                    "6 HOUR CONDITION PASSED",
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
                    "Actual Worked Hours:",
                    round(actual_worked_hours, 4),
                    flush=True,
                )

                print(
                    "COMP OFF WILL BE CREATED.",
                    flush=True,
                )

                print(
                    "********************************************",
                    flush=True,
                )

                _logger.warning(
                    "6-HOUR CONDITION PASSED | "
                    "Employee=%s | Holiday=%s | "
                    "Actual Worked Hours=%s",
                    employee.name,
                    holiday_date,
                    actual_worked_hours,
                )

                # -------------------------------------------------
                # 13. Unique Comp-Off Allocation Name
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
                # 14. Prevent Duplicate Allocation
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
                # 15. Calculate Validity Period
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
                # 16. Create Comp-Off Allocation
                # -------------------------------------------------
                try:

                    print("")
                    print(
                        "STEP 16: CREATING COMP OFF...",
                        flush=True,
                    )

                    allocation = self.env[
                        "hr.leave.allocation"
                    ].sudo().create(
                        {
                            "name": unique_name,

                            "employee_id":
                                employee.id,

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
                    # 17. Automatically Approve Allocation
                    # -------------------------------------------------
                    print(
                        "STEP 17: AUTO APPROVING COMP OFF...",
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
                            "State=%s | Start=%s | End=%s",
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
                    # 18. Employee Email
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
                                            Regards,<br/>
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
                    # 19. Manager Email
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
                                            Regards,<br/>
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
        # 20. Cron Completed
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