# -*- coding: utf-8 -*-
import math
from odoo import models, fields, api
from datetime import datetime, time, timedelta
from odoo.exceptions import UserError, ValidationError
import pytz


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    half_day_absent = fields.Boolean(
        string="Half Day Absent",
        compute="_compute_half_day",
        store=True
    )
    full_day_absent = fields.Boolean(
        string="Full Day Absent",
        compute="_compute_half_day",
        store=True
    )
    half_day_type = fields.Selection([
        ("first", "First Half"),
        ("second", "Second Half"),
    ], string="Half Day Type",
        compute="_compute_half_day",
        store=True
    )

    base_scheduled_hours = fields.Float(
        string="Shift Scheduled Hours",
        compute="_compute_base_scheduled",
        store=True,
    )
    permission_credit_applied = fields.Float(
        string="Permission Credit (hrs)",
        compute="_compute_worked",
        store=True,
    )

    # Moved to the top with the other fields!
    daily_total_hours = fields.Float(
        string="Daily Grand Total",
        compute="_compute_half_day",
        store=True
    )

    effective_check_in = fields.Datetime(compute="_compute_effective", store=True)
    worked_hours_custom = fields.Float(compute="_compute_worked", store=True)
    scheduled_hours = fields.Float(compute="_compute_scheduled", store=True)
    extra_hours = fields.Float(compute="_compute_extra",string="Calculated Extra Hours", store=True)
    total_hours = fields.Float(compute="_compute_total", store=True)

    # ---> PHOTO: One2many to attendance.photo (replaces old single image fields)
    photo_ids = fields.One2many(
        'attendance.photo',
        'attendance_id',
        string='Attendance Photos',
    )

    # ----------------------------------------------------------
    # Odoo 19 Native Overtime Injection
    # ----------------------------------------------------------
    overtime_hours = fields.Float(
        compute='_compute_native_overtime', store=True
    )
    validated_overtime_hours = fields.Float(
        compute='_compute_native_overtime',string="Validated overtime", store=True
    )

    @api.depends('extra_hours', 'approved_extra_hours')
    def _compute_native_overtime(self):
        for att in self:
            att.overtime_hours = att.extra_hours or 0.0
            att.validated_overtime_hours = att.approved_extra_hours or 0.0

    # ==========================================================
    # PLANNING INTEGRATION HELPER
    # ==========================================================
    def _get_shift_calendar(self):
        self.ensure_one()
        emp = self.employee_id
        if not emp:
            return self.env.company.resource_calendar_id

        check_time = self.check_in or self.check_out
        if not check_time:
            return emp.resource_calendar_id or self.env.company.resource_calendar_id

        tz = pytz.timezone(emp.tz or self.env.user.tz or 'UTC')
        check_time_local = pytz.utc.localize(check_time).astimezone(tz)
        local_day_start = check_time_local.replace(hour=0, minute=0, second=0, microsecond=0)
        local_day_end = local_day_start + timedelta(days=1)

        utc_day_start = local_day_start.astimezone(pytz.utc).replace(tzinfo=None)
        utc_day_end = local_day_end.astimezone(pytz.utc).replace(tzinfo=None)

        slot = self.env['planning.slot'].sudo().search([
            ('resource_id', '=', emp.resource_id.id),
            ('start_datetime', '<', utc_day_end),
            ('end_datetime', '>', utc_day_start),
            ('calendar_id', '!=', False),
            ('state', 'in', ['draft', 'published']),
        ], limit=1, order='start_datetime ASC')

        return slot.calendar_id if slot else (
                emp.resource_calendar_id or self.env.company.resource_calendar_id
        )

    # def _get_shift_times(self):
    #     self.ensure_one()
    #     cal = self._get_shift_calendar()
    #     if not cal or not self.check_in:
    #         return False, False
    #
    #     tz = pytz.timezone(cal.tz or self.employee_id.tz or 'UTC')
    #     check_in_local = fields.Datetime.context_timestamp(self, self.check_in)
    #     weekday = str(check_in_local.weekday())
    #
    #     shifts = cal.attendance_ids.filtered(
    #         lambda a: a.dayofweek == weekday and a.day_period != 'lunch'
    #     )
    #     if not shifts:
    #         return False, False
    #
    #     first_shift = min(shifts, key=lambda s: s.hour_from)
    #     last_shift = max(shifts, key=lambda s: s.hour_to)
    #
    #     shift_start_local = tz.localize(datetime.combine(
    #         check_in_local.date(),
    #         time(int(first_shift.hour_from), int((first_shift.hour_from % 1) * 60))
    #     ))
    #     shift_end_local = tz.localize(datetime.combine(
    #         check_in_local.date(),
    #         time(int(last_shift.hour_to), int((last_shift.hour_to % 1) * 60))
    #     ))
    #
    #     if last_shift.hour_to < first_shift.hour_from:
    #         shift_end_local += timedelta(days=1)
    #
    #     return (
    #         shift_start_local.astimezone(pytz.UTC).replace(tzinfo=None),
    #         shift_end_local.astimezone(pytz.UTC).replace(tzinfo=None),
    #     )

    def _get_shift_times(self):
        self.ensure_one()

        cal = self._get_shift_calendar()
        if not cal or not self.check_in:
            return False, False

        tz = pytz.timezone(cal.tz or self.employee_id.tz or 'UTC')

        check_in_local = fields.Datetime.context_timestamp(self, self.check_in)

        weekday = check_in_local.weekday()
        next_weekday = (weekday + 1) % 7

        # ---------------------------------------------------
        # GET TODAY SHIFTS
        # ---------------------------------------------------
        today_shifts = cal.attendance_ids.filtered(
            lambda a:
            int(a.dayofweek) == weekday
            and str(a.day_period).lower() != 'break'
        )

        shifts = today_shifts

        # ---------------------------------------------------
        # DETECT NIGHT SHIFT
        # ---------------------------------------------------
        has_late_shift = any(s.hour_to >= 22.0 for s in today_shifts)

        # ---------------------------------------------------
        # PULL NEXT DAY EARLY SHIFTS
        # ---------------------------------------------------
        if has_late_shift:
            next_day_shifts = cal.attendance_ids.filtered(
                lambda a:
                int(a.dayofweek) == next_weekday
                and str(a.day_period).lower() != 'break'
                and a.hour_from < 8.0
            )

            shifts |= next_day_shifts

        if not shifts:
            return False, False

        # ---------------------------------------------------
        # SORT SHIFTS PROPERLY
        # ---------------------------------------------------
        sorted_shifts = sorted(
            shifts,
            key=lambda s: (
                int(s.dayofweek),
                s.hour_from
            )
        )

        first_shift = sorted_shifts[0]
        last_shift = sorted_shifts[-1]

        # ---------------------------------------------------
        # SHIFT START
        # ---------------------------------------------------
        shift_start_local = tz.localize(datetime.combine(
            check_in_local.date(),
            time(
                int(first_shift.hour_from),
                int((first_shift.hour_from % 1) * 60)
            )
        ))

        # ---------------------------------------------------
        # SHIFT END DATE
        # ---------------------------------------------------
        end_date = check_in_local.date()

        if int(last_shift.dayofweek) != weekday:
            end_date += timedelta(days=1)

        # ---------------------------------------------------
        # HANDLE 24:00 SAFELY
        # ---------------------------------------------------
        if last_shift.hour_to >= 24.0:

            shift_end_local = tz.localize(datetime.combine(
                end_date,
                time(23, 59, 59)
            )) + timedelta(seconds=1)

        else:

            shift_end_local = tz.localize(datetime.combine(
                end_date,
                time(
                    int(last_shift.hour_to),
                    int((last_shift.hour_to % 1) * 60)
                )
            ))

        return (
            shift_start_local.astimezone(pytz.UTC).replace(tzinfo=None),
            shift_end_local.astimezone(pytz.UTC).replace(tzinfo=None),
        )

    @api.depends("check_in", "employee_id.resource_calendar_id")
    def _compute_base_scheduled(self):
        for att in self:
            shift_start, shift_end = att._get_shift_times()
            cal = att._get_shift_calendar()
            if not shift_start or not shift_end or not cal:
                att.base_scheduled_hours = 0.0
                continue
            att.base_scheduled_hours = round(cal.get_work_hours_count(shift_start, shift_end), 2)

    @api.depends("check_in", "employee_id.resource_calendar_id")
    def _compute_effective(self):
        for att in self:
            att.effective_check_in = att.check_in
            if not att.check_in:
                continue

            shift_start, _ = att._get_shift_times()
            if not shift_start:
                continue

            grace_end = shift_start + timedelta(minutes=30)
            if shift_start <= att.check_in <= grace_end:
                att.effective_check_in = shift_start

    # ==========================================================
    # 1. THE SMART PUNCH CALCULATOR (Dynamic Math)
    # ==========================================================
    @api.depends("effective_check_in", "check_in", "check_out", "employee_id.resource_calendar_id")
    def _compute_worked(self):
        for att in self:
            att.worked_hours_custom = 0.0
            att.permission_credit_applied = 0.0

            if not att.effective_check_in or not att.check_out:
                continue

            shift_start, shift_end = att._get_shift_times()
            cal = att._get_shift_calendar()

            # --- PART 1: EXACT PHYSICAL HOURS (Untouched & Safe) ---
            base_worked = 0.0
            if shift_start and cal:
                early_credit = 0.0
                if att.effective_check_in < shift_start:
                    actual_early_end = min(att.check_out, shift_start)
                    early_secs = max(0, (actual_early_end - att.effective_check_in).total_seconds())
                    early_credit = min(early_secs, 1800) / 3600.0  # Caps early grace at 30 mins

                calc_start = max(att.effective_check_in, shift_start)

                if att.check_out <= shift_start:
                    core_worked = 0.0
                else:
                    core_worked = cal.get_work_hours_count(calc_start, att.check_out)

                base_worked = core_worked + early_credit
            else:
                base_worked = (att.check_out - att.effective_check_in).total_seconds() / 3600.0

            # --- PART 2: SMART PERMISSION CREDIT (Half-Day Detector) ---
            permission_credit = 0.0
            if att.check_in:
                cal_tz = att._get_shift_calendar()
                tz = pytz.timezone((cal_tz.tz if cal_tz else None) or att.employee_id.tz or 'UTC')
                check_in_local = pytz.utc.localize(att.check_in).astimezone(tz)
                day_date = check_in_local.date()

                day_start_utc = check_in_local.replace(hour=0, minute=0, second=0).astimezone(pytz.utc).replace(
                    tzinfo=None)
                day_end_utc = check_in_local.replace(hour=23, minute=59, second=59).astimezone(pytz.utc).replace(
                    tzinfo=None)

                permission = self.env['hr.attendance.permission'].search([
                    ('employee_id', '=', att.employee_id.id),
                    ('date', '=', day_date),
                    ('state', '=', 'approved'),
                ], limit=1)

                if permission:
                    required_hours = 0.0
                    if shift_start and shift_end and cal:
                        required_hours = cal.get_work_hours_count(shift_start, shift_end)

                    if required_hours > 0:
                        all_punches = self.env['hr.attendance'].search([
                            ('employee_id', '=', att.employee_id.id),
                            ('check_in', '>=', day_start_utc),
                            ('check_in', '<=', day_end_utc),
                            ('check_out', '!=', False)
                        ]).sorted('check_in')

                        morning_worked = 0.0
                        afternoon_worked = 0.0
                        total_physical = 0.0

                        for p in all_punches:
                            p_start, _ = p._get_shift_times()
                            p_cal = p._get_shift_calendar()
                            p_base = 0.0
                            if p_start and p_cal and p.effective_check_in:
                                p_calc_start = max(p.effective_check_in, p_start)
                                if p.check_out > p_start:
                                    p_base = p_cal.get_work_hours_count(p_calc_start, p.check_out)
                                    if p.effective_check_in < p_start:
                                        p_early_secs = max(0, (min(p.check_out,
                                                                   p_start) - p.effective_check_in).total_seconds())
                                        p_base += min(p_early_secs, 1800) / 3600.0
                            else:
                                if p.effective_check_in:
                                    p_base = (p.check_out - p.effective_check_in).total_seconds() / 3600.0

                            total_physical += p_base

                            # Split into First/Second Half based on 1:00 PM (13:00)
                            p_check_in_local = pytz.utc.localize(p.check_in).astimezone(tz)
                            if p_check_in_local.hour < 13:
                                morning_worked += p_base
                            else:
                                afternoon_worked += p_base

                        # Handle current punch if not saved yet
                        actual_id = att._origin.id if hasattr(att, '_origin') and att._origin else att.id
                        if not isinstance(actual_id, int) or actual_id not in all_punches.ids:
                            total_physical += base_worked
                            if check_in_local.hour < 13:
                                morning_worked += base_worked
                            else:
                                afternoon_worked += base_worked

                        overall_shortfall = required_hours - total_physical

                        if overall_shortfall > 0:
                            half_target = required_hours / 2.0
                            morning_shortfall = max(0, half_target - morning_worked)
                            afternoon_shortfall = max(0, half_target - afternoon_worked)

                            max_credit = min(overall_shortfall, 1.0)
                            is_morning_punch = check_in_local.hour < 13

                            # Inject credit ONLY where the hours are missing
                            if is_morning_punch and morning_shortfall > 0:
                                morning_punches = [p for p in all_punches if
                                                   pytz.utc.localize(p.check_in).astimezone(tz).hour < 13]
                                first_morning_id = morning_punches[0].id if morning_punches else actual_id
                                if actual_id == first_morning_id or not isinstance(actual_id, int):
                                    permission_credit = min(morning_shortfall, max_credit)

                            elif not is_morning_punch and afternoon_shortfall > 0:
                                afternoon_punches = [p for p in all_punches if
                                                     pytz.utc.localize(p.check_in).astimezone(tz).hour >= 13]
                                first_afternoon_id = afternoon_punches[0].id if afternoon_punches else actual_id
                                if actual_id == first_afternoon_id or not isinstance(actual_id, int):
                                    # Ensure we don't exceed max_credit if morning also took some
                                    morning_taken = min(morning_shortfall,
                                                        max_credit) if morning_shortfall > 0 else 0.0
                                    remaining_credit = max(0, max_credit - morning_taken)
                                    permission_credit = min(afternoon_shortfall, remaining_credit)

            att.permission_credit_applied = round(permission_credit, 2)
            att.worked_hours_custom = round(base_worked + permission_credit, 2)

    # ==========================================================
    # 2. THE PENALTY JUDGE & DAILY TOTAL (🌟 Fixed Indentation!)
    # ==========================================================
    @api.depends("worked_hours_custom", "base_scheduled_hours", "check_in", "employee_id")
    def _compute_half_day(self):
        for att in self:
            # Reset values by default
            att.half_day_absent = False
            att.full_day_absent = False
            att.half_day_type = False
            att.daily_total_hours = 0.0

            if not att.check_in or not att.employee_id:
                continue

            required = att.base_scheduled_hours or 0.0
            if required <= 0.0:
                continue

            half_day_threshold = required / 2.0

            cal = att._get_shift_calendar()
            tz = pytz.timezone((cal.tz if cal else None) or att.employee_id.tz or 'UTC')
            check_in_local = pytz.utc.localize(att.check_in).astimezone(tz)

            day_start_utc = check_in_local.replace(hour=0, minute=0, second=0).astimezone(pytz.utc).replace(
                tzinfo=None)
            day_end_utc = check_in_local.replace(hour=23, minute=59, second=59).astimezone(pytz.utc).replace(
                tzinfo=None)

            actual_id = att._origin.id if hasattr(att, '_origin') and att._origin else att.id
            domain = [
                ('employee_id', '=', att.employee_id.id),
                ('check_in', '>=', day_start_utc),
                ('check_in', '<=', day_end_utc),
            ]
            if isinstance(actual_id, int):
                domain.append(('id', '!=', actual_id))

            other_records = self.env['hr.attendance'].search(domain)
            other_hours = sum(other_records.mapped('worked_hours_custom'))
            current_hours = att.worked_hours_custom or 0.0

            total_worked_today = other_hours + current_hours

            # Save the Grand Total to the database so the UI can see it!
            att.daily_total_hours = total_worked_today

            # THE DYNAMIC THRESHOLDS
            if total_worked_today < required:
                if total_worked_today < half_day_threshold:
                    att.full_day_absent = True
                else:
                    att.half_day_absent = True

                    shift_start, shift_end = att._get_shift_times()
                    if shift_start and shift_end:
                        # SURGICAL FIX: Combine all records for the day to find the true start and end times
                        all_records = other_records + att
                        first_check_in = min(all_records.mapped('check_in'))

                        # Safely get the latest check out (ignoring if they haven't checked out yet)
                        valid_check_outs = [c for c in all_records.mapped('check_out') if c]
                        last_check_out = max(valid_check_outs) if valid_check_outs else att.check_in

                        # Now measure the missed time against the TRUE day boundaries
                        missed_morning = max(0, (first_check_in - shift_start).total_seconds())
                        missed_afternoon = max(0, (shift_end - last_check_out).total_seconds())

                        if missed_morning > missed_afternoon:
                            att.half_day_type = 'first'
                        else:
                            att.half_day_type = 'second'
                    else:
                        att.half_day_type = 'second'

    @api.depends("check_in", "employee_id.resource_calendar_id", "half_day_absent", "full_day_absent",
                 "base_scheduled_hours")
    def _compute_scheduled(self):
        for att in self:
            cal = att._get_shift_calendar()
            if not att.check_in or not cal:
                att.scheduled_hours = 0.0
                continue

            # ZERO HARDCODING: Scheduled hours scales perfectly based on the calendar
            if att.full_day_absent:
                att.scheduled_hours = 0.0
            elif att.half_day_absent:
                att.scheduled_hours = (att.base_scheduled_hours or 0.0) / 2.0
            else:
                att.scheduled_hours = (att.base_scheduled_hours or 0.0)

    # ==========================================================
    # 3. COMPUTE: Extra Hours & Overtime
    # ==========================================================
    @api.depends("check_in", "check_out", "employee_id.resource_calendar_id")
    def _compute_extra(self):
        for att in self:
            att.extra_hours = 0.0
            if not att.check_in or not att.check_out:
                continue

            _, shift_end = att._get_shift_times()
            if not shift_end:
                continue

            if att.check_out > shift_end:
                raw_overtime = (att.check_out - shift_end).total_seconds() / 3600.0
                att.extra_hours = float(math.floor(raw_overtime))

    @api.depends("worked_hours_custom", "approved_extra_hours")
    def _compute_total(self):
        for att in self:
            att.total_hours = round((att.worked_hours_custom or 0.0) + (att.approved_extra_hours or 0.0), 2)

    # ==========================================================
    # 4. THE SIBLING SYNC (For Multiple Punches)
    # ==========================================================
    @api.model_create_multi
    def create(self, vals_list):
        records = super(HrAttendance, self).create(vals_list)
        records._sync_siblings_on_save()
        return records

    def write(self, vals):
        res = super(HrAttendance, self).write(vals)
        if 'check_out' in vals or 'check_in' in vals:
            self._sync_siblings_on_save()
        return res

    @api.model
    def save_attendance_photo(self, photo_base64, punch_type, geo_zone_id=False):
        """
        Called from JS after face verification.
        Creates a new attendance.photo record linked to this attendance,
        and maps the geo location field.
        punch_type: 'checkin' or 'checkout'
        """
        employee = self.env.user.employee_id
        if not employee:
            return False

        # We removed the if/else entirely!
        # Whether checking in or out, we just grab the most recent record.
        attendance = self.search([
            ('employee_id', '=', employee.id),
        ], order='id desc', limit=1)

        if not attendance:
            return False

        # Save the photo record
        self.env['attendance.photo'].sudo().create({
            'attendance_id': attendance.id,
            'photo': photo_base64,
            'punch_type': punch_type,
        })

        # Map the geo restriction ID to the corresponding field
        if geo_zone_id:
            if punch_type == 'checkin':
                attendance.sudo().write({'geo_restriction_id': geo_zone_id})
            elif punch_type == 'checkout':
                attendance.sudo().write({'check_out_geo_restriction_id': geo_zone_id})

        return True

    @api.model
    def check_employee_geo_allowed(self, latitude, longitude):
        """
        Called from JS before opening camera.
        Checks if employee is within any of their allowed office geo zones.
        Returns {'allowed': True/False, 'message': '...', 'zone_id': ID}
        """
        from geopy.distance import geodesic

        employee = self.env.user.employee_id
        if not employee:
            return {'allowed': False, 'message': 'No employee linked to your account.'}

        geo_locations = employee.geo_restriction_ids
        if not geo_locations:
            return {'allowed': False, 'message': 'No office locations configured for you. Contact HR.'}

        for geo in geo_locations:
            distance = geodesic(
                (geo.company_latitude, geo.company_longitude),
                (latitude, longitude)
            ).meters
            if distance <= geo.allowed_distance:
                # ---> THE ONLY CHANGE IS HERE: Changed 'geo_id' to 'zone_id'
                return {'allowed': True, 'zone_id': geo.id}

        return {
            'allowed': False,
            'message': 'You are outside the allowed office radius. Check-in not permitted.'
        }


    def _sync_siblings_on_save(self):
        """Forces all punches from the same day to recalculate together"""
        for att in self:
            if att.check_in and att.check_out:
                day_start = att.check_in.replace(hour=0, minute=0, second=0)
                day_end = att.check_in.replace(hour=23, minute=59, second=59)
                siblings = self.env['hr.attendance'].search([
                    ('employee_id', '=', att.employee_id.id),
                    ('check_in', '>=', day_start),
                    ('check_in', '<=', day_end)
                ])
                # Trigger Odoo's compute engine to refresh the day
                siblings._compute_worked()
                siblings._compute_half_day()

    # ==========================================================
    # 5. UI Display Fields & Legacy Code
    # ==========================================================
    day_of_week = fields.Selection([
        ('0', 'Mon'), ('1', 'Tue'), ('2', 'Wed'),
        ('3', 'Thu'), ('4', 'Fri'), ('5', 'Sat'), ('6', 'Sun'),
    ], string="Day", compute="_compute_day_of_week", store=True)

    @api.depends('check_in')
    def _compute_day_of_week(self):
        for att in self:
            att.day_of_week = str(att.check_in.weekday()) if att.check_in else False

    week_start = fields.Date(string="Week Start", compute="_compute_week_start", store=True)

    @api.depends('check_in')
    def _compute_week_start(self):
        for att in self:
            if att.check_in:
                att.week_start = att.check_in - timedelta(days=att.check_in.weekday())
            else:
                att.week_start = False

    daily_display = fields.Char(string="Hours", compute="_compute_daily_display", store=True)

    @api.depends('worked_hours_custom', 'extra_hours')
    def _compute_daily_display(self):
        def fmt(hours):
            if not hours: return "0:00"
            h = int(hours)
            m = int(round((hours - h) * 60))
            return f"{h}:{m:02d}"

        for att in self:
            worked = att.worked_hours_custom or 0.0
            extra = att.extra_hours or 0.0
            base = fmt(worked)
            att.daily_display = f"{base} (+{fmt(extra)})" if extra > 0 else base

    late_checkout_reason = fields.Text(string="Late Checkout Reason", tracking=True, store=True)
    late_checkout_state = fields.Selection([
        ('draft', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string="Late Checkout Status", default='draft', tracking=True)

    def action_approve_late_checkout(self):
        for rec in self:
            rec.write({'late_checkout_state': 'approved'})

    def action_reject_late_checkout(self):
        for rec in self:
            rec.write({'late_checkout_state': 'rejected'})

    @api.model
    def save_late_reason(self, reason):
        employee = self.env.user.employee_id
        if not employee:
            raise UserError("No employee linked to this user.")
        attendance = self.search([
            ('employee_id', '=', employee.id),
            ('check_out', '!=', False),
        ], order="check_out desc", limit=1)
        if not attendance:
            raise UserError("No attendance found.")
        if attendance.employee_id.id != employee.id:
            raise UserError("Not allowed.")
        attendance.sudo().write({
            'late_checkout_reason': reason,
            'late_checkout_state': 'draft',
        })
        attendance._send_late_checkout_email()
        return True

    approved_extra_hours = fields.Float(
        string="Approved Extra Hours",
        compute="_compute_approved_extra_hours",
        store=True,
    )

    @api.depends('extra_hours', 'late_checkout_state')
    def _compute_approved_extra_hours(self):
        for att in self:
            att.approved_extra_hours = (att.extra_hours if att.late_checkout_state == 'approved' else 0.0)

    @api.model
    def get_my_latest_attendance(self):
        employee = self.env.user.employee_id
        if not employee:
            return False
        attendance = self.search([
            ('employee_id', '=', employee.id),
            ('check_out', '!=', False),
        ], order='check_out desc', limit=1)
        if not attendance:
            return False
        return {
            'id': attendance.id,
            'extra_hours': attendance.extra_hours,
        }

    def _send_late_checkout_email(self):
        for att in self:
            manager = att.employee_id.parent_id
            if not manager:
                continue
            user = manager.user_id
            if not user or not user.email:
                continue
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            record_url = f"{base_url}/web#id={att.id}&model=hr.attendance&view_type=form"
            body = f"""
                <p>Dear {user.name},</p>
                <p>{att.employee_id.name} has checked out late and submitted a reason.</p>
                <p><b>Extra Hours:</b> {att.extra_hours:.2f}</p>
                <p><b>Reason:</b></p>
                <blockquote>{att.late_checkout_reason}</blockquote>
                <p><a href="{record_url}">Review &amp; Approve</a></p>
                <p>Regards,<br/>{self.env.user.name}</p>
            """
            try:
                self.env['mail.mail'].sudo().create({
                    'subject': f"Late Checkout Approval – {att.employee_id.name}",
                    'body_html': body,
                    'email_to': user.email,
                    'auto_delete': True,
                }).send()
            except Exception:
                pass

    can_approve_late_checkout = fields.Boolean(
        compute="_compute_can_approve_late_checkout", store=False
    )

    def _compute_can_approve_late_checkout(self):
        for att in self:
            manager = att.employee_id.parent_id
            current_employee = self.env.user.employee_id

            # Allow HR Administrators to approve/reject as well
            is_admin = self.env.user.has_group('hr_attendance.group_hr_attendance_manager')

            att.can_approve_late_checkout = bool(
                (manager and current_employee and manager.id == current_employee.id) or is_admin
            )

    @api.depends('worked_hours_custom', 'extra_hours', 'approved_extra_hours', 'late_checkout_state')
    def _compute_display_name(self):
        for att in self:
            std = round(att.worked_hours_custom or 0.0, 2)
            ext = round(att.extra_hours or 0.0, 2)
            if ext == 0:
                att.display_name = f"Std: {std}h"
                continue
            if att.late_checkout_state == 'approved':
                status = " Appr"
            elif att.late_checkout_state == 'rejected':
                status = " Rej"
            else:
                status = " Pend"
            att.display_name = f"Std: {std}h | Ext: {ext}h ({status})"

    # ==========================================================
    # EDP BOUNCER: WEEKEND RESTRICTION
    # ==========================================================
    @api.constrains('check_in', 'check_out')
    def _check_edp_restriction(self):
        for att in self:
            if not att.check_in:
                continue

            # 1. Figure out exactly what day it is
            tz = pytz.timezone(att.employee_id.tz or self.env.user.tz or 'UTC')
            check_in_local = pytz.utc.localize(att.check_in).astimezone(tz)

            weekday = check_in_local.weekday()  # Monday = 0, Saturday = 5, Sunday = 6
            day_of_month = check_in_local.day
            week_of_month = (day_of_month - 1) // 7 + 1

            # 2. Bulletproof Checkbox Reader
            get_param = self.env['ir.config_parameter'].sudo().get_param

            def is_active(param_name):
                return str(get_param(param_name, 'False')).strip().lower() in ['true', '1', 't', 'yes', 'y']

            restrict_sunday = is_active('attendance.edp_restrict_sunday')

            restricted_sats = []
            if is_active('attendance.edp_restrict_sat_1'): restricted_sats.append(1)
            if is_active('attendance.edp_restrict_sat_2'): restricted_sats.append(2)
            if is_active('attendance.edp_restrict_sat_3'): restricted_sats.append(3)
            if is_active('attendance.edp_restrict_sat_4'): restricted_sats.append(4)
            if is_active('attendance.edp_restrict_sat_5'): restricted_sats.append(5)

            # 3. Check if today hits the restricted rules
            is_sunday = (weekday == 6 and restrict_sunday)
            is_restricted_saturday = (weekday == 5 and week_of_month in restricted_sats)

            # 4. Setup Time boundaries for today
            local_day_start = check_in_local.replace(hour=0, minute=0, second=0, microsecond=0)
            local_day_end = local_day_start + timedelta(days=1)

            utc_day_start = local_day_start.astimezone(pytz.utc).replace(tzinfo=None)
            utc_day_end = local_day_end.astimezone(pytz.utc).replace(tzinfo=None)

            # 5. Check if today hits any restricted rule (Weekend only)
            if is_sunday or is_restricted_saturday:

                # 6. Check the Planning App for an approved EDP shift
                has_edp_slot = self.env['planning.slot'].sudo().search_count([
                    ('employee_id', '=', att.employee_id.id),
                    ('start_datetime', '<', utc_day_end),
                    ('end_datetime', '>', utc_day_start),
                    ('state', 'in', ['draft', 'published']),
                ])

                # 7. If they don't have a slot, kick them out!
                if not has_edp_slot:
                    if is_sunday:
                        reason_text = "Sunday"
                    else:
                        reason_text = f"the {week_of_month}st/nd/rd/th Saturday"

                    raise ValidationError(
                        f"EDP Restricted! \n\n"
                        f"Sorry {att.employee_id.name}, today is {reason_text}, which is an off-day according to company policy. "
                        f"You cannot check in unless you have an approved Extra Duty Plan (EDP) allocated in the schedule."
                    )