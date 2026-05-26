from odoo import models, fields

class ParentAccount(models.Model):
    _name = 'parent.account'
    _description = 'Parent Account'

    name = fields.Char(string="Name")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )