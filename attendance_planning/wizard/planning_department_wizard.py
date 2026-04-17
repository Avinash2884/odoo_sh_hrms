# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import pytz

class PlanningWizardLine(models.TransientModel):
    _name = 'planning.wizard.line'
    _description = 'Planning Wizard Line'

    wizard_id = fields.Many2one('planning.department.wizard', string='Wizard')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    calendar_id = fields.Many2one(
        'resource.calendar',
        string='Shift Template',
        domain=[('name', 'ilike', 'shift')]
    )


class PlanningDepartmentWizard(models.TransientModel):
    _name = 'planning.department.wizard'
    _description = 'Mass Schedule by Department'

    department_id = fields.Many2one('hr.department', string='Department', required=True)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    line_ids = fields.One2many('planning.wizard.line', 'wizard_id', string='Employee Shifts')

    @api.onchange('department_id')
    def _onchange_department_id(self):
        self.line_ids = [(5, 0, 0)]
        if self.department_id:
            employees = self.env['hr.employee'].search(
                [('department_id', '=', self.department_id.id)]
            )
            self.line_ids = [(0, 0, {'employee_id': emp.id}) for emp in employees]

    def action_generate_shifts(self):
        print("\n" + "="*50)
        print(f"🚀 [WIZARD START] Generating for {self.department_id.name}")
        print(f"📅 Range: {self.start_date} to {self.end_date}")
        print("="*50)

        if not self.line_ids:
            raise UserError("The employee list is empty!")

        slots_to_create = []

        for line in self.line_ids:
            if not line.calendar_id:
                raise UserError(f"Select a Shift Template for {line.employee_id.name}!")
            if not line.employee_id.resource_id:
                raise UserError(f"{line.employee_id.name} has no Resource attached!")

            tz_name = line.calendar_id.tz or self.env.user.tz or 'UTC'
            local_tz = pytz.timezone(tz_name)

            print(f"\n👤 Processing Employee: {line.employee_id.name} | TZ: {tz_name}")

            start_date = fields.Date.from_string(str(self.start_date))
            end_date = fields.Date.from_string(str(self.end_date))
            current_date = start_date

            while current_date <= end_date:
                dayofweek = str(current_date.weekday())

                # Get work lines only — skip lunch/break
                work_lines = line.calendar_id.attendance_ids.filtered(
                    lambda a, d=dayofweek: a.dayofweek == d and a.day_period != 'lunch'
                )

                if work_lines:
                    start_hour = min(work_lines.mapped('hour_from'))
                    end_hour = max(work_lines.mapped('hour_to'))
                    exact_hours = sum(att.hour_to - att.hour_from for att in work_lines)

                    print(f"   ✅ {current_date} (Day {dayofweek}): {exact_hours} Hours Calculated")

                    midnight = datetime(
                        current_date.year, current_date.month, current_date.day, 0, 0, 0
                    )
                    start_utc = local_tz.localize(
                        midnight + timedelta(hours=start_hour)
                    ).astimezone(pytz.utc).replace(tzinfo=None)

                    end_utc = local_tz.localize(
                        midnight + timedelta(hours=end_hour)
                    ).astimezone(pytz.utc).replace(tzinfo=None)

                    slots_to_create.append({
                        'resource_id': line.employee_id.resource_id.id,
                        'employee_id': line.employee_id.id,
                        'calendar_id': line.calendar_id.id,
                        'start_datetime': start_utc,
                        'end_datetime': end_utc,
                        'allocated_hours': exact_hours,
                        'allocated_percentage': 100.0,
                        'state': 'draft',
                    })
                else:
                    print(f"   ⏭️ {current_date} (Day {dayofweek}): Skipped (No work lines)")

                current_date += timedelta(days=1)

        if not slots_to_create:
            raise UserError("No working days found in the selected date range!")

        created = self.env['planning.slot'].create(slots_to_create)
        print(f"\n✅ [WIZARD SUCCESS] Inserted {len(created)} slots into Database")
        print("="*50 + "\n")

        return {'type': 'ir.actions.client', 'tag': 'reload'}











