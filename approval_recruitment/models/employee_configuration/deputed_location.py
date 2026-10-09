from odoo import models, fields

class DeputedLocation(models.Model):
    _name = 'deputed.location'
    _description = 'Deputed Location'

    name = fields.Char(string="Name")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )