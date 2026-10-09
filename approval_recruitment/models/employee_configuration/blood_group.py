from odoo import models, fields

class BloodGroup(models.Model):
    _name = 'blood.group'
    _description = 'Blood Group'

    name = fields.Char(string="Name")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )