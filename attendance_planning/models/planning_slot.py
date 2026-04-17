# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime, timedelta
import pytz

class PlanningSlot(models.Model):
    _inherit = 'planning.slot'

    calendar_id = fields.Many2one('resource.calendar', string='Shift Template')
    allocated_hours = fields.Float(compute='_compute_allocated_hours', store=True, readonly=False)
    allocated_percentage = fields.Float(compute='_compute_allocated_percentage', store=True, readonly=False)

    def _get_work_hours(self, calendar, date_local):
        dayofweek = str(date_local.weekday())
        work_lines = calendar.attendance_ids.filtered(
            lambda a: a.dayofweek == dayofweek and a.day_period != 'lunch'
        )
        if not work_lines:
            return 0.0
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('calendar_id') and vals.get('start_datetime'):
                calendar = self.env['resource.calendar'].browse(vals['calendar_id'])
                start_dt = vals['start_datetime']
                if isinstance(start_dt, str):
                    start_dt = datetime.fromisoformat(start_dt)
                tz_name = calendar.tz or self.env.user.tz or 'UTC'
                local_tz = pytz.timezone(tz_name)
                start_local = start_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
                dayofweek = str(start_local.weekday())
                work_lines = calendar.attendance_ids.filtered(
                    lambda a: a.dayofweek == dayofweek and a.day_period != 'lunch'
                )
                if work_lines:
                    vals['allocated_hours'] = sum(att.hour_to - att.hour_from for att in work_lines)
                    vals['allocated_percentage'] = 100.0

        records = super().create(vals_list)

        for record in records:
            if record.calendar_id and record.start_datetime:
                tz_name = record.calendar_id.tz or self.env.user.tz or 'UTC'
                local_tz = pytz.timezone(tz_name)
                start_local = record.start_datetime.replace(tzinfo=pytz.utc).astimezone(local_tz)
                dayofweek = str(start_local.weekday())
                work_lines = record.calendar_id.attendance_ids.filtered(
                    lambda a: a.dayofweek == dayofweek and a.day_period != 'lunch'
                )
                if work_lines:
                    exact_hours = sum(att.hour_to - att.hour_from for att in work_lines)
                    if record.allocated_hours != exact_hours:
                        self.env.cr.execute(
                            "UPDATE planning_slot SET allocated_hours=%s, allocated_percentage=%s WHERE id=%s",
                            (exact_hours, 100.0, record.id)
                        )
                        record.invalidate_recordset(['allocated_hours', 'allocated_percentage'])

        return records

    def write(self, vals):
        res = super().write(vals)
        if 'start_datetime' in vals or 'end_datetime' in vals or 'calendar_id' in vals:
            for slot in self:
                if slot.calendar_id and slot.start_datetime:
                    tz_name = slot.calendar_id.tz or self.env.user.tz or 'UTC'
                    local_tz = pytz.timezone(tz_name)
                    start_local = slot.start_datetime.replace(tzinfo=pytz.utc).astimezone(local_tz)
                    dayofweek = str(start_local.weekday())
                    work_lines = slot.calendar_id.attendance_ids.filtered(
                        lambda a: a.dayofweek == dayofweek and a.day_period != 'lunch'
                    )
                    if work_lines:
                        exact_hours = sum(att.hour_to - att.hour_from for att in work_lines)
                        if slot.allocated_hours != exact_hours:
                            self.env.cr.execute(
                                "UPDATE planning_slot SET allocated_hours=%s, allocated_percentage=%s WHERE id=%s",
                                (exact_hours, 100.0, slot.id)
                            )
                            slot.invalidate_recordset(['allocated_hours', 'allocated_percentage'])
        return res

    @api.model
    def get_gantt_data(self, *args, **kwargs):
        result = super().get_gantt_data(*args, **kwargs)
        if isinstance(result, dict) and 'working_periods' in result:
            # 🌟 Odoo JS bypass: Give the UI an infinite working period so it stops chopping the Total row math!
            for res_id in result['working_periods'].keys():
                result['working_periods'][res_id] = [
                    ["1970-01-01 00:00:00", "2099-12-31 23:59:59"]
                ]
        return result




