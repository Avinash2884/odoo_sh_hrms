from odoo import models, fields

class BaseLocation(models.Model):
    _name = 'base.location'
    _description = 'Base Location'

    name = fields.Char(string="Name")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )