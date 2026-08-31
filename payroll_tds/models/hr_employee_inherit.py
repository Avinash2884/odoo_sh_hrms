import calendar
import logging
import re
import math
import math
from decimal import Decimal, ROUND_HALF_UP
from odoo.exceptions import ValidationError
from odoo import models, fields, api
from calendar import monthrange
from datetime import date


class Employee(models.Model):
    _inherit = 'hr.employee'


    revision_ids = fields.One2many(
        'employee.salary.revision',
        'employee_id',
        string='Revised Wage Details'
    )

    pl_allocation_year = fields.Integer(
        string="PL Allocation Year",
        default=0
    )

    last_cl_allocation_month = fields.Char(
        string="Last CL Allocation Month"
    )

    last_sl_allocation_month = fields.Char(
        string="Last SL Allocation Month"
    )

    bereavement_allocation_year = fields.Integer(
        string="Bereavement Allocation Year",
        default=0
    )
    l10n_in_nps_employer_type = fields.Selection(
        selection=[
            ('5', '5%'),
            ('10', '10%'),
            ('14', '14%'),
        ],
        string="NPS Employer Contribution",
        default='10',
    )

    l10n_in_nps_employer_amount = fields.Monetary(
        string="NPS Employer Amount",
        compute="_compute_l10n_in_nps_employer_amount",
        store=True,
        currency_field='currency_id',
    )

    @api.depends('l10n_in_nps_employer_type')
    def _compute_l10n_in_nps_employer_amount(self):
        for employee in self:
            basic = employee.version_id.l10n_in_basic_salary_amount or 0.0
            percentage = float(
                employee.l10n_in_nps_employer_type or 0.0
            )

            employee.l10n_in_nps_employer_amount = (
                    basic * percentage / 100
            )

    pran_number = fields.Char(
        string="PRAN Number",
        copy=False,
        help="Enter a valid 12-digit PRAN number.",
    )

    @api.constrains("pran_number")
    def _check_pran_number(self):
        for employee in self:
            if employee.pran_number:
                pran = employee.pran_number.strip()

                if not re.fullmatch(r"\d{12}", pran):
                    raise ValidationError(
                        "PRAN Number must contain exactly 12 digits."
                    )

    financial_year_incentive = fields.Monetary(
        string="Financial Year Incentive",
        currency_field='currency_id',
        default=0.0,
        copy=False,
    )

    def _get_financial_year_start(self, payslip_date=None):
        """Return Financial Year start date (1st April)."""

        if not payslip_date:
            payslip_date = fields.Date.today()

        payslip_date = fields.Date.to_date(payslip_date)

        if payslip_date.month >= 4:
            return payslip_date.replace(
                month=4,
                day=1
            )
        else:
            return payslip_date.replace(
                year=payslip_date.year - 1,
                month=4,
                day=1
            )

    def _get_financial_year_end(self, payslip_date=None):
        """Return Financial Year end date (31st March)."""

        fy_start = self._get_financial_year_start(
            payslip_date
        )

        return fy_start.replace(
            year=fy_start.year + 1,
            month=3,
            day=31
        )

    def _update_financial_year_incentive(self, payslip):
        """
        Store cumulative IN + Bonus for the current Financial Year.

        Existing functionality is not changed.
        This method only updates financial_year_incentive.
        """

        for employee in self:

            if not employee or not payslip:
                continue

            if not payslip.date_from:
                continue

            payslip_date = fields.Date.to_date(
                payslip.date_from
            )

            fy_start = employee._get_financial_year_start(
                payslip_date
            )

            fy_end = employee._get_financial_year_end(
                payslip_date
            )

            # -------------------------------------------------
            # NEW FINANCIAL YEAR
            # -------------------------------------------------
            #
            # If April is the first payslip of the FY,
            # start the accumulation from zero.
            #
            # -------------------------------------------------

            if payslip_date.month == 4:

                previous_fy_slips = self.env['hr.payslip'].search([
                    ('employee_id', '=', employee.id),
                    ('date_from', '>=', fy_start),
                    ('date_from', '<', payslip.date_from),
                    ('state', 'in', ['done', 'paid']),
                ])

                if not previous_fy_slips:
                    employee.financial_year_incentive = 0.0

            # -------------------------------------------------
            # GET CURRENT PAYSLIP IN
            # -------------------------------------------------

            incentive_lines = payslip.line_ids.filtered(
                lambda line: line.code == 'IN'
            )

            current_incentive = abs(
                sum(incentive_lines.mapped('total'))
            )

            # -------------------------------------------------
            # GET CURRENT PAYSLIP BONUS
            # -------------------------------------------------

            bonus_lines = payslip.line_ids.filtered(
                lambda line: line.code == 'Bonus'
            )

            current_bonus = abs(
                sum(bonus_lines.mapped('total'))
            )

            # -------------------------------------------------
            # CURRENT MONTH ADDITION
            # -------------------------------------------------

            current_month_amount = (
                current_incentive
                + current_bonus
            )

            # -------------------------------------------------
            # FIND PREVIOUS PAYSLIPS IN SAME FY
            # -------------------------------------------------

            previous_slips = self.env['hr.payslip'].search([
                ('employee_id', '=', employee.id),
                ('id', '!=', payslip.id),
                ('date_from', '>=', fy_start),
                ('date_from', '<', payslip.date_from),
                ('date_from', '<=', fy_end),
                ('state', 'in', ['done', 'paid']),
            ], order='date_from asc, id asc')

            # -------------------------------------------------
            # CALCULATE PREVIOUS IN + BONUS
            # -------------------------------------------------

            previous_total = 0.0

            for previous_slip in previous_slips:

                previous_incentive_lines = (
                    previous_slip.line_ids.filtered(
                        lambda line: line.code == 'IN'
                    )
                )

                previous_bonus_lines = (
                    previous_slip.line_ids.filtered(
                        lambda line: line.code == 'Bonus'
                    )
                )

                previous_incentive = abs(
                    sum(
                        previous_incentive_lines.mapped('total')
                    )
                )

                previous_bonus = abs(
                    sum(
                        previous_bonus_lines.mapped('total')
                    )
                )

                previous_total += (
                    previous_incentive
                    + previous_bonus
                )

            # -------------------------------------------------
            # STORE CUMULATIVE FY VALUE
            # -------------------------------------------------

            employee.financial_year_incentive = (
                previous_total
                + current_month_amount
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

    @api.depends(
        'l10n_in_nps_employer_type',
        'version_id.l10n_in_basic_salary_amount',
    )
    def _compute_l10n_in_nps_employer_amount(self):
        for employee in self:
            basic = employee.version_id.l10n_in_basic_salary_amount or 0.0

            percentage = float(
                employee.l10n_in_nps_employer_type or 0.0
            )

            employee.l10n_in_nps_employer_amount = (
                    basic * percentage / 100
            )

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

    @api.depends(
        'rented_house_ids',
        'rented_house_ids.total_hra_exemption',
        'tax_regime'
    )
    def _compute_hra_exemption_amount(self):
        for emp in self:
            if emp.tax_regime == 'old':
                emp.hra_exemption_amount = sum(
                    emp.rented_house_ids.mapped('total_hra_exemption')
                )
            else:
                emp.hra_exemption_amount = 0.0

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

    standard_deduction = fields.Monetary(string='Standard Deduction')

    section_80c = fields.Monetary(string='Section 123 (80C)', help="Available only under Old Regime")
    # section_123_80c = fields.Monetary(
    #     string='Section 123 (80C)',
    #     help="Available only under Old Regime"
    # )

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
    section_80d = fields.Monetary(string='Section 80D', help="Available only under Old Regime")
    section_80g = fields.Monetary(string='Section 80G', help="Available only under Old Regime")
    nps = fields.Monetary(string='NPS (80CCD(1B))', help="Available only under Old Regime")
    home_loan_interest = fields.Monetary(string='Home loan interest',  currency_field='currency_id',
    help="Available only under Old Regime. Maximum allowable amount is ₹2,00,000.")

    @api.onchange('home_loan_interest')
    def _onchange_home_loan_interest(self):
        if self.home_loan_interest and self.home_loan_interest > 200000:
            self.home_loan_interest = 200000

    net_taxable_income = fields.Monetary(
        string='Net Taxable Income',
        currency_field='currency_id',
        compute='_compute_net_taxable_income',
        store=True,
        readonly=False
    )
    tds_amount = fields.Monetary(
        string='TDS Amount (Annual)',
        currency_field='currency_id',
        compute='_compute_tds_amount',
        store=True,
        readonly=False
    )

    tds_amount_month = fields.Monetary(
        string='TDS Amount (Monthly)',
        currency_field='currency_id',
        compute='_compute_tds_amount_month',
        store=True,
        readonly=False
    )

    tds_amount_new = fields.Monetary(
        string='TDS Amount (New Regime)',
        currency_field='currency_id',
        compute='_compute_tds_amount_new',
        store=True,
        readonly=False
    )

    tds_amount_new_month = fields.Monetary(
        string='TDS Amount New Regime (Month)',
        currency_field='currency_id',
        compute="_compute_tds_amount_new_month",
        store=True,
        readonly=False
    )
    tds_till_last_month = fields.Monetary(
        string="TDS Till Last Month",
        currency_field='currency_id',
        default=0.0,
    )
    surcharge_amount = fields.Monetary(
        string='Surcharge Amount',
        currency_field='currency_id',
        compute='_compute_tds_amount_new',
        store=True
    )
    relief_amount = fields.Monetary(
        string='Marginal Relief Amount',
        currency_field='currency_id',
        compute='_compute_tds_amount_new',
        store=True
    )
    l10n_in_incentive_percentage = fields.Monetary(
        readonly=False,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
    )

    l10n_in_pf_employee_type = fields.Selection(
        related="version_id.l10n_in_pf_employee_type",
        store=True,
        readonly=False,
    )

    l10n_in_pf_employer_type = fields.Selection(
        related="version_id.l10n_in_pf_employer_type",
        store=True,
        readonly=False,
    )
    dearness_allowance = fields.Monetary(
        related="version_id.dearness_allowance",
        store=True,
        readonly=False,
    )
    conveyance_allowance = fields.Monetary(
        related="version_id.conveyance_allowance",
        store=True,
        readonly=False,
    )
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

    @api.depends(
        'wage',
        'payslip_gross_wage',
        'payslip_paid_days',
        'payslip_month',
        'contract_date_start',
        'final_yearly_costs',
        'financial_year_incentive',
    )
    def _compute_total_income(self):
        for emp in self:

            # =====================================================
            # EXISTING EMPLOYEE CALCULATION
            # =====================================================

            emp.total_income = (
                    (emp.final_yearly_costs or 0.0)
                    + (emp.financial_year_incentive or 0.0)
            )

            # =====================================================
            # BASIC VALIDATION
            # =====================================================

            if not emp.contract_date_start or not emp.payslip_month:
                continue

            joining_date = emp.contract_date_start
            payslip_month = int(emp.payslip_month)

            # =====================================================
            # JOINING MONTH AND PAYSLIP MONTH MUST BE SAME
            # =====================================================

            if joining_date.month != payslip_month:
                continue

            total_days = monthrange(
                joining_date.year,
                joining_date.month
            )[1]

            # =====================================================
            # JOINED ON 1ST -> EXISTING LOGIC
            # =====================================================

            if joining_date.day == 1:
                continue

            # =====================================================
            # FULL MONTH SALARY -> EXISTING LOGIC
            # =====================================================

            if (emp.payslip_paid_days or 0.0) >= total_days:
                continue

            # =====================================================
            # NEW JOINER - PARTIAL JOINING MONTH
            # =====================================================

            if payslip_month >= 4:
                remaining_months = 15 - payslip_month
            else:
                remaining_months = 3 - payslip_month

            print("\n")
            print("====================================================")
            print("NEW JOINER TOTAL INCOME CALCULATION")
            print("Employee:", emp.name)
            print("Employee ID:", emp.id)
            print("====================================================")

            print("Joining Date:", joining_date)
            print("Payslip Month:", payslip_month)
            print("Total Days:", total_days)
            print("Paid Days:", emp.payslip_paid_days)
            print("Remaining Months:", remaining_months)

            print("Gross Wage:", emp.wage)
            print("Joining Month Gross:", emp.payslip_gross_wage)
            print(
                "Financial Year Incentive:",
                emp.financial_year_incentive
            )

            # =====================================================
            # JOINING MONTH ACTUAL SALARY
            # +
            # REMAINING FULL MONTH SALARY
            # +
            # FINANCIAL YEAR INCENTIVE
            # =====================================================

            joining_month_income = (
                    emp.payslip_gross_wage or 0.0
            )

            remaining_salary_income = (
                    (emp.wage or 0.0) * remaining_months
            )

            incentive_income = (
                    emp.financial_year_incentive or 0.0
            )

            emp.total_income = (
                    joining_month_income
                    + remaining_salary_income
                    + incentive_income
            )

            # =====================================================
            # DEBUG
            # =====================================================

            print("----------------------------------------------------")
            print("JOINING MONTH INCOME:", joining_month_income)
            print("REMAINING SALARY:", remaining_salary_income)
            print("INCENTIVE INCOME:", incentive_income)
            print("----------------------------------------------------")
            print("TOTAL INCOME:", emp.total_income)
            print("====================================================")

    annual_tds_base = fields.Float(
        string="Annual TDS Base",
        copy=False,
    )

    pl_allocation_year = fields.Integer(
        string="PL Allocation Year",
        default=0
    )

    last_cl_allocation_month = fields.Char(
        string="Last CL Allocation Month"
    )

    last_sl_allocation_month = fields.Char(
        string="Last SL Allocation Month"
    )

    bereavement_allocation_year = fields.Integer(
        string="Bereavement Allocation Year",
        default=0
    )

    @api.depends('payslip_month')
    def _compute_payslip_gross_wage(self):
        for emp in self:

            emp.payslip_gross_wage = 0.0

            if not emp.payslip_month:
                continue

            year = fields.Date.today().year
            month = int(emp.payslip_month)

            # First day of month
            start_date = date(year, month, 1)

            # Last day of month
            last_day = monthrange(year, month)[1]
            end_date = date(year, month, last_day)

            payslip = self.env['hr.payslip'].search([
                ('employee_id', '=', emp.id),
                ('date_from', '>=', start_date),
                ('date_to', '<=', end_date),
            ], limit=1, order="id desc")

            if payslip:
                emp.payslip_gross_wage = payslip.gross_wage or 0.0

    @api.depends('payslip_gross_wage')
    def _compute_payslip_yearly_cost(self):
        for emp in self:
            emp.payslip_yearly_cost = (
                                              emp.payslip_gross_wage or 0.0
                                      ) * 12

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

    total_days = fields.Integer(
        string="Total Days in Month",
        compute="_compute_total_days",
        store=True
    )
    per_day_gross = fields.Float(
        string="Per Day Gross",
        compute="_compute_per_day_gross",
        store=True
    )
    per_day_basic = fields.Float(
        string="Per Day Basic",
        compute="_compute_per_day_basic",
        store=True
    )

    prorated_salary = fields.Float(
        string="Prorated Salary",
        compute="_compute_prorated_salary",
        store=True
    )

    el_balance = fields.Float(
        string="EL Balance",
        compute="_compute_el_balance",
        store=False
    )



    leave_encashment = fields.Monetary(
        string="Leave Encashment Amount",
    )

    total_earnings = fields.Monetary(
        string="Total Earnings",
        compute="_compute_total_earnings",
        store=True
    )

    period_days = fields.Float(string="Notice Period (Days)")
    notice_served_days = fields.Float(string="Notice Served (Days)")

    unserved_days = fields.Float(
        string="Unserved Days",
        compute="_compute_unserved_days",
        store=True
    )

    notice_recovery = fields.Monetary(
        string="Notice Recovery",
        compute="_compute_notice_recovery",
        store=True
    )

    total_advance = fields.Monetary(
        string="Total Advance",
        currency_field='currency_id'
    )

    amount_recovered = fields.Monetary(
        string="Amount Recovered",
        currency_field='currency_id'
    )

    outstanding_amount = fields.Monetary(
        string="Outstanding Amount",
        currency_field='currency_id',
        compute="_compute_outstanding_amount",
        store=True
    )

    @api.depends('period_days', 'notice_served_days')
    def _compute_unserved_days(self):
        for emp in self:
            period = emp.period_days or 0.0
            served = emp.notice_served_days or 0.0

            # Avoid negative values
            emp.unserved_days = max(period - served, 0.0)

    @api.depends('unserved_days', 'per_day_gross')
    def _compute_notice_recovery(self):
        for emp in self:
            emp.notice_recovery = (emp.unserved_days or 0.0) * (emp.per_day_gross or 0.0)

    @api.depends('month', 'year')
    def _compute_total_days(self):
        for emp in self:
            if emp.month and emp.year:
                emp.total_days = monthrange(int(emp.year), int(emp.month))[1]
            else:
                emp.total_days = 0

    @api.depends('wage', 'total_days')
    def _compute_per_day_gross(self):
        for emp in self:
            if emp.wage and emp.total_days:
                emp.per_day_gross = emp.wage / emp.total_days
            else:
                emp.per_day_gross = 0.0

    @api.depends('l10n_in_basic_salary_amount', 'total_days')
    def _compute_per_day_basic(self):
        for emp in self:
            if emp.l10n_in_basic_salary_amount and emp.total_days:
                emp.per_day_basic = emp.l10n_in_basic_salary_amount / emp.total_days
            else:
                emp.per_day_basic = 0.0

    @api.depends('per_day_gross', 'ff_paid_days1')
    def _compute_prorated_salary(self):
        for emp in self:
            if emp.per_day_gross and emp.ff_paid_days1:
                emp.prorated_salary = emp.per_day_gross * emp.ff_paid_days1
            else:
                emp.prorated_salary = 0.0

    def _compute_el_balance(self):
        for emp in self:
            leave_type = self.env['hr.leave.type'].search([
                ('name', '=', 'Privilege Leave')
            ], limit=1)

            if leave_type:
                emp.el_balance = leave_type.with_context(employee_id=emp.id).virtual_remaining_leaves
            else:
                emp.el_balance = 0.0

    @api.onchange('el_balance', 'per_day_basic')
    def _onchange_leave_encashment(self):
        if not self.leave_encashment:
            self.leave_encashment = (
                    (self.el_balance or 0.0)
                    * (self.per_day_basic or 0.0)
            )

    @api.depends(
        'prorated_salary',
        'leave_encashment',
        'l10n_in_gratuity',
        'other_earnings'
    )
    def _compute_total_earnings(self):
        for emp in self:
            emp.total_earnings = (
                    (emp.prorated_salary or 0.0)
                    + (emp.leave_encashment or 0.0)
                    + (emp.l10n_in_gratuity or 0.0)
                    + (emp.other_earnings or 0.0)
            )

    @api.depends('total_advance', 'amount_recovered')
    def _compute_outstanding_amount(self):
        for emp in self:
            advance = emp.total_advance or 0.0
            recovered = emp.amount_recovered or 0.0

            # If recovered exceeds advance, avoid negative (optional)
            emp.outstanding_amount = max(advance - recovered, 0.0)

    ff_total_wage = fields.Float(string="Total Wage")
    ff_basic = fields.Float(string="FF Basic")
    ff_paid_days = fields.Float(string="FF Paid Days")
    ff_paid_days1 = fields.Float(string="Paid Days")

    @api.depends(
        'final_yearly_costs',
        'total_income',
        'financial_year_incentive',
        'standard_deduction',
        'hra_exemption_amount',
        'tax_on_employment',
        'entertainment_allowance',
        'previous_employment_income',
        'previous_employment_professional_tax',
        'section_80c',
        'section_123_80ccc',
        'section_124_1_80ccd_1',
        'section_124_1b_80ccd_1b',
        'section_126_80d',
        'section_127_80dd',
        'section_128_80ddb',
        'section_129_80e',
        'section_130_80ee',
        'section_131_80eea',
        'section_132_80eeb',
        'section_133_80g',
        'section_134_80gg',
        'section_137_80ggc',
        'section_153_80tta',
        'section_154_80u',
        'section_80d',
        'section_80g',
        'nps',
        'home_loan_interest',
        'tax_regime',
    )
    def _compute_net_taxable_income(self):
        for emp in self:

            annual_income = emp.final_yearly_costs or 0.0

            joining_date = emp.contract_date_start

            # =========================================================
            # NEW JOINER IN CURRENT FINANCIAL YEAR
            # =========================================================
            if joining_date and emp.payslip_month:

                payslip_month = int(emp.payslip_month)

                # -----------------------------------------------------
                # Joining month itself
                # -----------------------------------------------------
                if (
                        joining_date.month == payslip_month
                        and joining_date.day > 1
                ):

                    gross_wage = emp.wage or 0.0
                    payslip_gross = emp.payslip_gross_wage or 0.0

                    # Partial month salary
                    if round(gross_wage, 2) != round(
                            payslip_gross, 2
                    ):
                        annual_income = (
                                emp.total_income
                                or annual_income
                        )

                    # Full month salary
                    else:
                        annual_income = (
                                emp.final_yearly_costs
                                or 0.0
                        )

                # -----------------------------------------------------
                # Current payslip month is AFTER joining month
                # -----------------------------------------------------
                elif (
                        joining_date.day > 1
                        and joining_date.month != payslip_month
                ):

                    # Find joining month payslip
                    joining_month_start = date(
                        joining_date.year,
                        joining_date.month,
                        1
                    )

                    joining_month_end = date(
                        joining_date.year,
                        joining_date.month,
                        monthrange(
                            joining_date.year,
                            joining_date.month
                        )[1]
                    )

                    joining_payslip = self.env['hr.payslip'].search(
                        [
                            ('employee_id', '=', emp.id),
                            ('date_from', '>=', joining_month_start),
                            ('date_to', '<=', joining_month_end),
                        ],
                        order='id desc',
                        limit=1
                    )

                    joining_month_gross = 0.0

                    if joining_payslip:
                        joining_month_gross = (
                                joining_payslip.gross_wage or 0.0
                        )

                    # -------------------------------------------------
                    # Remaining months in Financial Year
                    # -------------------------------------------------
                    if payslip_month >= 4:
                        remaining_months = 16 - payslip_month
                    else:
                        remaining_months = 4 - payslip_month

                    # -------------------------------------------------
                    # Total Income
                    #
                    # Joining month actual salary
                    # +
                    # Remaining full month salary
                    # -------------------------------------------------
                    if joining_month_gross:

                        annual_income = (
                                joining_month_gross
                                + (
                                        (emp.wage or 0.0)
                                        * remaining_months
                                )
                                + (emp.financial_year_incentive or 0.0)
                        )

                        print("----------------------------------------------------")
                        print("NET TAXABLE INCOME - NEW JOINER CALCULATION")
                        print("Joining Month Gross:", joining_month_gross)
                        print("Remaining Months:", remaining_months)
                        print(
                            "Remaining Salary:",
                            (emp.wage or 0.0) * remaining_months
                        )
                        print(
                            "Financial Year Incentive:",
                            emp.financial_year_incentive or 0.0
                        )
                        print(
                            "Annual Income Used:",
                            annual_income
                        )
                        print("----------------------------------------------------")
                    else:
                        # Keep existing functionality if
                        # joining month payslip is not available
                        annual_income = (
                                emp.total_income
                                or annual_income
                        )

            # =========================================================
            # DEDUCTIONS
            # =========================================================
            deduction = emp.standard_deduction or 0.0

            if emp.tax_regime == 'old':
                deduction += (
                        emp.hra_exemption_amount or 0.0
                )

                deduction += (
                        emp.tax_on_employment or 0.0
                )

                deduction += (
                        emp.entertainment_allowance or 0.0
                )

                # Previous Employment
                deduction += (
                        emp.previous_employment_income or 0.0
                )

                deduction += (
                        emp.previous_employment_professional_tax
                        or 0.0
                )

                deduction += (
                        (emp.section_80c or 0.0)
                        + (emp.section_80d or 0.0)
                        + (emp.section_80g or 0.0)
                        + (emp.nps or 0.0)
                        + (emp.section_123_80ccc or 0.0)
                        + (emp.section_124_1_80ccd_1 or 0.0)
                        + (emp.section_124_1b_80ccd_1b or 0.0)
                        + (emp.section_126_80d or 0.0)
                        + (emp.section_127_80dd or 0.0)
                        + (emp.section_128_80ddb or 0.0)
                        + (emp.section_129_80e or 0.0)
                        + (emp.section_130_80ee or 0.0)
                        + (emp.section_131_80eea or 0.0)
                        + (emp.section_132_80eeb or 0.0)
                        + (emp.section_133_80g or 0.0)
                        + (emp.section_134_80gg or 0.0)
                        + (emp.section_137_80ggc or 0.0)
                        + (emp.section_153_80tta or 0.0)
                        + (emp.section_154_80u or 0.0)
                        + min(
                    emp.home_loan_interest or 0.0,
                    200000.0
                )
                )

            # =========================================================
            # NET TAXABLE INCOME
            # =========================================================
            emp.net_taxable_income = max(
                annual_income - deduction,
                0.0
            )

            print("\n")
            print("====================================================")
            print("NET TAXABLE INCOME CALCULATION")
            print("Employee:", emp.name)
            print("Employee ID:", emp.id)
            print("Final Yearly Costs:", emp.final_yearly_costs or 0.0)
            print(
                "Financial Year Incentive:",
                emp.financial_year_incentive or 0.0
            )
            print(
                "Total Income:",
                emp.total_income or 0.0
            )
            print(
                "Annual Income Used:",
                annual_income
            )
            print(
                "Standard Deduction:",
                emp.standard_deduction or 0.0
            )
            print(
                "Total Deduction:",
                deduction
            )
            print(
                "Net Taxable Income:",
                max(
                    annual_income - deduction,
                    0.0
                )
            )
            print("====================================================")

    @api.onchange('tax_regime')
    def _onchange_tax_regime(self):
        """Automatically update standard deduction based on selected regime."""
        if self.tax_regime == 'old':
            self.standard_deduction = 50000
            self.section_80c = 0.0
            self.section_80d = 0.0
            self.section_80g = 0.0
            self.nps = 0.0
            self.home_loan_interest = 0.0
        elif self.tax_regime == 'new':
            self.standard_deduction = 75000
        else:
            self.standard_deduction = 0.0

    @api.depends('net_taxable_income', 'tax_regime')
    def _compute_tds_amount(self):
        for emp in self:
            taxable_income = emp.net_taxable_income or 0.0
            tds = 0.0

            if emp.tax_regime == 'old':
                if taxable_income <= 250000:
                    # No tax up to ₹2.5L
                    tds = 0.0
                elif taxable_income <= 500000:
                    # 5% on income exceeding ₹2.5L
                    tds = (taxable_income - 250000) * 0.05
                elif taxable_income <= 1000000:
                    # ₹12,500 + 20% on income exceeding ₹5L
                    tds = 12500 + (taxable_income - 500000) * 0.20
                else:
                    # ₹1,12,500 + 30% on income exceeding ₹10L
                    tds = 112500 + (taxable_income - 1000000) * 0.30

                    # Add 4% Cess
                tds += tds * 0.04

            else:
                tds = 0.0  # No calculation for other regimes here

            emp.tds_amount = round(tds, 2)

            # @api.depends('tds_amount')

    # def _compute_tds_amount_month(self):
    #     for emp in self:
    #         emp.tds_amount_month = round((emp.tds_amount or 0.0) / 12.0, 2)

    @api.depends(
        'tds_amount',
        'tds_till_last_month',
        'payslip_month'
    )
    def _compute_tds_amount_month(self):
        for emp in self:

            month = int(emp.payslip_month or 0)

            if not month:
                emp.tds_amount_month = 0.0
                continue

            if month >= 4:
                remaining_months = 16 - month
            else:
                remaining_months = 4 - month

            remaining_months = max(remaining_months, 1)

            remaining_tax = max(
                (emp.tds_amount or 0.0)
                - (emp.tds_till_last_month or 0.0),
                0.0
            )

            emp.tds_amount_month = round(
                remaining_tax / remaining_months,
                2
            )
            # ---------------------------------------------------------

    # TDS - New Regime
    # ---------------------------------------------------------
    @api.depends('net_taxable_income', 'tax_regime')
    def _compute_tds_amount_new(self):
        for emp in self:
            print("\n")
            print("=" * 70)
            print("TDS AMOUNT NEW CALCULATION START")
            print("Employee:", emp.name)
            print("Employee ID:", emp.id)
            print("=" * 70)

            taxable_income = emp.net_taxable_income or 0.0
            tds = 0.0

            print("Original Net Taxable Income:", taxable_income)
            print("Tax Regime:", emp.tax_regime)

            if emp.tax_regime == 'new':

                # ---------------------------------------------------------
                # ROUND TOTAL INCOME BY ₹10
                # ---------------------------------------------------------
                rounded_taxable_income = float(
                    Decimal(str(taxable_income)).quantize(
                        Decimal('1E1'),
                        rounding=ROUND_HALF_UP
                    )
                )

                print("\n--- TAXABLE INCOME ROUNDING ---")
                print("Original Taxable Income:", taxable_income)
                print("Rounded Taxable Income:", rounded_taxable_income)

                taxable_income_for_tax = rounded_taxable_income

                # ---------------------------------------------------------
                # TAX SLAB CALCULATION
                # ---------------------------------------------------------

                if taxable_income_for_tax <= 400000:
                    tds = 0.0

                elif taxable_income_for_tax <= 800000:
                    tds = (
                                  taxable_income_for_tax - 400000
                          ) * 0.05

                elif taxable_income_for_tax <= 1200000:
                    tds = (
                            (400000 * 0.05)
                            + (taxable_income_for_tax - 800000) * 0.10
                    )

                elif taxable_income_for_tax <= 1600000:
                    tds = (
                            (400000 * 0.05)
                            + (400000 * 0.10)
                            + (taxable_income_for_tax - 1200000) * 0.15
                    )

                elif taxable_income_for_tax <= 2000000:
                    tds = (
                            (400000 * 0.05)
                            + (400000 * 0.10)
                            + (400000 * 0.15)
                            + (taxable_income_for_tax - 1600000) * 0.20
                    )

                elif taxable_income_for_tax <= 2400000:
                    tds = (
                            (400000 * 0.05)
                            + (400000 * 0.10)
                            + (400000 * 0.15)
                            + (400000 * 0.20)
                            + (taxable_income_for_tax - 2000000) * 0.25
                    )

                else:
                    tds = (
                            (400000 * 0.05)
                            + (400000 * 0.10)
                            + (400000 * 0.15)
                            + (400000 * 0.20)
                            + (400000 * 0.25)
                            + (taxable_income_for_tax - 2400000) * 0.30
                    )

                print("\n--- TAX SLAB RESULT ---")
                print("Taxable Income Used For Tax:", taxable_income_for_tax)
                print("Tax Before Rebate:", tds)

                # ---------------------------------------------------------
                # REBATE
                # ---------------------------------------------------------

                rebate_relief = 0.0

                if taxable_income_for_tax <= 1200000:
                    rebate_relief = tds
                    tds = 0.0

                print("\n--- REBATE RESULT ---")
                print("Rebate Relief:", rebate_relief)
                print("Tax After Rebate:", tds)

                # ---------------------------------------------------------
                # SURCHARGE
                # ---------------------------------------------------------

                surcharge = 0.0

                if taxable_income_for_tax > 5000000 and taxable_income_for_tax <= 10000000:
                    surcharge = tds * 0.10

                elif taxable_income_for_tax > 10000000 and taxable_income_for_tax <= 20000000:
                    surcharge = tds * 0.15

                elif taxable_income_for_tax > 20000000 and taxable_income_for_tax <= 50000000:
                    surcharge = tds * 0.25

                elif taxable_income_for_tax > 50000000:
                    surcharge = tds * 0.25

                emp.surcharge_amount = round(surcharge, 2)

                print("\n--- SURCHARGE RESULT ---")
                print("Surcharge:", surcharge)

                # ---------------------------------------------------------
                # ADD SURCHARGE
                # ---------------------------------------------------------

                tds += surcharge

                print("Tax After Surcharge:", tds)

                # ---------------------------------------------------------
                # MARGINAL RELIEF
                # ---------------------------------------------------------

                marginal_relief = 0.0

                print("\n--- MARGINAL RELIEF CALCULATION ---")
                print("Taxable Income Used:", taxable_income_for_tax)
                print(
                    "Marginal Relief Condition:",
                    1200000 < taxable_income_for_tax <= 1260000
                )

                if 1200000 < taxable_income_for_tax <= 1260000:

                    excess_income = taxable_income_for_tax - 1200000

                    print("Excess Income Above 12L:", excess_income)
                    print("Tax Before Marginal Relief:", tds)

                    if tds > excess_income:

                        marginal_relief = tds - excess_income
                        tds = excess_income

                        print(
                            "Marginal Relief Applied:",
                            marginal_relief
                        )

                        print(
                            "Tax After Marginal Relief:",
                            tds
                        )

                    else:
                        print(
                            "Marginal Relief NOT Applied - "
                            "Tax is not greater than excess income"
                        )

                else:
                    print(
                        "Marginal Relief NOT APPLIED - "
                        "Taxable income is outside 12L-12.6L range"
                    )

                # ---------------------------------------------------------
                # TOTAL RELIEF
                # ---------------------------------------------------------

                emp.relief_amount = round(
                    rebate_relief + marginal_relief,
                    2
                )

                print("\n--- FINAL RELIEF RESULT ---")
                print("Rebate Relief:", rebate_relief)
                print("Marginal Relief:", marginal_relief)
                print("TOTAL RELIEF AMOUNT:", emp.relief_amount)

                # ---------------------------------------------------------
                # CESS
                # ---------------------------------------------------------

                cess = tds * 0.04

                print("\n--- CESS CALCULATION ---")
                print("Tax Before Cess:", tds)
                print("Cess 4%:", cess)

                tds += cess

                print("Final TDS Including Cess:", tds)

            else:
                tds = 0.0
                emp.surcharge_amount = 0.0
                emp.relief_amount = 0.0

                print("\n--- NON NEW REGIME ---")
                print("TDS:", tds)
                print("Relief:", emp.relief_amount)

            emp.tds_amount_new = round(tds, 2)

            print("\n" + "=" * 70)
            print("FINAL TDS RESULT")
            print("Employee:", emp.name)
            print("Original Taxable Income:", taxable_income)
            print("Taxable Income Used For Tax:", taxable_income_for_tax if emp.tax_regime == 'new' else 0.0)
            print("Relief Amount:", emp.relief_amount)
            print("Surcharge Amount:", emp.surcharge_amount)
            print("TDS Amount New:", emp.tds_amount_new)
            print("=" * 70)
            print("\n")

            # @api.depends('tds_amount_new')

    # def _compute_tds_amount_new_month(self):
    #     for emp in self:
    #         emp.tds_amount_new_month = round((emp.tds_amount_new or 0.0) / 12, 2)

    @api.depends(
        'tds_amount_new',
        'tds_till_last_month',
        'payslip_month',
        'payslip_paid_days',
        'contract_date_start',
        'wage',
        'payslip_gross_wage',
        'annual_tds_base',
    )
    def _compute_tds_amount_new_month(self):
        for emp in self:

            print("\n")
            print("=" * 70)
            print("TDS AMOUNT NEW REGIME MONTH CALCULATION START")
            print("Employee:", emp.name)
            print("Employee ID:", emp.id)
            print("=" * 70)

            month = int(
                emp.payslip_month or 0
            )

            print("Payslip Month:", month)

            if not month:
                emp.tds_amount_new_month = 0.0

                print("No Payslip Month")
                print("Monthly TDS: 0.0")
                print("=" * 70)

                continue

            # ---------------------------------------
            # Existing Remaining Months Logic
            # ---------------------------------------

            if month >= 4:
                remaining_months = 16 - month
            else:
                remaining_months = 4 - month

            remaining_months = max(
                remaining_months,
                1
            )

            print("\n--- EXISTING REMAINING MONTHS LOGIC ---")
            print("Payslip Month:", month)
            print("Remaining Months:", remaining_months)

            joining_date = (
                emp.contract_date_start
            )

            print("\n--- JOINING DATE ---")
            print("Joining Date:", joining_date)

            # ---------------------------------------
            # Existing Annual TDS Logic
            # ---------------------------------------

            if (
                    joining_date
                    and joining_date.day > 1
                    and emp.annual_tds_base
                    and month == joining_date.month
            ):
                annual_tds = (
                    emp.annual_tds_base
                )

                print("\n--- ANNUAL TDS BASE ---")
                print("New Joiner - Joining Month")
                print("Using Annual TDS Base:", annual_tds)

            else:
                annual_tds = (
                        emp.tds_amount_new
                        or 0.0
                )

                print("\n--- ANNUAL TDS ---")
                print("Using TDS Amount New:", annual_tds)

                print("\n--- ANNUAL TDS ---")
                print("Using TDS Amount New:", annual_tds)

            # ---------------------------------------
            # Existing Remaining Tax Logic
            # ---------------------------------------

            remaining_tax = max(
                annual_tds
                - (
                        emp.tds_till_last_month
                        or 0.0
                ),
                0.0
            )

            print("\n--- REMAINING TAX CALCULATION ---")
            print("Annual TDS:", annual_tds)
            print(
                "TDS Till Last Month:",
                emp.tds_till_last_month or 0.0
            )
            print("Remaining Tax:", remaining_tax)

            monthly_tds = (
                    remaining_tax
                    / remaining_months
            )

            print("\n--- MONTHLY TDS BEFORE PRORATION ---")
            print("Remaining Tax:", remaining_tax)
            print("Remaining Months:", remaining_months)
            print("Monthly TDS:", monthly_tds)

            # ---------------------------------------
            # Prorate TDS for New Joiner
            # ---------------------------------------

            joining_date = (
                emp.contract_date_start
            )

            if (
                    joining_date
                    and joining_date.month == month
                    and joining_date.day > 1
                    and abs(
                (emp.wage or 0.0)
                - (
                        emp.payslip_gross_wage
                        or 0.0
                )
            ) > 0.01
            ):
                total_days = calendar.monthrange(
                    joining_date.year,
                    joining_date.month
                )[1]

                paid_days = (
                        emp.payslip_paid_days
                        or total_days
                )

                print("\n--- NEW JOINER PRORATION ---")
                print("Joining Date:", joining_date)
                print("Joining Month:", joining_date.month)
                print("Payslip Month:", month)
                print("Total Days:", total_days)
                print("Paid Days:", paid_days)
                print("Monthly TDS Before Proration:", monthly_tds)

                monthly_tds = (
                                      monthly_tds * paid_days
                              ) / total_days

                print("Monthly TDS After Proration:", monthly_tds)

            else:
                print("\n--- NEW JOINER PRORATION NOT APPLIED ---")

            # ---------------------------------------
            # Existing rounding logic
            # ---------------------------------------

            emp.tds_amount_new_month = round(
                monthly_tds
            )

            print("\n" + "=" * 70)
            print("FINAL MONTHLY TDS RESULT")
            print("Employee:", emp.name)
            print("Employee ID:", emp.id)
            print("Annual TDS:", annual_tds)
            print(
                "TDS Till Last Month:",
                emp.tds_till_last_month or 0.0
            )
            print("Remaining Tax:", remaining_tax)
            print("Remaining Months:", remaining_months)
            print("Monthly TDS Before Rounding:", monthly_tds)
            print(
                "TDS Amount New Regime (Month):",
                emp.tds_amount_new_month
            )
            print("=" * 70)
            print("\n")

    def write(self, vals):

        res = super().write(vals)

        if 'wage' in vals:

            for employee in self:
                print("Salary Changed")

                employee.financial_year_incentive = 0.0

                # Recompute Annual TDS
                employee._compute_tds_amount()

                # Recompute Monthly TDS
                employee._compute_tds_amount_month()

        return res

    variable_pay = fields.Monetary(string="Variable Pay")
    variable_bonus = fields.Monetary(string="Bonus")
    basic_arrear = fields.Monetary(string="Basic Arrear")
    hra_arrear = fields.Monetary(string="HRA Arrear")
    special_allowance_arrear = fields.Monetary(string="Special Allowance Arrear")
    fixed_stipend = fields.Monetary(string="Fixed Stipend")
    stipend = fields.Monetary(string="Stipend")
    stipend_arrear = fields.Monetary(string="Stipend Arrear")
    employee_incentive = fields.Monetary(string="Incentive")
    referral_incentive = fields.Monetary(string="Referral Incentive")
    notice_period = fields.Monetary(string="Notice Period Pay")
    salary_arrear = fields.Monetary(string="Salary Arrear")
    # leave_encashment = fields.Monetary(string="Leave Encashment")
    hold_salary = fields.Monetary(string="Hold Salary")
    other_earnings = fields.Monetary(string="Other Earnings")

    notice_pay_deduction = fields.Monetary("Notice Pay Deduction")
    loan_deduction = fields.Monetary("Loan")
    pf_arrear = fields.Monetary("PF Arrear")
    other_deductions = fields.Monetary("Other Deductions")

    loan_amount = fields.Float(string="Loan Amount")

    loan_interest = fields.Float(
        string="Interest %",
        default=0.0
    )

    loan_months = fields.Integer(
        string="No of Installments"
    )

    monthly_installment = fields.Float(
        string="Monthly Installment",
        compute="_compute_monthly_installment",
        store=True
    )

    total_payable_amount = fields.Float(
        string="Total Payable",
        compute="_compute_total_payable",
        store=True
    )

    remaining_balance = fields.Float(
        string="Remaining Balance",
        compute="_compute_remaining_balance",
        store=True
    )

    paid_installments = fields.Integer(
        string="Paid Installments",
        default=0
    )

    @api.depends('loan_amount', 'loan_interest')
    def _compute_total_payable(self):
        for emp in self:
            interest_amt = (
                                   (emp.loan_amount or 0.0)
                                   * (emp.loan_interest or 0.0)
                           ) / 100

            emp.total_payable_amount = (
                    (emp.loan_amount or 0.0)
                    + interest_amt
            )

    @api.depends('total_payable_amount', 'loan_months')
    def _compute_monthly_installment(self):
        for emp in self:

            if emp.loan_months:
                emp.monthly_installment = (
                        emp.total_payable_amount
                        / emp.loan_months
                )
            else:
                emp.monthly_installment = 0.0

    @api.depends(
        'total_payable_amount',
        'monthly_installment',
        'paid_installments'
    )
    def _compute_remaining_balance(self):
        for emp in self:
            paid_amount = (
                    emp.monthly_installment
                    * emp.paid_installments
            )

            balance = (
                    emp.total_payable_amount
                    - paid_amount
            )

            emp.remaining_balance = max(balance, 0.0)

            # Privilege Leave Allocation

    def cron_allocate_privilege_leave(self):

        current_year = fields.Date.today().year

        leave_type = self.env['hr.leave.type'].search([
            ('name', '=', 'Privilege Leave')
        ], limit=1)

        if not leave_type:
            return

        employees = self.search([
            ('date_of_confirmation', '!=', False),
        ])

        for emp in employees:

            if emp.pl_allocation_year == current_year:
                continue

            confirmation_date = fields.Date.to_date(
                emp.date_of_confirmation
            )

            # First year allocation
            if confirmation_date.year == current_year:

                leave_days = 12 - confirmation_date.month + 1

                if emp.probation_date_start and emp.probation_date_end:
                    probation_start = fields.Date.to_date(
                        emp.probation_date_start
                    )

                    probation_end = fields.Date.to_date(
                        emp.probation_date_end
                    )

                    probation_months = (
                            (probation_end.year - probation_start.year) * 12
                            + probation_end.month
                            - probation_start.month
                            + 1
                    )

                    leave_days += probation_months

                    # Every year after confirmation
            else:
                leave_days = 12

            self.env['hr.leave.allocation'].create({
                'name': f'Privilege Leave {current_year}',
                'employee_id': emp.id,
                'holiday_status_id': leave_type.id,
                'number_of_days': leave_days,
            })

            emp.pl_allocation_year = current_year

            # Casual and Sick Leave Allocation

    def cron_allocate_monthly_cl_sl(self):

        today = fields.Date.today()
        current_month = today.strftime('%Y-%m')

        casual_leave = self.env['hr.leave.type'].search([
            ('name', '=', 'Casual Leave')
        ], limit=1)

        sick_leave = self.env['hr.leave.type'].search([
            ('name', '=', 'Sick Leave')
        ], limit=1)

        if not casual_leave or not sick_leave:
            return

        employees = self.search([])

        for emp in employees:

            allocate_leave = True

            # ==========================
            # Probation Employees
            # ==========================
            if (
                    emp.probation_date_start
                    and emp.probation_date_end
            ):

                probation_start = fields.Date.to_date(
                    emp.probation_date_start
                )

                probation_end = fields.Date.to_date(
                    emp.probation_date_end
                )

                # Probation period-la month start date
                if (
                        probation_start <= today <= probation_end
                        and today.day == 1
                ):
                    allocate_leave = True

                    # ==========================
            # Confirmation Day Credit
            # ==========================
            if emp.date_of_confirmation:

                confirmation_date = fields.Date.to_date(
                    emp.date_of_confirmation
                )

                # Confirm aana day
                if today == confirmation_date:
                    allocate_leave = True

                    # Already confirmed employee
                elif (
                        confirmation_date < today
                        and today.day == 1
                ):
                    allocate_leave = True

                    # ==========================
            # Allocate CL
            # ==========================
            if (
                    allocate_leave
                    and emp.last_cl_allocation_month != current_month
            ):
                self.env['hr.leave.allocation'].create({
                    'name': f'CL {current_month}',
                    'employee_id': emp.id,
                    'holiday_status_id': casual_leave.id,
                    'number_of_days': 1,
                    # 'state': 'validate',
                })

                emp.last_cl_allocation_month = current_month

                # ==========================
            # Allocate SL
            # ==========================
            if (
                    allocate_leave
                    and emp.last_sl_allocation_month != current_month
            ):
                self.env['hr.leave.allocation'].create({
                    'name': f'SL {current_month}',
                    'employee_id': emp.id,
                    'holiday_status_id': sick_leave.id,
                    'number_of_days': 1,
                    # 'state': 'validate',
                })

                emp.last_sl_allocation_month = current_month

                # Bereavement Leave

    def cron_allocate_bereavement_leave(self):

        current_year = fields.Date.today().year

        leave_type = self.env['hr.leave.type'].search([
            ('name', '=', 'Bereavement Leave')
        ], limit=1)

        if not leave_type:
            return

        employees = self.search([
            ('date_of_confirmation', '!=', False),
        ])

        for emp in employees:

            # Already allocated this year
            if emp.bereavement_allocation_year == current_year:
                continue

            confirmation_date = fields.Date.to_date(
                emp.date_of_confirmation
            )

            # Employee should already be confirmed
            if confirmation_date > fields.Date.today():
                continue

            self.env['hr.leave.allocation'].create({
                'name': f'Bereavement Leave {current_year}',
                'employee_id': emp.id,
                'holiday_status_id': leave_type.id,
                'number_of_days': 6,
            })

            emp.bereavement_allocation_year = current_year

    def cron_allocate_probation_sick_leave(self):

        today = fields.Date.today()

        # Sick Leave Type
        leave_type = self.env['hr.leave.type'].search([
            ('name', '=', 'Sick Leave - Probation')
        ], limit=1)

        if not leave_type:
            return

            # Employees currently under probation
        employees = self.search([
            ('probation_date_start', '!=', False),
            ('probation_date_end', '!=', False),
            ('probation_date_start', '<=', today),
            ('probation_date_end', '>=', today),
        ])

        for emp in employees:

            start_date = fields.Date.to_date(emp.probation_date_start)

            # Allocate only on the probation start day of every month
            if today.day != start_date.day:
                continue

                # Prevent duplicate allocation in the same month
            existing = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', emp.id),
                ('holiday_status_id', '=', leave_type.id),
            ], limit=1)

            if existing:
                continue

            allocation = self.env['hr.leave.allocation'].create({
                'name': f'Sick Leave - Probation ({today.strftime("%B %Y")})',
                'employee_id': emp.id,
                'holiday_status_id': leave_type.id,
                'number_of_days': 1,
            })

            # Odoo 19
            # allocation.action_validate()

    def cron_allocate_probation_casual_leave(self):

        today = fields.Date.today()

        leave_type = self.env['hr.leave.type'].search([
            ('name', '=', 'Casual Leave - Probation')
        ], limit=1)

        if not leave_type:
            return

        employees = self.search([
            ('probation_date_start', '!=', False),
            ('probation_date_end', '!=', False),
            ('probation_date_start', '<=', today),
            ('probation_date_end', '>=', today),
        ])

        for emp in employees:

            probation_start = fields.Date.to_date(
                emp.probation_date_start
            )

            probation_end = fields.Date.to_date(
                emp.probation_date_end
            )

            # Calculate probation months
            probation_months = (
                    (probation_end.year - probation_start.year) * 12
                    + probation_end.month
                    - probation_start.month
            )

            allocations = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', emp.id),
                ('holiday_status_id', '=', leave_type.id),
            ])

            total_allocated = sum(
                allocations.mapped('number_of_days')
            )

            # =========================================
            # Probation <= 3 Months
            # Allocate 2 CL together
            # =========================================
            if probation_months <= 3:

                if total_allocated >= 2:
                    continue

                self.env['hr.leave.allocation'].create({
                    'name': 'Casual Leave - Probation (3 Months)',
                    'employee_id': emp.id,
                    'holiday_status_id': leave_type.id,
                    'number_of_days': 2,
                })

                # =========================================
            # Probation > 3 Months
            # Allocate Monthly 1 CL
            # =========================================
            else:

                # Allocate on same day every month
                if today.day != probation_start.day:
                    continue

                current_month = today.strftime('%Y-%m')

                existing = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', emp.id),
                    ('holiday_status_id', '=', leave_type.id),
                    ('name', '=', f'Casual Leave - Probation ({current_month})')
                ], limit=1)

                if existing:
                    continue

                self.env['hr.leave.allocation'].create({
                    'name': f'Casual Leave - Probation ({current_month})',
                    'employee_id': emp.id,
                    'holiday_status_id': leave_type.id,
                    'number_of_days': 1,
                })



