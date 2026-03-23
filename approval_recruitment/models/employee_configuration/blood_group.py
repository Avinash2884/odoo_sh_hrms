from odoo import models, fields

class BloodGroup(models.Model):
    _name = 'blood.group'
    _description = 'Blood Group'

    name = fields.Char(string="Name", required=True)