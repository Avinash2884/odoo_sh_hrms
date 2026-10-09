from odoo import fields, models


class GeoRestriction(models.Model):
    _name = 'geo.restriction'
    _description = 'Geo Restriction'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name')

    company_latitude = fields.Float(
        string='Company Latitude',
        digits=(16, 6),
        tracking=True,
    )

    company_longitude = fields.Float(
        string='Company Longitude',
        digits=(16, 6),
        tracking=True,
    )

    allowed_distance = fields.Float(
        string='Allowed Distance (Meters)',
        digits=(16, 2),
        tracking=True,
    )