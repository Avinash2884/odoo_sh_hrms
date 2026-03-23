from odoo import models, fields, api, _

class PayrollClearance(models.Model):
    _name = 'payroll.clearance'
    _description = 'Payroll Clearance'

    name = fields.Many2one('payroll.component',string="Payroll Component",required=True)
    applicable = fields.Selection([
        ('yes','Yes'),
        ('no','No'),
    ],string="Applicable")
    amount = fields.Float(string="Amount")
    dues_cleared = fields.Selection([
        ('cleared', 'Cleared'),
        ('pending', 'Pending'),
        ('na', 'N/A'),
    ], string="Dues Cleared")
    remarks = fields.Text(string="Remarks")

    payroll_state = fields.Selection([
        ('proceed', 'Proceed'),
    ], tracking=True)

    initiate_separation_id = fields.Many2one('initiate.separation',string="Initiate Separation")
