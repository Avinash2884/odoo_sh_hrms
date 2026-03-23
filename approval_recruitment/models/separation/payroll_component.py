from odoo import models, fields, api, _

class PayrollComponent(models.Model):
    _name = 'payroll.component'
    _description = 'Payroll Component'
    _copy = True

    name = fields.Char(string="Payroll Component",required=True)