# # -*- coding: utf-8 -*-
# from odoo import api, fields, models
# from odoo.exceptions import UserError
# from datetime import datetime, timedelta
# import pytz
#
#
# class PlanningWizardLine(models.TransientModel):
#     _name = 'planning.wizard.line'
#     _description = 'Planning Wizard Line'
#
#     wizard_id = fields.Many2one('planning.department.wizard', string='Wizard')
#     employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
#     calendar_id = fields.Many2one(
#         'resource.calendar',
#         string='Shift Template',
#         domain=[('name', 'ilike', 'shift')]
#     )
#
#
# class PlanningDepartmentWizard(models.TransientModel):
#     _name = 'planning.department.wizard'
#     _description = 'Mass Schedule by Department'
#
#     department_id = fields.Many2one('hr.department', string='Department', required=True)
#
#     # 🌟 CHANGED to simple Dates! No more confusing clocks for the managers.
#     start_date = fields.Date(string='Start Date', required=True)
#     end_date = fields.Date(string='End Date', required=True)
#
#     line_ids = fields.One2many('planning.wizard.line', 'wizard_id', string='Employee Shifts')
#
#     @api.onchange('department_id')
#     def _onchange_department_id(self):
#         self.line_ids = [(5, 0, 0)]
#         if self.department_id:
#             employees = self.env['hr.employee'].search([('department_id', '=', self.department_id.id)])
#             lines = [(0, 0, {'employee_id': emp.id}) for emp in employees]
#             self.line_ids = lines
#
#     def action_generate_shifts(self):
#         if not self.line_ids:
#             raise UserError("The employee list is empty!")
#
#         slots_to_create = []
#         created_count = 0
#
#         for line in self.line_ids:
#             if not line.calendar_id:
#                 raise UserError(f"Select a Shift Template for {line.employee_id.name}!")
#             if not line.employee_id.resource_id:
#                 raise UserError(f"{line.employee_id.name} does not have a 'Resource' attached!")
#
#             # Prepare to translate the timezones perfectly
#             tz_name = line.calendar_id.tz or self.env.user.tz or 'UTC'
#             local_tz = pytz.timezone(tz_name)
#
#             # 🌟 THE MAGIC LOOP: Goes through every single day one by one
#             current_date = self.start_date
#             while current_date <= self.end_date:
#                 dayofweek = str(current_date.weekday())
#
#                 # Check if the template has working hours for this specific day (skips weekends automatically!)
#                 attendances = line.calendar_id.attendance_ids.filtered(lambda a: a.dayofweek == dayofweek)
#
#                 if attendances:
#                     # Extract the exact times from the template (e.g. 14.0 for 2:00 PM)
#                     start_hour = min(attendances.mapped('hour_from'))
#                     end_hour = max(attendances.mapped('hour_to'))
#
#                     # Create the exact start and end datetimes
#                     start_time_local = local_tz.localize(
#                         datetime.combine(current_date, datetime.min.time()) + timedelta(hours=start_hour))
#                     end_time_local = local_tz.localize(
#                         datetime.combine(current_date, datetime.min.time()) + timedelta(hours=end_hour))
#
#                     # Convert to UTC for the Odoo database
#                     start_time_utc = start_time_local.astimezone(pytz.utc).replace(tzinfo=None)
#                     end_time_utc = end_time_local.astimezone(pytz.utc).replace(tzinfo=None)
#
#                     # Queue up the specific daily shift!
#                     slots_to_create.append({
#                         'resource_id': line.employee_id.resource_id.id,
#                         'employee_id': line.employee_id.id,
#                         'calendar_id': line.calendar_id.id,
#                         'start_datetime': start_time_utc,
#                         'end_datetime': end_time_utc,
#                         'state': 'draft',
#                     })
#                     created_count += 1
#
#                 # Move to the next day in the loop
#                 current_date += timedelta(days=1)
#
#         if slots_to_create:
#             self.env['planning.slot'].create(slots_to_create)
#
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': 'Success!',
#                 'message': f'Successfully generated {created_count} individual daily shifts!',
#                 'type': 'success',
#                 'sticky': False,
#                 'next': {'type': 'ir.actions.client', 'tag': 'reload'},
#             }
#         }
#
