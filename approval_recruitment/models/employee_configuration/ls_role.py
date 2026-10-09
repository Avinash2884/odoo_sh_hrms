from odoo import models, fields

class LsRole(models.Model):
    _name = 'ls.role'
    _description = 'Ls Role'

    name = fields.Char(string="Name")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )