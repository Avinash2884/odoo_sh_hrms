from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    regularization = fields.Boolean(string="Regularization",
                                    help="Regularized attendance")

    @api.model
    def create(self, vals):
        # Normalize vals into a list of dicts
        vals_list = vals if isinstance(vals, list) else [vals]

        for vals_item in vals_list:
            employee = self.env['hr.employee'].browse(vals_item.get('employee_id'))

            check_in_val = vals_item.get('check_in') or fields.Datetime.now()
            if isinstance(check_in_val, str):
                check_in_val = fields.Datetime.from_string(check_in_val)

            day_start = check_in_val.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = check_in_val.replace(hour=23, minute=59, second=59, microsecond=0)

            # 🔹 Check if this employee has a planning slot covering that day
            has_planning_that_day = self.env['planning.slot'].search_count([
                ('employee_id', '=', employee.id),
                ('start_datetime', '<=', day_end),
                ('end_datetime', '>=', day_start),
            ]) > 0

            if has_planning_that_day:
                # Validate the check-in time against that day's planning slot
                planning = self.env['planning.slot'].search([
                    ('employee_id', '=', employee.id),
                    ('start_datetime', '<=', check_in_val),
                    ('end_datetime', '>=', check_in_val)
                ], limit=1)

                if not planning:
                    raise ValidationError("❌ Check-in not allowed outside your assigned shift time!")

        return super(HrAttendance, self).create(vals_list)