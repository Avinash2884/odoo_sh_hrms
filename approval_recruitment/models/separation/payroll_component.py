from odoo import models, fields, api, _

class PayrollComponent(models.Model):
    _name = 'payroll.component'
    _description = 'Payroll Component'
    _copy = True
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Payroll Component",required=True)
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )