from odoo import models, fields

class LsAccountType(models.Model):
    _name = 'ls.account.type'
    _description = 'Account Type'

    name = fields.Char(string="Name")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )