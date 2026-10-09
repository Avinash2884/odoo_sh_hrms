from odoo import models, fields, api


# =============================================================
# SECTION 123 (80C) INVESTMENT
# =============================================================

class HrEmployeeInvestment(models.Model):
    _name = 'hr.employee.investment'
    _description = 'Employee Section 123 (80C) Investment'
    _order = 'id asc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )

    investment_type = fields.Selection(
        [
            (
                'life_insurance_premium',
                'Life Insurance Premium'
            ),
            (
                'employee_provident_fund',
                'Employee Provident Fund'
            ),
            (
                'ulip',
                'Unit - Linked Insurance Plan'
            ),
            (
                'national_savings_certificates',
                'National Savings Certificates'
            ),
            (
                'elss',
                'ELSS Tax Saving Mutual Fund'
            ),
            (
                'children_tution_fees',
                'Children Tution Fees'
            ),
            (
                'sukanya_samiddhi',
                'Sukanya Samiddhi Deposit Scheme'
            ),
            (
                'five_year_fixed_deposit',
                '5 Year Fixed Deposit in Scheduled Banks'
            ),
            (
                'post_office_term_deposit',
                'Term Deposit in Post Office'
            ),
            (
                'senior_citizen_savings_scheme',
                'Senior Citizen Savings Scheme'
            ),
            (
                'nabard_rural_bonds',
                'NABARD Rural Bonds'
            ),
            (
                'infrastructure_bonds',
                'Infrastructure Bonds'
            ),
            (
                'stamp_duty_registration',
                'Stamp duty & registration fee on buying house property'
            ),
            (
                'interest_nsc',
                'Interest on National Savings Certificates'
            ),
            (
                'home_loan_principal_repayment',
                'Principal Repayment of Home Loan'
            ),
        ],
        string='Investment Type',
        required=True,
    )

    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='employee_id.currency_id',
        store=True,
        readonly=True,
    )


# =============================================================
# SECTION 123 (80CCC) INVESTMENT
# =============================================================

class HrEmployeeInvestment80CCC(models.Model):
    _name = 'hr.employee.investment.80ccc'
    _description = 'Employee Section 123 (80CCC) Investment'
    _order = 'id asc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )

    investment_type = fields.Selection(
        [
            (
                'lic_annuity_plan',
                'Contribution to annuity plan of LIC'
            ),
        ],
        string='Investment Type',
        required=True,
    )

    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='employee_id.currency_id',
        store=True,
        readonly=True,
    )


# =============================================================
# SECTION 124 (1) (80CCD (1)) INVESTMENT
# =============================================================

class HrEmployeeInvestment80CCD1(models.Model):
    _name = 'hr.employee.investment.80ccd1'
    _description = 'Employee Section 124 (1) (80CCD (1)) Investment'
    _order = 'id asc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )

    investment_type = fields.Selection(
        [
            (
                'national_pension_scheme',
                'National Pension Scheme'
            ),
        ],
        string='Investment Type',
        required=True,
    )

    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='employee_id.currency_id',
        store=True,
        readonly=True,
    )


# =============================================================
# SECTION 124 (1B) (80CCD (1B)) INVESTMENT
# =============================================================

class HrEmployeeInvestment80CCD1B(models.Model):
    _name = 'hr.employee.investment.80ccd1b'
    _description = 'Employee Section 124 (1B) (80CCD (1B)) Investment'
    _order = 'id asc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )

    investment_type = fields.Selection(
        [
            (
                'national_pension_scheme',
                'National Pension Scheme'
            ),
        ],
        string='Investment Type',
        required=True,
    )

    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
    )

    limit_amount = fields.Monetary(
        string='Additional Exemption Limit',
        currency_field='currency_id',
        default=50000,
        readonly=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='employee_id.currency_id',
        store=True,
        readonly=True,
    )


# =============================================================
# SECTION 127 (80DD) INVESTMENT
# =============================================================

class HrEmployeeInvestment80DD(models.Model):
    _name = 'hr.employee.investment.80dd'
    _description = 'Employee Section 127 (80DD) Investment'
    _order = 'id asc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )

    investment_type = fields.Selection(
        [
            (
                'dependent_disability',
                'Treatment of dependant with disability'
            ),
            (
                'dependent_severe_disability',
                'Treatment of dependant with severe disability'
            ),
        ],
        string='Investment Type',
        required=True,
    )

    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
    )

    limit_amount = fields.Monetary(
        string='Limit',
        currency_field='currency_id',
        compute='_compute_limit_amount',
        store=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='employee_id.currency_id',
        store=True,
        readonly=True,
    )

    @api.depends('investment_type')
    def _compute_limit_amount(self):
        for record in self:
            if record.investment_type == 'dependent_disability':
                record.limit_amount = 75000
            elif record.investment_type == 'dependent_severe_disability':
                record.limit_amount = 125000
            else:
                record.limit_amount = 0


# =============================================================
# SECTION 128 (80DDB) INVESTMENT
# =============================================================

class HrEmployeeInvestment80DDB(models.Model):
    _name = 'hr.employee.investment.80ddb'
    _description = 'Employee Section 128 (80DDB) Investment'
    _order = 'id asc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )

    investment_type = fields.Selection(
        [
            (
                'medical_expenditure_self_dependent',
                'Medical expenditure for self or dependant'
            ),
            (
                'medical_expenditure_senior_citizen',
                'Medical Expenditure for self or dependent for senior citizen'
            ),
            (
                'medical_expenditure_very_senior_citizen',
                'Medical Expenditure for self or dependent for very senior citizen'
            ),
        ],
        string='Investment Type',
        required=True,
    )

    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
    )

    limit_amount = fields.Monetary(
        string='Limit',
        currency_field='currency_id',
        compute='_compute_limit_amount',
        store=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='employee_id.currency_id',
        store=True,
        readonly=True,
    )

    @api.depends('investment_type')
    def _compute_limit_amount(self):
        for record in self:
            if record.investment_type == 'medical_expenditure_self_dependent':
                record.limit_amount = 40000
            elif record.investment_type == 'medical_expenditure_senior_citizen':
                record.limit_amount = 100000
            elif record.investment_type == 'medical_expenditure_very_senior_citizen':
                record.limit_amount = 100000
            else:
                record.limit_amount = 0


# =============================================================
# SECTION 129 (80E) INVESTMENT
# =============================================================

class HrEmployeeInvestment80E(models.Model):
    _name = 'hr.employee.investment.80e'
    _description = 'Employee Section 129 (80E) Investment'
    _order = 'id asc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )

    investment_type = fields.Selection(
        [
            (
                'education_loan_interest',
                'Interest Paid on Education Loan'
            ),
        ],
        string='Investment Type',
        required=True,
    )

    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='employee_id.currency_id',
        store=True,
        readonly=True,
    )


# =============================================================
# SECTION 130 (80EE) INVESTMENT
# =============================================================

class HrEmployeeInvestment80EE(models.Model):
    _name = 'hr.employee.investment.80ee'
    _description = 'Employee Section 130 (80EE) Investment'
    _order = 'id asc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )

    investment_type = fields.Selection(
        [
            (
                'additional_housing_loan_interest_2016_2017',
                'Additional interest on housing loan borrowed between 1 Apr 2016 and 31 Mar 2017'
            ),
        ],
        string='Investment Type',
        required=True,
    )

    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
    )

    limit_amount = fields.Monetary(
        string='Limit',
        currency_field='currency_id',
        default=50000,
        readonly=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='employee_id.currency_id',
        store=True,
        readonly=True,
    )


# =============================================================
# SECTION 131 (80EEA) INVESTMENT
# =============================================================

class HrEmployeeInvestment80EEA(models.Model):
    _name = 'hr.employee.investment.80eea'
    _description = 'Employee Section 131 (80EEA) Investment'
    _order = 'id asc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )

    investment_type = fields.Selection(
        [
            (
                'additional_housing_loan_interest_2019_2022',
                'Additional interest on housing loan borrowed between 1 Apr 2019 and 31 Mar 2022'
            ),
        ],
        string='Investment Type',
        required=True,
    )

    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
    )

    limit_amount = fields.Monetary(
        string='Limit',
        currency_field='currency_id',
        default=150000,
        readonly=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='employee_id.currency_id',
        store=True,
        readonly=True,
    )


# =============================================================
# SECTION 123 (80EEB) INVESTMENT
# =============================================================

class HrEmployeeInvestment80EEB(models.Model):
    _name = 'hr.employee.investment.80eeb'
    _description = 'Employee Section 123 (80EEB) Investment'
    _order = 'id asc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )

    investment_type = fields.Selection(
        [
            (
                'electric_vehicle_loan_interest',
                'Interest on electric vehicle loan borrowed between 1 Apr 2019 and 31 Mar 2023'
            ),
        ],
        string='Investment Type',
        required=True,
    )

    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
    )

    limit_amount = fields.Monetary(
        string='Limit',
        currency_field='currency_id',
        default=150000,
        readonly=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='employee_id.currency_id',
        store=True,
        readonly=True,
    )


# =============================================================
# SECTION 133 (80G) INVESTMENT
# =============================================================

class HrEmployeeInvestment80G(models.Model):
    _name = 'hr.employee.investment.80g'
    _description = 'Employee Section 133 (80G) Investment'
    _order = 'id asc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )

    investment_type = fields.Selection(
        [
            (
                'donation_100_exemption',
                'Donation eligible for 100% Exemption'
            ),
            (
                'donation_50_exemption',
                'Donation eligible for 50% Exemption'
            ),
        ],
        string='Investment Type',
        required=True,
    )

    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='employee_id.currency_id',
        store=True,
        readonly=True,
    )


# =============================================================
# SECTION 134 (80GG) INVESTMENT
# =============================================================

class HrEmployeeInvestment80GG(models.Model):
    _name = 'hr.employee.investment.80gg'
    _description = 'Employee Section 134 (80GG) Investment'
    _order = 'id asc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )

    investment_type = fields.Selection(
        [
            (
                'house_rent_paid',
                'House Rent Paid'
            ),
        ],
        string='Investment Type',
        required=True,
    )

    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
    )

    limit_amount = fields.Monetary(
        string='Limit',
        currency_field='currency_id',
        default=60000,
        readonly=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='employee_id.currency_id',
        store=True,
        readonly=True,
    )


# =============================================================
# SECTION (80GGC) INVESTMENT
# =============================================================

class HrEmployeeInvestment80GGC(models.Model):
    _name = 'hr.employee.investment.80ggc'
    _description = 'Employee Section (80GGC) Investment'
    _order = 'id asc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )

    investment_type = fields.Selection(
        [
            (
                'political_party_donation',
                'Donation for Political Party'
            ),
        ],
        string='Investment Type',
        required=True,
    )

    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='employee_id.currency_id',
        store=True,
        readonly=True,
    )


# =============================================================
# SECTION 153 (80TTA) INVESTMENT
# =============================================================

class HrEmployeeInvestment80TTA(models.Model):
    _name = 'hr.employee.investment.80tta'
    _description = 'Employee Section 153 (80TTA) Investment'
    _order = 'id asc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )

    investment_type = fields.Selection(
        [
            (
                'savings_account_interest',
                'Interest from Savings Account'
            ),
        ],
        string='Investment Type',
        required=True,
    )

    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
    )

    limit_amount = fields.Monetary(
        string='Limit',
        currency_field='currency_id',
        default=10000,
        readonly=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='employee_id.currency_id',
        store=True,
        readonly=True,
    )


# =============================================================
# SECTION 154 (80U) INVESTMENT
# =============================================================

class HrEmployeeInvestment80U(models.Model):
    _name = 'hr.employee.investment.80u'
    _description = 'Employee Section 154 (80U) Investment'
    _order = 'id asc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )

    investment_type = fields.Selection(
        [
            (
                'permanent_physical_disability',
                'Permanent Physical Disability (Self)'
            ),
            (
                'permanent_severe_physical_disability',
                'Permanent Severe Physical Disability (Self)'
            ),
        ],
        string='Investment Type',
        required=True,
    )

    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
    )

    limit_amount = fields.Monetary(
        string='Limit',
        currency_field='currency_id',
        compute='_compute_limit_amount',
        store=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='employee_id.currency_id',
        store=True,
        readonly=True,
    )

    @api.depends('investment_type')
    def _compute_limit_amount(self):
        for record in self:
            if record.investment_type == 'permanent_physical_disability':
                record.limit_amount = 75000
            elif record.investment_type == 'permanent_severe_physical_disability':
                record.limit_amount = 125000
            else:
                record.limit_amount = 0


# =============================================================
# OTHER ALLOWANCE DETAILS
# =============================================================

class HrEmployeeOtherAllowance(models.Model):
    _name = 'hr.employee.other.allowance'
    _description = 'Employee Other Allowance Details'
    _order = 'id asc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )

    allowance_type = fields.Selection(
        [
            (
                'conveyance_allowance',
                'Conveyance Allowance'
            ),
        ],
        string='Allowance Type',
        required=True,
    )

    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='employee_id.currency_id',
        store=True,
        readonly=True,
    )


# =============================================================
# EMPLOYEE - ALL INVESTMENT FIELDS
# =============================================================

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    investment_80c_ids = fields.One2many(
        'hr.employee.investment',
        'employee_id',
        string='Section 123 (80C) Investments',
        copy=False,
    )

    investment_80ccc_ids = fields.One2many(
        'hr.employee.investment.80ccc',
        'employee_id',
        string='Section 123 (80CCC) Investments',
        copy=False,
    )

    investment_80ccd1_ids = fields.One2many(
        'hr.employee.investment.80ccd1',
        'employee_id',
        string='Section 124 (1) (80CCD (1)) Investments',
        copy=False,
    )

    investment_80ccd1b_ids = fields.One2many(
        'hr.employee.investment.80ccd1b',
        'employee_id',
        string='Section 124 (1B) (80CCD (1B)) Investments',
        copy=False,
    )

    investment_80dd_ids = fields.One2many(
        'hr.employee.investment.80dd',
        'employee_id',
        string='Section 127 (80DD) Investments',
        copy=False,
    )

    investment_80ddb_ids = fields.One2many(
        'hr.employee.investment.80ddb',
        'employee_id',
        string='Section 128 (80DDB) Investments',
        copy=False,
    )

    investment_80e_ids = fields.One2many(
        'hr.employee.investment.80e',
        'employee_id',
        string='Section 129 (80E) Investments',
        copy=False,
    )

    investment_80ee_ids = fields.One2many(
        'hr.employee.investment.80ee',
        'employee_id',
        string='Section 130 (80EE) Investments',
        copy=False,
    )

    investment_80eea_ids = fields.One2many(
        'hr.employee.investment.80eea',
        'employee_id',
        string='Section 131 (80EEA) Investments',
        copy=False,
    )

    investment_80eeb_ids = fields.One2many(
        'hr.employee.investment.80eeb',
        'employee_id',
        string='Section 123 (80EEB) Investments',
        copy=False,
    )

    investment_80g_ids = fields.One2many(
        'hr.employee.investment.80g',
        'employee_id',
        string='Section 133 (80G) Investments',
        copy=False,
    )

    investment_80gg_ids = fields.One2many(
        'hr.employee.investment.80gg',
        'employee_id',
        string='Section 134 (80GG) Investments',
        copy=False,
    )

    investment_80ggc_ids = fields.One2many(
        'hr.employee.investment.80ggc',
        'employee_id',
        string='Section (80GGC) Investments',
        copy=False,
    )

    investment_80tta_ids = fields.One2many(
        'hr.employee.investment.80tta',
        'employee_id',
        string='Section 153 (80TTA) Investments',
        copy=False,
    )

    investment_80u_ids = fields.One2many(
        'hr.employee.investment.80u',
        'employee_id',
        string='Section 154 (80U) Investments',
        copy=False,
    )

    other_allowance_ids = fields.One2many(
        'hr.employee.other.allowance',
        'employee_id',
        string='Other Allowance Details',
        copy=False,
    )

    other_income_ids = fields.One2many(
        'hr.employee.other.income',
        'employee_id',
        string='Other Sources of Income',
        copy=False,
    )


