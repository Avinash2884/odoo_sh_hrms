from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta, time
import pytz
import logging

_logger = logging.getLogger(__name__)


class PlanningSlot(models.Model):
    _inherit = 'planning.slot'

    calendar_id = fields.Many2one('resource.calendar', string='Shift Template')
    allocated_hours = fields.Float(compute='_compute_allocated_hours', store=True, readonly=False)
    allocated_percentage = fields.Float(compute='_compute_allocated_percentage', store=True, readonly=False)

    ls_employee_id = fields.Char(string="Employee ID", related='employee_id.ls_employee_id', store=True)
    import_employee_id = fields.Char(string="Import Employee ID")
    import_date = fields.Date(string="Import Date")

    department_id = fields.Many2one('hr.department', string="Department", related='employee_id.department_id',
                                    store=True, readonly=True)

    #  THE NUCLEAR FIX: A completely disconnected, standalone field.
    # No compute, no inverse, no onchange. Odoo's JS cannot touch this!
    shift_date = fields.Date(string="Planned Date")

    # ============ NEW FIELDS FOR WEEK OFF ============
    is_week_off = fields.Boolean(
        string="Is Week Off",
        default=False,
        help="True if this slot represents a week-off day (no shift assigned)"
    )

    shift_display = fields.Char(
        string="Shift_Template",
        compute="_compute_shift_display",
        store=True,
        help="Shows shift name or 'Week Off'"
    )

    @api.depends('calendar_id', 'is_week_off')
    def _compute_shift_display(self):
        """Display either shift name or 'Week Off' label"""
        for rec in self:
            if rec.is_week_off:
                rec.shift_display = 'Week Off'
            else:
                rec.shift_display = rec.calendar_id.name if rec.calendar_id else ''

    # ============ END NEW FIELDS ============


    def _get_work_hours(self, calendar, date_local):
        dayofweek = str(date_local.weekday())
        work_lines = calendar.attendance_ids.filtered(lambda a: a.dayofweek == dayofweek and a.day_period != 'lunch')
        if not work_lines: return 0.0
        return sum(att.hour_to - att.hour_from for att in work_lines)

    @api.depends('start_datetime', 'end_datetime', 'employee_id', 'calendar_id')
    def _compute_allocated_hours(self):
        for slot in self:
            if slot.calendar_id and slot.start_datetime and slot.end_datetime:
                tz_name = slot.calendar_id.tz or self.env.user.tz or 'UTC'
                local_tz = pytz.timezone(tz_name)
                start_local = slot.start_datetime.replace(tzinfo=pytz.utc).astimezone(local_tz)
                slot.allocated_hours = self._get_work_hours(slot.calendar_id, start_local)
            else:
                super(PlanningSlot, slot)._compute_allocated_hours()

    @api.depends('allocated_hours', 'start_datetime', 'end_datetime', 'calendar_id')
    def _compute_allocated_percentage(self):
        for slot in self:
            if slot.calendar_id:
                slot.allocated_percentage = 100.0
            else:
                super(PlanningSlot, slot)._compute_allocated_percentage()

    # ==========================================================
    #  CREATION INTERCEPTOR
    # ==========================================================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # 1. Excel Employee ID
            if vals.get('import_employee_id'):
                custom_id = str(vals['import_employee_id']).strip()
                employee = self.env['hr.employee'].search([('ls_employee_id', '=', custom_id)], limit=1)
                if employee:
                    vals['employee_id'] = employee.id
                    vals['resource_id'] = employee.resource_id.id
                    vals['import_employee_id'] = False
                else:
                    raise UserError(f"IMPORT HALTED: Could not find Employee ID '{custom_id}'.")

            # =========================================================
            # 2. NEW LOGIC: Handle WEEK OFF slots (no calendar_id required)
            # =========================================================
            if vals.get('is_week_off'):
                target_date = vals.get('import_date') or vals.get('shift_date')
                if target_date:
                    import_date_val = fields.Date.to_date(target_date)

                    # Set full-day span so Gantt renders it
                    vals['shift_date'] = import_date_val
                    vals['start_datetime'] = datetime.combine(import_date_val, time(0, 0))
                    vals['end_datetime'] = datetime.combine(import_date_val, time(23, 59))
                    vals['allocated_hours'] = 0.0
                    vals['allocated_percentage'] = 0.0
                    vals['calendar_id'] = False  # No shift template for week off
                    vals['import_date'] = False
                continue  # Skip the normal shift processing (Steps 3 & 4) below
            # =========================================================

            # 3. Grab HR's typed Date (or Excel import date) and do the math BEFORE saving
            target_date = vals.get('import_date') or vals.get('shift_date')
            if target_date and vals.get('calendar_id'):
                calendar = self.env['resource.calendar'].browse(vals['calendar_id'])
                if not calendar.exists():
                    raise UserError(f"Shift Template ID {vals['calendar_id']} does not exist.")

                import_date_val = fields.Date.to_date(target_date)
                weekday_str = str(import_date_val.weekday())
                work_lines = calendar.attendance_ids.filtered(
                    lambda a: a.dayofweek == weekday_str and a.day_period != 'lunch')

                if not work_lines:
                    raise UserError(
                        f"Template '{calendar.name}' has no hours defined for {import_date_val.strftime('%A')}.")

                first_shift = min(work_lines, key=lambda s: s.hour_from)
                last_shift = max(work_lines, key=lambda s: s.hour_to)

                emp_tz = False
                if vals.get('employee_id'):
                    emp = self.env['hr.employee'].browse(vals.get('employee_id'))
                    emp_tz = emp.tz
                tz_name = calendar.tz or emp_tz or self.env.user.tz or 'UTC'
                tz = pytz.timezone(tz_name)

                start_local = tz.localize(datetime.combine(import_date_val, time(int(first_shift.hour_from), int((
                                                                                                                         first_shift.hour_from % 1) * 60))))
                end_local = tz.localize(datetime.combine(import_date_val, time(int(last_shift.hour_to),
                                                                               int((last_shift.hour_to % 1) * 60))))

                vals['start_datetime'] = start_local.astimezone(pytz.utc).replace(tzinfo=None)
                vals['end_datetime'] = end_local.astimezone(pytz.utc).replace(tzinfo=None)
                vals['shift_date'] = target_date
                if 'import_date' in vals:
                    vals['import_date'] = False

            # 4. Handle Allocated Hours
            if vals.get('calendar_id') and vals.get('start_datetime'):
                calendar = self.env['resource.calendar'].browse(vals['calendar_id'])
                start_dt = vals['start_datetime']
                if isinstance(start_dt, str): start_dt = datetime.fromisoformat(start_dt)
                tz_name = calendar.tz or self.env.user.tz or 'UTC'
                local_tz = pytz.timezone(tz_name)
                start_local = start_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
                dayofweek = str(start_local.weekday())
                work_lines = calendar.attendance_ids.filtered(
                    lambda a: a.dayofweek == dayofweek and a.day_period != 'lunch')
                if work_lines:
                    vals['allocated_hours'] = sum(att.hour_to - att.hour_from for att in work_lines)
                    vals['allocated_percentage'] = 100.0

        records = super(PlanningSlot, self).create(vals_list)

        # 5. If a shift was created on the Gantt Chart natively, back-fill our clean date
        for rec in records:
            if rec.start_datetime and not rec.shift_date:
                tz_name = rec.calendar_id.tz or rec.employee_id.tz or self.env.user.tz or 'UTC'
                local_tz = pytz.timezone(tz_name)
                calc_date = rec.start_datetime.replace(tzinfo=pytz.utc).astimezone(local_tz).date()
                self.env.cr.execute("UPDATE planning_slot SET shift_date=%s WHERE id=%s", (calc_date, rec.id))

            # Backfill allocated hours
            if rec.calendar_id and rec.start_datetime:
                tz_name = rec.calendar_id.tz or self.env.user.tz or 'UTC'
                local_tz = pytz.timezone(tz_name)
                start_local = rec.start_datetime.replace(tzinfo=pytz.utc).astimezone(local_tz)
                dayofweek = str(start_local.weekday())
                work_lines = rec.calendar_id.attendance_ids.filtered(
                    lambda a: a.dayofweek == dayofweek and a.day_period != 'lunch')
                if work_lines:
                    exact_hours = sum(att.hour_to - att.hour_from for att in work_lines)
                    if rec.allocated_hours != exact_hours:
                        self.env.cr.execute(
                            "UPDATE planning_slot SET allocated_hours=%s, allocated_percentage=%s WHERE id=%s",
                            (exact_hours, 100.0, rec.id))

        records.invalidate_recordset()
        return records

    # ==========================================================
    #  EDIT INTERCEPTOR (Direct SQL Database Bypass)
    # ==========================================================
    def write(self, vals):
        # 1. Save whatever HR typed first
        res = super(PlanningSlot, self).write(vals)

        # 2. Wait until the save is complete, then calculate the hidden math in the background
        for slot in self:
            # SCENARIO A: HR updated the 'Planned Date' or 'Shift Template' in the List View
            if ('shift_date' in vals or 'calendar_id' in vals) and slot.shift_date and slot.calendar_id:
                weekday_str = str(slot.shift_date.weekday())
                work_lines = slot.calendar_id.attendance_ids.filtered(
                    lambda a: a.dayofweek == weekday_str and a.day_period != 'lunch')

                if not work_lines:
                    raise UserError(
                        f"Template '{slot.calendar_id.name}' has no hours defined for {slot.shift_date.strftime('%A')}.")

                first_shift = min(work_lines, key=lambda s: s.hour_from)
                last_shift = max(work_lines, key=lambda s: s.hour_to)
                tz = pytz.timezone(slot.calendar_id.tz or slot.employee_id.tz or self.env.user.tz or 'UTC')

                start_local = tz.localize(datetime.combine(slot.shift_date, time(int(first_shift.hour_from), int((
                                                                                                                             first_shift.hour_from % 1) * 60))))
                end_local = tz.localize(datetime.combine(slot.shift_date, time(int(last_shift.hour_to),
                                                                               int((last_shift.hour_to % 1) * 60))))

                start_utc = start_local.astimezone(pytz.utc).replace(tzinfo=None)
                end_utc = end_local.astimezone(pytz.utc).replace(tzinfo=None)

                # Execute Raw SQL to force the timestamps into the database without Odoo noticing or fighting back
                self.env.cr.execute("UPDATE planning_slot SET start_datetime=%s, end_datetime=%s WHERE id=%s",
                                    (start_utc, end_utc, slot.id))

            # SCENARIO B: HR dragged and dropped a shift directly on the Gantt Chart (native time change)
            elif 'start_datetime' in vals and slot.start_datetime:
                tz_name = slot.calendar_id.tz or slot.employee_id.tz or self.env.user.tz or 'UTC'
                local_tz = pytz.timezone(tz_name)
                calc_date = slot.start_datetime.replace(tzinfo=pytz.utc).astimezone(local_tz).date()
                self.env.cr.execute("UPDATE planning_slot SET shift_date=%s WHERE id=%s", (calc_date, slot.id))

            # Keep Allocated Hours accurate
            if 'start_datetime' in vals or 'end_datetime' in vals or 'calendar_id' in vals:
                if slot.calendar_id and slot.start_datetime:
                    tz_name = slot.calendar_id.tz or self.env.user.tz or 'UTC'
                    local_tz = pytz.timezone(tz_name)
                    start_local = slot.start_datetime.replace(tzinfo=pytz.utc).astimezone(local_tz)
                    dayofweek = str(start_local.weekday())
                    work_lines = slot.calendar_id.attendance_ids.filtered(
                        lambda a: a.dayofweek == dayofweek and a.day_period != 'lunch')
                    if work_lines:
                        exact_hours = sum(att.hour_to - att.hour_from for att in work_lines)
                        if slot.allocated_hours != exact_hours:
                            self.env.cr.execute(
                                "UPDATE planning_slot SET allocated_hours=%s, allocated_percentage=%s WHERE id=%s",
                                (exact_hours, 100.0, slot.id))

        self.invalidate_recordset()
        return res

    @api.model
    def get_gantt_data(self, *args, **kwargs):
        result = super().get_gantt_data(*args, **kwargs)
        if isinstance(result, dict) and 'working_periods' in result:
            for res_id in result['working_periods'].keys():
                result['working_periods'][res_id] = [["1970-01-01 00:00:00", "2099-12-31 23:59:59"]]
        return result


