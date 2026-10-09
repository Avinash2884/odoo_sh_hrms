from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    geo_restriction_ids = fields.Many2many(
        'geo.restriction',
        string="Allowed Office Locations"
    )