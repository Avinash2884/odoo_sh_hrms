from odoo import models, fields


class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    # ==========================================================
    # Leave Allocation Fields
    # ==========================================================

    revision_ids = fields.One2many(
        'employee.salary.revision',
        'employee_id',
        string='Revised Wage Details'
    )

    pl_allocation_year = fields.Integer(
        related='employee_id.pl_allocation_year',
        string="PL Allocation Year",
        readonly=False,
    )

    last_cl_allocation_month = fields.Char(
        related='employee_id.last_cl_allocation_month',
        string="Last CL Allocation Month",
        readonly=False,
    )

    last_sl_allocation_month = fields.Char(
        related='employee_id.last_sl_allocation_month',
        string="Last SL Allocation Month",
        readonly=False,
    )

    bereavement_allocation_year = fields.Integer(
        related='employee_id.bereavement_allocation_year',
        string="Bereavement Allocation Year",
        readonly=False,
    )

    l10n_in_nps_employer_type = fields.Selection(
        selection=[
            ('0', '0'),
            ('5', '5'),
            ('10', '10'),
            ('14', '14'),
        ],
        string="NPS Employer Contribution",
        default='0',
    )

    l10n_in_nps_employer_amount = fields.Monetary(
        string="NPS Employer Amount",
        compute="_compute_l10n_in_nps_employer_amount",
        store=True,
        currency_field='currency_id',
    )

    pran_number = fields.Char(
        string="PRAN Number",
        copy=False,
        help="Enter a valid 12-digit PRAN number.",
    )

    financial_year_incentive = fields.Monetary(
        string="Financial Year Incentive",
        currency_field='currency_id',
        default=0.0,
        copy=False,
    )

    # ==========================================================
    # Tax / TDS Fields
    # ==========================================================

    tax_regime = fields.Selection([
        ('old', 'Old Regime'),
        ('new', 'New Regime'),
    ], string='Tax Regime')

    hra_exemption_amount = fields.Monetary(
        string="HRA Exemption",
        currency_field='currency_id',
        compute="_compute_hra_exemption_amount",
        store=True,
        readonly=True,
    )
    tax_on_employment = fields.Monetary(
        string="Tax on Employment",
        currency_field='currency_id',
        help="Professional Tax / Tax on Employment",
    )
    previous_employment_income = fields.Monetary(
        string="Income After Exemptions",
        currency_field='currency_id',
        help="Taxable Income under Previous Employment - Income After Exemptions",
    )

    previous_employment_professional_tax = fields.Monetary(
        string="Less: Professional Tax",
        currency_field='currency_id',
        help="Professional Tax under Previous Employment",
    )

    entertainment_allowance = fields.Monetary(
        string="Entertainment Allowance",
        currency_field='currency_id',
        help="Entertainment Allowance under Section 19",
    )

    standard_deduction = fields.Monetary(
        related='employee_id.standard_deduction',
        string='Standard Deduction',
        currency_field='currency_id',
        readonly=False,
    )

    section_80c = fields.Monetary(
        related='employee_id.section_80c',
        string='Section 80C',
        currency_field='currency_id',
        readonly=False,
    )
    section_123_80ccc = fields.Monetary(
        string='Section 123 (80CCC)',
        help="Available only under Old Regime"
    )

    section_124_1_80ccd_1 = fields.Monetary(
        string='Section 124 (1) (80CCD (1))',
        help="Available only under Old Regime"
    )

    section_124_1b_80ccd_1b = fields.Monetary(
        string='Section 124(1B) (80CCD(1B))',
        help="Available only under Old Regime"
    )

    section_126_80d = fields.Monetary(
        string='Section 126 (80D)',
        help="Available only under Old Regime"
    )

    section_127_80dd = fields.Monetary(
        string='Section 127 (80DD)',
        help="Available only under Old Regime"
    )

    section_128_80ddb = fields.Monetary(
        string='Section 128(80DDB)',
        help="Available only under Old Regime"
    )

    section_129_80e = fields.Monetary(
        string='Section 129 (80E)',
        help="Available only under Old Regime"
    )

    section_130_80ee = fields.Monetary(
        string='Section 130 (80EE)',
        help="Available only under Old Regime"
    )

    section_131_80eea = fields.Monetary(
        string='Section 131 (80EEA)',
        help="Available only under Old Regime"
    )

    section_132_80eeb = fields.Monetary(
        string='Section 132 (80EEB)',
        help="Available only under Old Regime"
    )

    section_133_80g = fields.Monetary(
        string='Section 133(80G)',
        help="Available only under Old Regime"
    )

    section_134_80gg = fields.Monetary(
        string='Section 134(80GG)',
        help="Available only under Old Regime"
    )

    section_137_80ggc = fields.Monetary(
        string='Section 137 (80GGC)',
        help="Available only under Old Regime"
    )

    section_153_80tta = fields.Monetary(
        string='Section 153(80TTA)',
        help="Available only under Old Regime"
    )

    section_154_80u = fields.Monetary(
        string='Section 154(80U)',
        help="Available only under Old Regime"
    )

    section_80d = fields.Monetary(
        related='employee_id.section_80d',
        string='Section 80D',
        currency_field='currency_id',
        readonly=False,
    )

    section_80g = fields.Monetary(
        related='employee_id.section_80g',
        string='Section 80G',
        currency_field='currency_id',
        readonly=False,
    )

    nps = fields.Monetary(
        related='employee_id.nps',
        string='NPS (80CCD(1B))',
        currency_field='currency_id',
        readonly=False,
    )

    home_loan_interest = fields.Monetary(
        related='employee_id.home_loan_interest',
        string='Home Loan Interest',
        currency_field='currency_id',
        readonly=False,
    )

    net_taxable_income = fields.Monetary(
        related='employee_id.net_taxable_income',
        string='Net Taxable Income',
        currency_field='currency_id',
        readonly=False,
    )

    tds_amount = fields.Monetary(
        related='employee_id.tds_amount',
        string='TDS Amount (Annual)',
        currency_field='currency_id',
        readonly=False,
    )

    tds_amount_month = fields.Monetary(
        related='employee_id.tds_amount_month',
        string='TDS Amount (Monthly)',
        currency_field='currency_id',
        readonly=False,
    )

    tds_amount_new = fields.Monetary(
        related='employee_id.tds_amount_new',
        string='TDS Amount (New Regime)',
        currency_field='currency_id',
        readonly=False,
    )

    tds_amount_new_month = fields.Monetary(
        related='employee_id.tds_amount_new_month',
        string='TDS Amount New Regime (Month)',
        currency_field='currency_id',
        readonly=False,
    )

    tds_till_last_month = fields.Monetary(
        related='employee_id.tds_till_last_month',
        string='TDS Till Last Month',
        currency_field='currency_id',
        readonly=False,
    )

    surcharge_amount = fields.Monetary(
        related='employee_id.surcharge_amount',
        string='Surcharge Amount',
        currency_field='currency_id',
        readonly=False,
    )

    relief_amount = fields.Monetary(
        related='employee_id.relief_amount',
        string='Marginal Relief Amount',
        currency_field='currency_id',
        readonly=False,
    )

    l10n_in_incentive_percentage = fields.Monetary(
        related='employee_id.l10n_in_incentive_percentage',
        readonly=False,
    )

    # ==========================================================
    # Currency
    # ==========================================================

    currency_id = fields.Many2one(
        related='employee_id.currency_id',
        string='Currency',
        readonly=True,
    )

    # l10n_in_pf_employee_type = fields.Selection(
    #     related="version_id.l10n_in_pf_employee_type",
    #     store=True,
    #     readonly=False,
    # )
    #
    # l10n_in_pf_employer_type = fields.Selection(
    #     related="version_id.l10n_in_pf_employer_type",
    #     store=True,
    #     readonly=False,
    # )
    # dearness_allowance = fields.Monetary(
    #     related="version_id.dearness_allowance",
    #     store=True,
    #     readonly=False,
    # )
    # conveyance_allowance = fields.Monetary(
    #     related="version_id.conveyance_allowance",
    #     store=True,
    #     readonly=False,
    # )

    # ==========================================================
    # Payslip Fields
    # ==========================================================

    # ADD HERE
    payslip_gross_wage = fields.Monetary(
        string="Payslip Gross Wage",
        currency_field='currency_id',
        compute="_compute_payslip_gross_wage",
        store=True
    )
    payslip_yearly_cost = fields.Monetary(
        string="Payslip Yearly Cost",
        currency_field='currency_id',
        compute="_compute_payslip_yearly_cost",
        store=True
    )

    payslip_month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ],
        string="Payslip Month",
        default=lambda self: str(fields.Date.today().month)
    )
    payslip_paid_days = fields.Float(
        string="Payslip Paid Days",
        default=0.0,
    )

    total_income = fields.Monetary(
        string="Total Income",
        currency_field="currency_id",
        compute="_compute_total_income",
        store=True
    )

    annual_tds_base = fields.Float(
        string="Annual TDS Base",
        copy=False,
    )

    bereavement_allocation_year = fields.Integer(
        string="Bereavement Allocation Year",
        default=0
    )

    month = fields.Selection([
        ('1', 'January'), ('2', 'February'), ('3', 'March'),
        ('4', 'April'), ('5', 'May'), ('6', 'June'),
        ('7', 'July'), ('8', 'August'), ('9', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ], string="Month")

    year = fields.Char(
        string="Year",
        default=lambda self: str(fields.Date.today().year)
    )

    # ==========================================================
    # Salary / Working Day Calculation Fields
    # ==========================================================

    total_days = fields.Integer(
        related='employee_id.total_days',
        string="Total Days in Month",
        readonly=False,
    )

    per_day_gross = fields.Float(
        related='employee_id.per_day_gross',
        string="Per Day Gross",
        readonly=False,
    )

    per_day_basic = fields.Float(
        related='employee_id.per_day_basic',
        string="Per Day Basic",
        readonly=False,
    )

    prorated_salary = fields.Float(
        related='employee_id.prorated_salary',
        string="Prorated Salary",
        readonly=False,
    )

    leave_encashment = fields.Monetary(
        related='employee_id.leave_encashment',
        string="Leave Encashment Amount",
        currency_field='currency_id',
        readonly=False,
    )
    el_balance = fields.Float(
        string="EL Balance",
        compute="_compute_el_balance",
        store=False
    )

    total_earnings = fields.Monetary(
        related='employee_id.total_earnings',
        string="Total Earnings",
        currency_field='currency_id',
        readonly=False,
    )

    # ==========================================================
    # Notice Period / Full & Final Fields
    # ==========================================================

    period_days = fields.Float(
        related='employee_id.period_days',
        string="Notice Period (Days)",
        readonly=False,
    )

    notice_served_days = fields.Float(
        related='employee_id.notice_served_days',
        string="Notice Served (Days)",
        readonly=False,
    )

    unserved_days = fields.Float(
        related='employee_id.unserved_days',
        string="Unserved Days",
        readonly=False,
    )

    notice_recovery = fields.Monetary(
        related='employee_id.notice_recovery',
        string="Notice Recovery",
        currency_field='currency_id',
        readonly=False,
    )

    total_advance = fields.Monetary(
        related='employee_id.total_advance',
        string="Total Advance",
        currency_field='currency_id',
        readonly=False,
    )

    amount_recovered = fields.Monetary(
        related='employee_id.amount_recovered',
        string="Amount Recovered",
        currency_field='currency_id',
        readonly=False,
    )

    outstanding_amount = fields.Monetary(
        related='employee_id.outstanding_amount',
        string="Outstanding Amount",
        currency_field='currency_id',
        readonly=False,
    )

    # ==========================================================
    # Full & Final Salary Fields
    # ==========================================================

    ff_total_wage = fields.Float(
        related='employee_id.ff_total_wage',
        string="Total Wage",
        readonly=False,
    )

    ff_basic = fields.Float(
        related='employee_id.ff_basic',
        string="FF Basic",
        readonly=False,
    )

    ff_paid_days = fields.Float(
        related='employee_id.ff_paid_days',
        string="FF Paid Days",
        readonly=False,
    )

    ff_paid_days1 = fields.Float(
        related='employee_id.ff_paid_days1',
        string="Paid Days",
        readonly=False,
    )

    # ==========================================================
    # Earnings / Arrears Fields
    # ==========================================================

    variable_pay = fields.Monetary(
        related='employee_id.variable_pay',
        string="Variable Pay",
        currency_field='currency_id',
        readonly=False,
    )

    variable_bonus = fields.Monetary(
        related='employee_id.variable_bonus',
        string="Bonus",
        currency_field='currency_id',
        readonly=False,
    )

    basic_arrear = fields.Monetary(
        related='employee_id.basic_arrear',
        string="Basic Arrear",
        currency_field='currency_id',
        readonly=False,
    )

    hra_arrear = fields.Monetary(
        related='employee_id.hra_arrear',
        string="HRA Arrear",
        currency_field='currency_id',
        readonly=False,
    )

    special_allowance_arrear = fields.Monetary(
        related='employee_id.special_allowance_arrear',
        string="Special Allowance Arrear",
        currency_field='currency_id',
        readonly=False,
    )

    fixed_stipend = fields.Monetary(
        related='employee_id.fixed_stipend',
        string="Fixed Stipend",
        currency_field='currency_id',
        readonly=False,
    )

    stipend = fields.Monetary(
        related='employee_id.stipend',
        string="Stipend",
        currency_field='currency_id',
        readonly=False,
    )

    stipend_arrear = fields.Monetary(
        related='employee_id.stipend_arrear',
        string="Stipend Arrear",
        currency_field='currency_id',
        readonly=False,
    )

    employee_incentive = fields.Monetary(
        related='employee_id.employee_incentive',
        string="Incentive",
        currency_field='currency_id',
        readonly=False,
    )

    referral_incentive = fields.Monetary(
        related='employee_id.referral_incentive',
        string="Referral Incentive",
        currency_field='currency_id',
        readonly=False,
    )

    notice_period = fields.Monetary(
        related='employee_id.notice_period',
        string="Notice Period Pay",
        currency_field='currency_id',
        readonly=False,
    )

    show_employee_earnings_details = fields.Boolean(
        string="Show Employee Earnings Details",
        default=False,
    )

    show_employee_deductions_details = fields.Boolean(
        string="Show Employee Deductions Details",
        default=False,
    )

    show_nps_contribution_details = fields.Boolean(
        string="Show NPS Contribution Details",
        default=False,
    )

    salary_arrear = fields.Monetary(
        related='employee_id.salary_arrear',
        string="Salary Arrear",
        currency_field='currency_id',
        readonly=False,
    )

    hold_salary = fields.Monetary(
        related='employee_id.hold_salary',
        string="Hold Salary",
        currency_field='currency_id',
        readonly=False,
    )

    other_earnings = fields.Monetary(
        related='employee_id.other_earnings',
        string="Other Earnings",
        currency_field='currency_id',
        readonly=False,
    )

    # ==========================================================
    # Deduction Fields
    # ==========================================================

    notice_pay_deduction = fields.Monetary(
        related='employee_id.notice_pay_deduction',
        string="Notice Pay Deduction",
        currency_field='currency_id',
        readonly=False,
    )

    loan_deduction = fields.Monetary(
        related='employee_id.loan_deduction',
        string="Loan",
        currency_field='currency_id',
        readonly=False,
    )

    pf_arrear = fields.Monetary(
        related='employee_id.pf_arrear',
        string="PF Arrear",
        currency_field='currency_id',
        readonly=False,
    )

    other_deductions = fields.Monetary(
        related='employee_id.other_deductions',
        string="Other Deductions",
        currency_field='currency_id',
        readonly=False,
    )

    # ==========================================================
    # Loan Fields
    # ==========================================================

    loan_amount = fields.Float(
        related='employee_id.loan_amount',
        string="Loan Amount",
        readonly=False,
    )

    loan_interest = fields.Float(
        related='employee_id.loan_interest',
        string="Interest %",
        readonly=False,
    )

    loan_months = fields.Integer(
        related='employee_id.loan_months',
        string="No of Installments",
        readonly=False,
    )

    monthly_installment = fields.Float(
        related='employee_id.monthly_installment',
        string="Monthly Installment",
        readonly=False,
    )

    total_payable_amount = fields.Float(
        related='employee_id.total_payable_amount',
        string="Total Payable",
        readonly=False,
    )

    remaining_balance = fields.Float(
        related='employee_id.remaining_balance',
        string="Remaining Balance",
        readonly=False,
    )

    paid_installments = fields.Integer(
        related='employee_id.paid_installments',
        string="Paid Installments",
        readonly=False,
    )
    # ==========================================================
    # Rented House
    # ==========================================================

    is_rented_house = fields.Boolean(
        related='employee_id.is_rented_house',
        string='Are you staying in a rented house?',
        readonly=False,
    )
    show_pf_contribution_details = fields.Boolean(
        string="Show PF Contribution Details",
        default=False,
    )

    show_esic_details = fields.Boolean(
        string="Show ESIC Details",
        default=False,
    )

    show_other_deductions_details = fields.Boolean(
        string="Show Other Deductions Details",
        default=False,
    )

    show_lwf_details = fields.Boolean(
        string="Show LWF Details",
        default=False,
    )

    show_tax_deductions_details = fields.Boolean(
        string="Show Tax Deductions Details",
        default=False,
    )
    basic_salary_annual = fields.Monetary(
        related='employee_id.basic_salary_annual',
        string="Basic Salary (Annual)",
        currency_field='currency_id',
        readonly=True,
    )

    hra_annual = fields.Monetary(
        related='employee_id.hra_annual',
        string="HRA (Annual)",
        currency_field='currency_id',
        readonly=True,
    )

    conveyance_annual = fields.Monetary(
        related='employee_id.conveyance_annual',
        string="Conveyance Allowance (Annual)",
        currency_field='currency_id',
        readonly=True,
    )

    stipend_annual = fields.Monetary(
        string="Stipend (Annual)",
        compute="_compute_salary_structure_amounts",
        currency_field="currency_id",
    )

    pf_employer_annual = fields.Monetary(
        related='employee_id.pf_employer_annual',
        string="PF Employer Contribution (Annual)",
        currency_field='currency_id',
        readonly=True,
    )

    edli_employer_amount = fields.Monetary(
        related='employee_id.edli_employer_amount',
        string="EDLI - Employer Contribution",
        currency_field='currency_id',
        readonly=True,
    )

    edli_employer_annual = fields.Monetary(
        related='employee_id.edli_employer_annual',
        string="EDLI Employer Contribution (Annual)",
        currency_field='currency_id',
        readonly=True,
    )

    epf_admin_amount = fields.Monetary(
        related='employee_id.epf_admin_amount',
        string="EPF Admin Charges - Employer Contribution",
        currency_field='currency_id',
        readonly=True,
    )

    epf_admin_annual = fields.Monetary(
        related='employee_id.epf_admin_annual',
        string="EPF Admin Charges (Annual)",
        currency_field='currency_id',
        readonly=True,
    )

    salary_structure_gross_earnings = fields.Monetary(
        related='employee_id.salary_structure_gross_earnings',
        string="Gross Earnings",
        currency_field='currency_id',
        readonly=True,
    )

    salary_structure_gross_earnings_annual = fields.Monetary(
        related='employee_id.salary_structure_gross_earnings_annual',
        string="Gross Earnings (Annual)",
        currency_field='currency_id',
        readonly=True,
    )

    salary_structure_monthly_total = fields.Monetary(
        related='employee_id.salary_structure_monthly_total',
        string="Cost to Company",
        currency_field='currency_id',
        readonly=True,
    )

    salary_structure_annual_total = fields.Monetary(
        related='employee_id.salary_structure_annual_total',
        string="Annual Cost to Company",
        currency_field='currency_id',
        readonly=True,
    )

    PF_WAGE_LIMIT = 25000.0
    EDLI_ADMIN_RATE = 0.005

    total_epf_amount = fields.Monetary(
        string="Total EPF Contribution",
        compute="_compute_salary_structure_amounts",
        currency_field="currency_id",
    )

    total_epf_annual = fields.Monetary(
        string="Total EPF Contribution (Annual)",
        compute="_compute_salary_structure_amounts",
        currency_field="currency_id",
    )

    pf_wage_label = fields.Char(
        string="PF Wage Label",
        compute="_compute_salary_structure_amounts",
    )

