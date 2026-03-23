from odoo import models, fields

class LsAccountType(models.Model):
    _name = 'ls.account.type'
    _description = 'Account Type'

    name = fields.Char(string="Name", required=True)