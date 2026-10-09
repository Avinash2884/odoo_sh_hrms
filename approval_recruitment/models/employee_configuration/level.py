from odoo import models, fields

class Level(models.Model):
    _name = 'level'
    _description = 'Level'

    name = fields.Char(string="Name")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )