from odoo import models, fields

class Function(models.Model):
    _name = 'function'
    _description = 'Function'

    name = fields.Char(string="Name")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )