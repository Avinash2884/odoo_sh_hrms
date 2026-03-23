from odoo import models, fields

class AccountOfficeName(models.Model):
    _name = 'account.office.name'
    _description = 'Account Office Name'

    name = fields.Char(string="Name", required=True)