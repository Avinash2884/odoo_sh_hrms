from odoo import models, fields

class EmploymentType(models.Model):
    _name = 'employment.type'
    _description = 'Employment Type'

    name = fields.Char(string="Name", required=True)