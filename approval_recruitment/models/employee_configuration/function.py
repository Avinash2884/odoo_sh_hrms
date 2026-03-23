from odoo import models, fields

class Function(models.Model):
    _name = 'function'
    _description = 'Function'

    name = fields.Char(string="Name", required=True)