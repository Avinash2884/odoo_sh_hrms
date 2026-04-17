from odoo import fields, models


class GeoRestriction(models.Model):
    _name = 'geo.restriction'
    _description = 'Geo Restriction'

    name = fields.Char(string='Name')

    company_latitude = fields.Float(
        string='Company Latitude',
        digits=(16, 6),
    )

    company_longitude = fields.Float(
        string='Company Longitude',
        digits=(16, 6),
    )

    allowed_distance = fields.Float(
        string='Allowed Distance (Meters)',
        digits=(16, 2)
    )

    employee_ids = fields.Many2many(
        'hr.employee',
        string="Employees"
    )