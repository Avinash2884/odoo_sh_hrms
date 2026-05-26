from odoo import models, fields

class AccountOfficeName(models.Model):
    _name = 'account.office.name'
    _description = 'Account Office Name'

    name = fields.Char(string="Name")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )
