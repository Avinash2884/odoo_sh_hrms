from odoo import models, fields

CATEGORY_SELECTION = [
    ('required', 'Required'),
    ('optional', 'Optional'),
    ('no', 'None')
]


class ApprovalCategoryLoan(models.Model):
    _inherit = 'approval.category'

    # Loan Type
    has_loan_type = fields.Selection(
        CATEGORY_SELECTION,
        string="Loan Type",
        default="no",
        required=True
    )

    # Loan Amount
    has_loan_amount = fields.Selection(
        CATEGORY_SELECTION,
        string="Loan Amount",
        default="no",
        required=True
    )

    # Repayment Period
    has_repayment_period = fields.Selection(
        CATEGORY_SELECTION,
        string="Repayment Period",
        default="no",
        required=True
    )