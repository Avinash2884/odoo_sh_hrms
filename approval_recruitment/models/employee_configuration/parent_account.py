from odoo import models, fields

class ParentAccount(models.Model):
    _name = 'parent.account'
    _description = 'Parent Account'

    name = fields.Char(string="Name", required=True)