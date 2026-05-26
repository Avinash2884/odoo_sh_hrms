from odoo import models, fields

class EntityName(models.Model):
    _name = 'entity.name'
    _description = 'Entity Name'

    name = fields.Char(string="Name")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )