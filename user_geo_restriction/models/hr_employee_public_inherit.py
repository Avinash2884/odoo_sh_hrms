from odoo import models, fields, api, _

class HrEmployeeInherit(models.Model):
    _inherit = 'hr.employee.public'
    _description = 'HR Employee Public'

    geo_restriction_ids = fields.Many2many(
        related='employee_id.geo_restriction_ids',
        string="Allowed Office Locations",
        readonly=True,
    )
