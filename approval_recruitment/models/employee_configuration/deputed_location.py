from odoo import models, fields

class DeputedLocation(models.Model):
    _name = 'deputed.location'
    _description = 'Deputed Location'

    name = fields.Char(string="Name", required=True)