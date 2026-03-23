from odoo import models, fields

class Region(models.Model):
    _name = 'region'
    _description = 'Region'

    name = fields.Char(string="Name", required=True)