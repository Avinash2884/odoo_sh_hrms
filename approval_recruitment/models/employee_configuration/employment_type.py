from odoo import models, fields

class EmploymentType(models.Model):
    _name = 'employment.type'
    _description = 'Employment Type'

    name = fields.Char(string="Name")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )