from odoo import models, fields

class EntityName(models.Model):
    _name = 'entity.name'
    _description = 'Entity Name'

    name = fields.Char(string="Name", required=True)