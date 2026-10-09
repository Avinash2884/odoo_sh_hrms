from odoo import models, fields

class Designation(models.Model):
    _name = 'designation'
    _description = 'Designation'

    name = fields.Char(string="Name")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )