from odoo import models, fields

class Vertical(models.Model):
    _name = 'vertical'
    _description = 'Vertical'

    name = fields.Char(string="Name", required=True)