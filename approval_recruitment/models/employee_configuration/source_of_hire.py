from odoo import models, fields

class SourceOfHire(models.Model):
    _name = 'source.of.hire'
    _description = 'Source Of Hire'

    name = fields.Char(string="Name", required=True)