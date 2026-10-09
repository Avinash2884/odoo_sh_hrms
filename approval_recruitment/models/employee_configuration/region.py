from odoo import models, fields

class Region(models.Model):
    _name = 'region'
    _description = 'Region'

    name = fields.Char(string="Name")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )