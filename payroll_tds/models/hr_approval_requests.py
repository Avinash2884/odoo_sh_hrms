from odoo import models, fields, api


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    ls_employee_code = fields.Char(
        string='Employee ID',
        compute='_compute_employee_details',
        store=True
    )

    ls_department_id = fields.Many2one(
        'hr.department',
        string='Department',
        compute='_compute_employee_details',
        store=True
    )

    # Loan Fields
    loan_type = fields.Selection([
        ('personal', 'Personal Loan'),
        ('car', 'Car Loan'),
        ('home', 'Home Loan'),
        ('education', 'Education Loan'),
        ('medical', 'Medical Loan'),
        ('gold', 'Gold Loan'),
        ('business', 'Business Loan'),
    ], string="Loan Types")

    loan_amount = fields.Monetary(
        string="Loan Amount",
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id
    )

    repayment_period = fields.Integer(
        string="Repayment Period (Months)"
    )
   # Date Store
    approved_date = fields.Datetime(
        string="Approved On",
        readonly=True,
        copy=False
    )
    category_id = fields.Many2one('approval.category', string="Category", required=True)
    has_loan_type = fields.Selection(related="category_id.has_loan_type")
    has_loan_amount = fields.Selection(related="category_id.has_loan_amount")
    has_repayment_period = fields.Selection(related="category_id.has_repayment_period")

    @api.depends('request_owner_id')
    def _compute_employee_details(self):
        for rec in self:
            rec.ls_employee_code = False
            rec.ls_department_id = False

            if rec.request_owner_id:
                employee = self.env['hr.employee'].search([
                    ('user_id', '=', rec.request_owner_id.id)
                ], limit=1)

                if employee:
                    rec.ls_employee_code = employee.ls_employee_id
                    rec.ls_department_id = employee.department_id.id

    def action_approve(self, approver=None):

        res = super().action_approve(approver=approver)

        for rec in self:

            rec.approved_date = fields.Datetime.now()

            employee = self.env['hr.employee'].search([
                ('user_id', '=', rec.request_owner_id.id)
            ], limit=1)

            if employee:
                employee.write({
                    'loan_amount': rec.loan_amount or 0.0,
                    'loan_months': rec.repayment_period or 0,
                })

        return res