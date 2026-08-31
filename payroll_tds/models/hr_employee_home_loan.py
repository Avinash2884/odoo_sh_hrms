from odoo import models, fields


class HrEmployeeHomeLoan(models.Model):
    _name = 'hr.employee.home.loan'
    _description = 'Employee Home Loan Details'

    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        required=True,
        ondelete='cascade'
    )

    principal_paid = fields.Monetary(
        string="Principal Paid on Home Loan",
        currency_field='currency_id'
    )

    interest_paid = fields.Monetary(
        string="Interest Paid on Home Loan (Section 22)",
        currency_field='currency_id'
    )

    lender_name = fields.Char(
        string="Name of the Lender"
    )

    lender_pan = fields.Char(
        string="Lender PAN"
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='employee_id.currency_id',
        string="Currency",
        readonly=True
    )