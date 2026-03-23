from odoo import models, fields

class Band(models.Model):
    _name = 'band'
    _description = 'Band'

    name = fields.Char(string="Name", required=True)