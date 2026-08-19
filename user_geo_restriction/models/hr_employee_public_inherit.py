from odoo import models, fields, api, _

class HrEmployeeInherit(models.Model):
    _inherit = 'hr.employee.public'
    _description = 'HR Employee Public'

    geo_restriction_ids = fields.Many2many(
        related='employee_id.geo_restriction_ids',
        string="Allowed Office Locations",
        readonly=True,
    )

    is_my_employees = fields.Boolean(
        compute="_compute_is_my_employees",
    )

    @api.depends("user_id")
    def _compute_is_my_employees(self):
        current_user = self.env.user

        for employee in self:
            employee.is_my_employees = employee.user_id == current_user