# =============================================================
# SECTION 126 (80D) EXEMPTION
# =============================================================

class HrEmployeeInvestment80D(models.Model):
    _name = 'hr.employee.investment.80d'
    _description = 'Employee Section 126 (80D) Exemption'
    _order = 'id asc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )

    investment_type = fields.Selection(
        [
            (
                'medical_policy_self_spouse_children',
                'Medical Insurance Policy for Self, Spouse, Children'
            ),
            (
                'medical_policy_self_spouse_children_senior',
                'Medical Insurance Policy for Self, Spouse, Children for Senior Citizen'
            ),
            (
                'medical_policy_parents',
                'Medical Insurance Policy for Parents'
            ),
            (
                'medical_policy_parents_senior',
                'Medical Insurance Policy for Parents for Senior Citizen'
            ),
            (
                'preventive_health_checkup',
                'Preventive Health Check-up'
            ),
            (
                'preventive_health_checkup_parents',
                'Preventive Health Check-up for Parents'
            ),
            (
                'medical_bills_self_spouse_children_senior',
                'Medical Bills for Self, Spouse, Children for Senior Citizen'
            ),
            (
                'medical_bills_parents_senior',
                'Medical Bills for Parents for Senior Citizen'
            ),
        ],
        string='Exemption Type',
        required=True,
    )

    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
    )

    limit_amount = fields.Monetary(
        string='Limit',
        currency_field='currency_id',
        compute='_compute_limit_amount',
        store=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='employee_id.currency_id',
        store=True,
        readonly=True,
    )

    @api.depends('investment_type')
    def _compute_limit_amount(self):
        for record in self:
            if record.investment_type == 'medical_policy_self_spouse_children':
                record.limit_amount = 25000.0

            elif record.investment_type == 'medical_policy_self_spouse_children_senior':
                record.limit_amount = 50000.0

            elif record.investment_type == 'medical_policy_parents':
                record.limit_amount = 25000.0

            elif record.investment_type == 'medical_policy_parents_senior':
                record.limit_amount = 50000.0

            elif record.investment_type == 'preventive_health_checkup':
                record.limit_amount = 5000.0

            elif record.investment_type == 'preventive_health_checkup_parents':
                record.limit_amount = 5000.0

            elif record.investment_type == 'medical_bills_self_spouse_children_senior':
                record.limit_amount = 50000.0

            elif record.investment_type == 'medical_bills_parents_senior':
                record.limit_amount = 50000.0

            else:
                record.limit_amount = 0.0


# =============================================================
# EMPLOYEE - SECTION 126 (80D)
# =============================================================

class HrEmployeeInvestmentFields(models.Model):
    _inherit = 'hr.employee'

    investment_80d_ids = fields.One2many(
        'hr.employee.investment.80d',
        'employee_id',
        string='Section 126 (80D) Exemptions',
        copy=False,
    )
# =============================================================
# OTHER SOURCES OF INCOME
# =============================================================

class HrEmployeeOtherIncome(models.Model):
    _name = 'hr.employee.other.income'
    _description = 'Employee Other Sources of Income'
    _order = 'id asc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )

    income_type = fields.Selection(
        [
            (
                'other_sources_income',
                'Income from Other Sources'
            ),
            (
                'savings_deposit_interest',
                'Interest Earned from Savings Deposit'
            ),
            (
                'fixed_deposit_interest',
                'Interest Earned from Fixed Deposit'
            ),
            (
                'nsc_interest',
                'Interest Earned from National Savings Certificates'
            ),
        ],
        string='Income Type',
        required=True,
    )

    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='employee_id.currency_id',
        store=True,
        readonly=True,
    )