from odoo import models, fields

class LsRole(models.Model):
    _name = 'ls.role'
    _description = 'Ls Role'

    name = fields.Char(string="Name", required=True)