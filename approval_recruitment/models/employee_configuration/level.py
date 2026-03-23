from odoo import models, fields

class Level(models.Model):
    _name = 'level'
    _description = 'Level'

    name = fields.Char(string="Name", required=True)