from odoo import models, fields

class Designation(models.Model):
    _name = 'designation'
    _description = 'Designation'

    name = fields.Char(string="Name", required=True)