from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError


class HrAttendance(models.Model):
    """Inherited hr_attendance model to add new fields"""
    _inherit = 'hr.attendance'

    regularization = fields.Boolean(string="Regularization",
                                    help="Regularized attendance")

    @api.model
    def create(self, vals):
        # Normalize vals into a list of dicts
        vals_list = vals if isinstance(vals, list) else [vals]

        for vals_item in vals_list:
            employee = self.env['hr.employee'].browse(vals_item.get('employee_id'))
            now = fields.Datetime.now()

            # 🔹 Check if this employee has any planning slots at all
            has_planning = self.env['planning.slot'].search_count([
                ('employee_id', '=', employee.id)
            ]) > 0

            if has_planning:
                # Validate only if employee has planning
                planning = self.env['planning.slot'].search([
                    ('employee_id', '=', employee.id),
                    ('start_datetime', '<=', now),
                    ('end_datetime', '>=', now)
                ], limit=1)

                if not planning:
                    raise ValidationError("❌ Check-in not allowed outside your assigned shift time!")

        return super(HrAttendance, self).create(vals_list)
