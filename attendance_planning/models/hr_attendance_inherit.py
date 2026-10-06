# -*- coding: utf-8 -*-
import math
import time as time_module
import logging
from odoo import models, fields, api
from datetime import datetime, time, timedelta
from odoo.exceptions import UserError, ValidationError
import pytz

_logger = logging.getLogger(__name__)


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
        # Extra/overtime hours are only accepted within a 4-hour window after
        # the shift ends. Checking out any later than that still counts as
        # 4 hours max — it's treated as the cap, not unlimited overtime.
        MAX_EXTRA_HOURS_WINDOW = 4.0

        for att in self:
            att.extra_hours = 0.0
            if not att.check_in or not att.check_out:
                continue

            _, shift_end = att._get_shift_times()
            if not shift_end:
                continue

            if att.check_out > shift_end:
                raw_overtime = (att.check_out - shift_end).total_seconds() / 3600.0
                capped_overtime = min(raw_overtime, MAX_EXTRA_HOURS_WINDOW)
                att.extra_hours = float(math.floor(capped_overtime))

    @api.depends("worked_hours_custom", "approved_extra_hours")
    def _compute_total(self):
        for att in self:
            att.total_hours = round((att.worked_hours_custom or 0.0) + (att.approved_extra_hours or 0.0), 2)

    # ==========================================================
    # 4. THE SIBLING SYNC & AUTO-APPROVAL NET
    # ==========================================================
    @api.model_create_multi
    def create(self, vals_list):
        records = super(HrAttendance, self).create(vals_list)
        records._sync_siblings_on_save()

        # 🟢 THE FIX: Auto-Approve if *extra hours* are under 4
        for att in records:
            if 0 < att.extra_hours < 4.0 and att.late_checkout_state == 'draft':
                att.late_checkout_state = 'approved'

        return records

    def write(self, vals):
        res = super(HrAttendance, self).write(vals)

        if 'check_out' in vals or 'check_in' in vals:
            self._sync_siblings_on_save()

            # 🟢 THE FIX: Auto-Approve if a manager edits the *extra hours* manually
            state_changed = False
            for att in self:
                if 0 < att.extra_hours < 4.0 and att.late_checkout_state == 'draft':
                    # Use super to write silently and avoid infinite loops
                    super(HrAttendance, att).write({'late_checkout_state': 'approved'})
                    state_changed = True

            if state_changed:
                self._sync_native_overtime_record()

        if 'late_checkout_state' in vals:
            self._sync_native_overtime_record()

        return res
    @api.model
    def face_punch_and_save_photo(self, photo_base64, geo_zone_id=False):
        """Atomic punch + photo save — punch and photo happen in ONE
        request/transaction, so there's no gap for a race to occur."""
        employee = self.env.user.employee_id
        if not employee:
            _logger.warning(
                "[face_punch_and_save_photo] No employee linked to user_id=%s (uid=%s)",
                self.env.user.id, self.env.uid
            )
            return {'success': False, 'error': 'No employee linked to your account.'}

        was_checked_in = employee.attendance_state == 'checked_in'
        _logger.info(
            "[face_punch_and_save_photo] START employee_id=%s (%s) current_state=%s geo_zone_id=%s",
            employee.id, employee.name, employee.attendance_state, geo_zone_id
        )

        try:
            employee.sudo()._attendance_action_change()
        except Exception:
            _logger.exception(
                "[face_punch_and_save_photo] _attendance_action_change() raised for employee_id=%s (%s)",
                employee.id, employee.name
            )
            raise

        attendance = employee.sudo().last_attendance_id

        if not attendance:
            _logger.error(
                "[face_punch_and_save_photo] Punch failed, no attendance record created for employee_id=%s (%s)",
                employee.id, employee.name
            )
            return {'success': False, 'error': 'Punch failed — no attendance record was created.'}

        punch_type = 'checkout' if was_checked_in else 'checkin'
        _logger.info(
            "[face_punch_and_save_photo] Punch OK employee_id=%s attendance_id=%s punch_type=%s",
            employee.id, attendance.id, punch_type
        )

        try:
            self.env['attendance.photo'].sudo().create({
                'attendance_id': attendance.id,
                'photo': photo_base64,
                'punch_type': punch_type,
            })
        except Exception as e:
            _logger.exception(
                "[face_punch_and_save_photo] Photo save FAILED for attendance_id=%s employee_id=%s "
                "punch_type=%s — attendance record itself was already created.",
                attendance.id, employee.id, punch_type
            )
            return {
                'success': False, 'error': str(e),
                'punch_succeeded': True,
                'attendance_id': attendance.id, 'punch_type': punch_type,
            }

        if geo_zone_id:
            field = 'geo_restriction_id' if punch_type == 'checkin' else 'check_out_geo_restriction_id'
            attendance.sudo().write({field: geo_zone_id})

        _logger.info(
            "[face_punch_and_save_photo] SUCCESS employee_id=%s attendance_id=%s punch_type=%s",
            employee.id, attendance.id, punch_type
        )
        return {'success': True, 'attendance_id': attendance.id, 'punch_type': punch_type}

    @api.model
    def save_attendance_photo(self, attendance_id, photo_base64, punch_type, geo_zone_id=False):
        """
        Called from JS after face verification. The attendance_id is now
        passed in directly by the JS (determined deterministically via a
        before/after open-session snapshot) — no server-side searching or
        guessing needed anymore.
        """
        employee = self.env.user.employee_id
        if not employee:
            _logger.warning(
                "[save_attendance_photo] No employee linked to user_id=%s (uid=%s), attendance_id=%s",
                self.env.user.id, self.env.uid, attendance_id
            )
            return {'success': False, 'error': 'No employee linked to your account.'}

        attendance = self.browse(attendance_id).exists()
        if not attendance or attendance.employee_id.id != employee.id:
            _logger.warning(
                "[save_attendance_photo] Invalid/unauthorized attendance_id=%s for employee_id=%s "
                "(record_exists=%s, owner_id=%s)",
                attendance_id, employee.id, bool(attendance),
                attendance.employee_id.id if attendance else None
            )
            return {'success': False, 'error': 'Invalid or unauthorized attendance record.'}

        try:
            self.env['attendance.photo'].sudo().create({
                'attendance_id': attendance.id,
                'photo': photo_base64,
                'punch_type': punch_type,
            })
        except Exception as e:
            _logger.exception(
                "[save_attendance_photo] Photo save FAILED for attendance_id=%s employee_id=%s punch_type=%s",
                attendance.id, employee.id, punch_type
            )
            return {'success': False, 'error': str(e)}

        if geo_zone_id:
            if punch_type == 'checkin':
                attendance.sudo().write({'geo_restriction_id': geo_zone_id})
            elif punch_type == 'checkout':
                attendance.sudo().write({'check_out_geo_restriction_id': geo_zone_id})

        _logger.info(
            "[save_attendance_photo] SUCCESS attendance_id=%s employee_id=%s punch_type=%s geo_zone_id=%s",
            attendance.id, employee.id, punch_type, geo_zone_id
        )
        return {'success': True, 'attendance_id': attendance.id}


    @api.model
    def get_open_attendance_id(self):
        """Returns the id of the employee's currently open (not checked-out)
        attendance session, or False if none. Called by JS before AND after
        a punch to deterministically identify which record that specific
        punch touched — no searching by 'latest timestamp', no race."""
        employee = self.env.user.employee_id
        if not employee:
            return False
        att = self.search([
            ('employee_id', '=', employee.id),
            ('check_out', '=', False),
        ], order='check_in desc', limit=1)
        return att.id if att else False



    # ==========================================================
    # AUTO-CHECKOUT REMINDER (post-shift nudge popup)
    # ==========================================================
    @api.model
    def get_open_session_reminder_info(self):
        """Called every minute by the client-side reminder timer.
        Tells the JS whether the employee is still checked in, and if so,
        what the shift-end time is (UTC ISO string) so the JS can decide
        locally when to start/keep popping the reminder. Read-only —
        never mutates anything.

        TEST MODE: if the system parameter
        'attendance_planning.auto_checkout_test_mode' is set to 'True',
        the real shift-end calculation is bypassed and "shift end" is
        treated as (check_in + 1 minute), and the JS is told to use a
        much shorter grace/ignore window — purely so this feature can be
        tested in a couple of minutes instead of waiting for a real
        shift to end. Leave this OFF ('False' or unset) in production —
        it does not change anything else about the module."""
        employee = self.env.user.employee_id
        if not employee:
            return False

        att = self.search([
            ('employee_id', '=', employee.id),
            ('check_out', '=', False),
        ], order='check_in desc', limit=1)

        if not att:
            return False

        test_mode = self.env['ir.config_parameter'].sudo().get_param(
            'attendance_planning.auto_checkout_test_mode', 'False'
        ) == 'True'

        if test_mode:
            shift_end = att.check_in + timedelta(minutes=1)
        else:
            _, shift_end = att._get_shift_times()

        if not shift_end:
            return False

        return {
            'attendance_id': att.id,
            'shift_end': fields.Datetime.to_string(shift_end),
            'server_now': fields.Datetime.to_string(fields.Datetime.now()),
            'test_mode': test_mode,
        }

    @api.model
    def keep_working_ping(self, attendance_id):
        """Called when the employee taps 'Yes' on the reminder popup.
        Purely a heartbeat for now — kept as its own endpoint in case you
        later want to log every 'still working' confirmation."""
        att = self.browse(attendance_id).exists()
        if not att or att.employee_id.id != self.env.user.employee_id.id:
            return False
        return True

    @api.model
    def checkout_now_explicit_no(self, attendance_id):
        """Called when the employee actively taps 'No, check me out' on the
        reminder popup. This IS a response, so it does NOT get the NR flag
        — it's just a normal checkout, and goes through the same
        extra_hours / late_checkout_state logic as any other checkout."""
        employee = self.env.user.employee_id
        if not employee:
            return {'success': False, 'error': 'No employee linked to your account.'}

        att = self.browse(attendance_id).exists()
        if not att or att.employee_id.id != employee.id:
            return {'success': False, 'error': 'Invalid or unauthorized attendance record.'}

        if att.check_out:
            return {'success': True, 'already_checked_out': True}

        att.sudo().write({'check_out': fields.Datetime.now()})
        return {'success': True, 'attendance_id': att.id}

    @api.model
    def send_checkout_push_reminder(self, attendance_id, stage):
        """Sends a real phone push notification (via Odoo Enterprise
        mobile app's inbox notification channel / configured Firebase Web
        Push for browser users) alongside the in-browser popup.
        Fire-and-forget from the JS side — never raises, so a push
        failure can't break the reminder/checkout flow itself.

        stage: 'shift_end' (phase 1, every 1 min) or 'ot_cap' (phase 2,
        every 3 min during the post-4h grace nudges).
        """
        att = self.sudo().browse(attendance_id).exists()
        if not att or not att.employee_id.user_id or not att.employee_id.user_id.partner_id:
            return False

        if stage == 'ot_cap':
            subject = "Maximum extra hours reached"
            body = "You've reached the 4-hour extra-time limit. Please check out now."
        else:
            subject = "You haven't checked out"
            body = "Your shift has ended. Are you working extra hours? Please respond or check out."

        try:
            self.env['mail.thread'].sudo().message_notify(
                partner_ids=[att.employee_id.user_id.partner_id.id],
                subject=subject,
                body=body,
            )
        except Exception:
            # Never let a push failure interrupt the checkout/reminder flow.
            return False
        return True

    @api.model
    def force_auto_checkout_no_response(self, attendance_id):
        """Called by the client after ~15 minutes of the reminder popup
        being ignored. Checks the employee out immediately (no face
        verification — this is a silent system-triggered checkout) and
        stamps the record as 'no_response' instead of 'draft'/'approved'
        so it never silently counts toward P+OT pay. It shows up as its
        own NR legend entry on the attendance sheet for manager review."""
        employee = self.env.user.employee_id
        if not employee:
            return {'success': False, 'error': 'No employee linked to your account.'}

        att = self.browse(attendance_id).exists()
        if not att or att.employee_id.id != employee.id:
            return {'success': False, 'error': 'Invalid or unauthorized attendance record.'}

        if att.check_out:
            # Already checked out by some other path (e.g. employee clicked
            # the real checkout button meanwhile) — nothing to do.
            return {'success': True, 'already_checked_out': True}

        att.sudo().write({
            'check_out': fields.Datetime.now(),
            'late_checkout_state': 'no_response',
            'was_auto_checkout_no_response': True,
            'late_checkout_reason': 'Auto checked-out by system — employee did not respond '
                                     'to the "working extra hours?" reminder.',
        })

        att._send_late_checkout_email()
        return {'success': True, 'attendance_id': att.id}

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
            _logger.warning(
                "[check_employee_geo_allowed] No employee linked to user_id=%s (uid=%s)",
                self.env.user.id, self.env.uid
            )
            return {'allowed': False, 'message': 'No employee linked to your account.'}

        if employee.bypass_geo_restriction:
            _logger.info(
                "[check_employee_geo_allowed] employee_id=%s (%s) has geo-bypass enabled — allowed.",
                employee.id, employee.name
            )
            return {'allowed': True, 'zone_id': False}

        geo_locations = employee.geo_restriction_ids
        if not geo_locations:
            _logger.warning(
                "[check_employee_geo_allowed] employee_id=%s (%s) has NO geo zones configured — blocked.",
                employee.id, employee.name
            )
            return {'allowed': False, 'message': 'No office locations configured for you. Contact HR.'}

        for geo in geo_locations:
            distance = geodesic(
                (geo.company_latitude, geo.company_longitude),
                (latitude, longitude)
            ).meters
            if distance <= geo.allowed_distance:
                _logger.info(
                    "[check_employee_geo_allowed] employee_id=%s ALLOWED, matched zone_id=%s (%.1fm <= %.1fm)",
                    employee.id, geo.id, distance, geo.allowed_distance
                )
                return {'allowed': True, 'zone_id': geo.id}

        _logger.warning(
            "[check_employee_geo_allowed] employee_id=%s (%s) BLOCKED — outside all %d configured zone(s). "
            "employee_lat=%s employee_lng=%s",
            employee.id, employee.name, len(geo_locations), latitude, longitude
        )
        return {
            'allowed': False,
            'message': 'You are outside the allowed office radius. Check-in not permitted.'
        }

    @api.model
    def is_geo_bypass_employee(self):
        """Instant check — no GPS needed. Lets the frontend skip the GPS
        fetch entirely for employees flagged 'Allow Check-in Anywhere',
        instead of fetching GPS first and only THEN discovering it wasn't
        even needed."""
        employee = self.env.user.employee_id
        if not employee:
            return False
        return bool(employee.bypass_geo_restriction)


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

    def _sync_native_overtime_record(self):

        for att in self:
            if not att.employee_id or not att.check_in:
                continue

            att_date = att.check_in.date()
            line_model = self.env['hr.attendance.overtime.line'].sudo()

            existing_line = line_model.search([
                ('employee_id', '=', att.employee_id.id),
                ('date', '=', att_date),
            ], limit=1)

            if not existing_line:
                continue

            target_duration = att.approved_extra_hours or 0.0

            if existing_line.duration != target_duration:
                existing_line.write({'duration': target_duration})

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
        ('no_response', 'No Response'),
    ], string="Late Checkout Status", default='draft', tracking=True)

    # Sticky marker: stays True forever once this record was force-checked-out
    # by the no-response flow, even after late_checkout_state later moves on
    # to 'approved'/'rejected'. Used only to scope the P->P/A->A downgrade-on-
    # reject penalty to NR-originated records, so it never touches the
    # pre-existing normal late-checkout approve/reject flow.
    was_auto_checkout_no_response = fields.Boolean(default=False, copy=False)

    def _can_review_late_checkout(self):
        """True if the current user is allowed to approve/reject this
        record's late-checkout / no-response entry: HR OT-admin, or any
        manager anywhere up this employee's reporting chain (not just the
        direct manager). Runs fully under sudo so that just checking this
        doesn't itself get blocked by hr.attendance's normal 'only see your
        own record' access rights/rules — we're intentionally replacing
        that with our own hierarchy-based check here."""
        self.ensure_one()
        rec = self.sudo()
        if self.env.user.has_group('hr_attendance.group_hr_attendance_manager'):
            return True
        manager = rec.employee_id.parent_id
        seen = set()
        while manager and manager.id not in seen:
            if manager.user_id.id == self.env.user.id:
                return True
            seen.add(manager.id)
            manager = manager.parent_id
        return False

    def action_approve_late_checkout(self):
        for rec in self:
            rec_sudo = rec.sudo()
            if not rec_sudo._can_review_late_checkout():
                raise UserError("You don't have permission to approve this employee's attendance.")
            rec_sudo.write({'late_checkout_state': 'approved'})

    def action_reject_late_checkout(self):
        for rec in self:
            rec_sudo = rec.sudo()
            if not rec_sudo._can_review_late_checkout():
                raise UserError("You don't have permission to reject this employee's attendance.")
            rec_sudo.write({'late_checkout_state': 'rejected'})

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

        #  THE FIX: Only trigger approval logic if OT is 4 hours or more
        if attendance.extra_hours >= 4.0:
            attendance.sudo().write({
                'late_checkout_reason': reason,
                'late_checkout_state': 'draft',  # Keeps it pending for manager
            })
            attendance._send_late_checkout_email()
        else:
            # If it's less than 4 hours, auto-approve it so the manager gets no email
            # and the system automatically accumulates it in the red column!
            attendance.sudo().write({
                'late_checkout_reason': reason,
                'late_checkout_state': 'approved',
            })

        return True

    approved_extra_hours = fields.Float(
        string="Approved Extra Hours",
        compute="_compute_approved_extra_hours",
        store=True,
    )

    @api.depends('extra_hours', 'late_checkout_state')
    def _compute_approved_extra_hours(self):
        for att in self:
            # NR (No Response) is a hold state — never auto-pay OT for it,
            # no matter how small extra_hours is. A manager must review and
            # explicitly approve/reject it first.
            if att.late_checkout_state == 'no_response':
                att.approved_extra_hours = 0.0
                continue

            #  NEW: Auto-approve small OT, strictly block 4+ hours!
            if att.extra_hours > 0 and att.extra_hours < 4.0:
                att.approved_extra_hours = att.extra_hours
            else:
                # If it's 4.0 or more, it stays 0.0 UNTIL the manager clicks approve
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
    # EDP BOUNCER: TWO-TRACK RESTRICTION (Regular vs Rotational)
    # ==========================================================
    @api.constrains('check_in', 'check_out')
    def _check_edp_restriction(self):
        for att in self:
            if not att.check_in:
                continue

            emp = att.employee_id

            # 1. Figure out exactly what day it is
            tz = pytz.timezone(emp.tz or self.env.user.tz or 'UTC')
            check_in_local = pytz.utc.localize(att.check_in).astimezone(tz)

            weekday = check_in_local.weekday()  # Monday = 0, Saturday = 5, Sunday = 6
            day_of_month = check_in_local.day
            week_of_month = (day_of_month - 1) // 7 + 1

            # 2. Setup Time boundaries for today (needed by both tracks)
            local_day_start = check_in_local.replace(hour=0, minute=0, second=0, microsecond=0)
            local_day_end = local_day_start + timedelta(days=1)

            utc_day_start = local_day_start.astimezone(pytz.utc).replace(tzinfo=None)
            utc_day_end = local_day_end.astimezone(pytz.utc).replace(tzinfo=None)

            # ==================================================
            # TRACK B: ROTATIONAL SHIFT EMPLOYEES
            # ==================================================
            if emp.shift_type == 'rotational':
                has_slot = self.env['planning.slot'].sudo().search_count([
                    ('employee_id', '=', emp.id),
                    ('start_datetime', '<', utc_day_end),
                    ('end_datetime', '>', utc_day_start),
                    ('state', '=', 'published'),
                    ('is_week_off', '!=', True),  # ← ADDED THIS LINE
                ])

                if not has_slot:
                    raise ValidationError(
                        f"Week-Off Detected! \n\n"
                        f"Sorry {emp.name}, you don't have a shift scheduled for today in the Planning app, "
                        f"which means today is your week-off. "
                        f"You cannot check in unless you have an approved Extra Duty Plan (EDP) allocated in the schedule."
                    )
                continue  # Rotational handled, skip Track A entirely

            # ==================================================
            # TRACK A: REGULAR SHIFT EMPLOYEES (unchanged logic)
            # ==================================================

            # 3. Bulletproof Checkbox Reader
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

            # 4. Check if today hits the restricted rules
            is_sunday = (weekday == 6 and restrict_sunday)
            is_restricted_saturday = (weekday == 5 and week_of_month in restricted_sats)

            # 5. Check if today hits any restricted rule (Weekend only)
            if is_sunday or is_restricted_saturday:

                # 6. Check the Planning App for an approved EDP shift
                has_edp_slot = self.env['planning.slot'].sudo().search_count([
                    ('employee_id', '=', emp.id),
                    ('start_datetime', '<', utc_day_end),
                    ('end_datetime', '>', utc_day_start),
                    ('state', '=', 'published'),
                    ('is_week_off', '!=', True),  # ← ADDED THIS LINE
                ])

                # 7. If they don't have a slot, kick them out!
                if not has_edp_slot:
                    if is_sunday:
                        reason_text = "Sunday"
                    else:
                        reason_text = f"the {week_of_month}st/nd/rd/th Saturday"

                    raise ValidationError(
                        f"EDP Restricted! \n\n"
                        f"Sorry {emp.name}, today is {reason_text}, which is an off-day according to company policy. "
                        f"You cannot check in unless you have an approved Extra Duty Plan (EDP) allocated in the schedule."
                    )