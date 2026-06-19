from odoo import models, fields, api


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    leave_type_name = fields.Char(
        string="Time Off Request Type",
        compute="_compute_leave_type_name"
    )

    @api.depends('employee_id')
    def _compute_leave_type_name(self):
        for rec in self:
            rec.leave_type_name = False

            leave = self.env['hr.leave'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', 'in', ['validate', 'validate1']),
            ], limit=1)

            if leave:
                rec.leave_type_name = leave.holiday_status_id.name