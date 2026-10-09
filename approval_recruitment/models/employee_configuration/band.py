from odoo import models, fields

class Band(models.Model):
    _name = 'band'
    _description = 'Band'

    name = fields.Char(string="Name")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )