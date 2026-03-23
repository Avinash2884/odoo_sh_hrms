from odoo import fields, models, api


class GeoRestriction(models.Model):
    _name = 'geo.restriction'

    company_latitude = fields.Float(string='Company Latitude', digits=(16, 6),
                                    help='Set Company Latitude here')
    # company_longitude = fields.Float(string='Company Longitude', digits=(16, 6),
    #                                  help='Set Company Longitude here')
    # allowed_distance = fields.Float(
    #     string='Allowed Distance (M)', digits=(16, 0),
    #     help='Set the allowed distance for check-in or check-out in kilometers. Example: 2.5 for 2.5 kilometers.'
    # )