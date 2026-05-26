from odoo import models, fields, api, _

class ItemName(models.Model):
    _name = 'item.name'
    _description = 'Item Name'
    _copy = True
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Item Name",required=True)
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )