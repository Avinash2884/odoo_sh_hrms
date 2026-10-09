from odoo import models, fields

class SourceOfHire(models.Model):
    _name = 'source.of.hire'
    _description = 'Source Of Hire'

    name = fields.Char(string="Name")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )