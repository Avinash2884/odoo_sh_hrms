from odoo import models, fields

class BaseLocation(models.Model):
    _name = 'base.location'
    _description = 'Base Location'

    name = fields.Char(string="Name", required=True)