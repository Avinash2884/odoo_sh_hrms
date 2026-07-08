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

    tax_regime = fields.Selection([
        ('old', 'Old Regime'),
        ('new', 'New Regime'),
    ], string='Tax Regime')
    standard_deduction = fields.Monetary(string='Standard Deduction')
    section_80c = fields.Monetary(string='Section 80C', help="Available only under Old Regime")
    section_80d = fields.Monetary(string='Section 80D', help="Available only under Old Regime")
    section_80g = fields.Monetary(string='Section 80G', help="Available only under Old Regime")
    nps = fields.Monetary(string='NPS (80CCD(1B))', help="Available only under Old Regime")
    home_loan_interest = fields.Monetary(string='Home loan interest', help="Available only under Old Regime")
    net_taxable_income = fields.Monetary(
        string='Net Taxable Income',
        currency_field='currency_id',
        compute='_compute_net_taxable_income',
        store=True
    )
    tds_amount = fields.Monetary(
        string='TDS Amount (Annual)',
        currency_field='currency_id',
        compute='_compute_tds_amount',
        store=True
    )

    tds_amount_month = fields.Monetary(
        string='TDS Amount (Monthly)',
        currency_field='currency_id',
        compute='_compute_tds_amount_month',
        store=True
    )

    tds_amount_new = fields.Monetary(
        string='TDS Amount (New Regime)',
        currency_field='currency_id',
        compute='_compute_tds_amount_new',
        store=True
    )

    tds_amount_new_month = fields.Monetary(
        string='TDS Amount New Regime (Month)',
        currency_field='currency_id',
        compute='_compute_tds_amount_new_month',
        store=True
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
        'payslip_yearly_cost',
        'standard_deduction',
        'section_80c',
        'section_80d',
        'section_80g',
        'nps',
        'home_loan_interest',
        'tax_regime',
    )
    def _compute_net_taxable_income(self):
        for emp in self:
            annual_income = emp.payslip_yearly_cost or 0.0
            deduction = emp.standard_deduction or 0.0

            if emp.tax_regime == 'old':
                # Include all old regime deductions
                deduction += (
                        (emp.section_80c or 0.0)
                        + (emp.section_80d or 0.0)
                        + (emp.section_80g or 0.0)
                        + (emp.nps or 0.0)
                        + (emp.home_loan_interest or 0.0)
                )

            # Net taxable income = annual - total deductions
            emp.net_taxable_income = max(annual_income - deduction, 0.0)

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

    @api.depends('tds_amount')
    def _compute_tds_amount_month(self):

        Payslip = self.env['hr.payslip']

        for emp in self:

            annual_tds = emp.tds_amount or 0.0

            today = fields.Date.today()

            # Financial Year
            if today.month >= 4:
                fy_start = date(today.year, 4, 1)
            else:
                fy_start = date(today.year - 1, 4, 1)

            # Previous Payslips (Current Month exclude)
            payslips = Payslip.search([
                ('employee_id', '=', emp.id),
                ('state', 'in', ['done', 'paid']),
                ('date_from', '>=', fy_start),
                ('date_to', '<', date(today.year, today.month, 1)),
            ])

            previous_tds = 0.0

            for slip in payslips:
                tds_line = slip.line_ids.filtered(
                    lambda l: l.code == 'TDS'
                )

                previous_tds += sum(tds_line.mapped('total'))

            remaining_tax = max(
                annual_tds - previous_tds,
                0
            )

            # Remaining Months
            if today.month >= 4:
                remaining_months = 16 - today.month
            else:
                remaining_months = 4 - today.month

            if remaining_months:
                emp.tds_amount_month = round(
                    remaining_tax / remaining_months,
                    2
                )
            else:
                emp.tds_amount_month = remaining_tax

    @api.depends('net_taxable_income', 'tax_regime')
    def _compute_tds_amount_new(self):
        for emp in self:
            taxable_income = emp.net_taxable_income or 0.0
            tds = 0.0

            if emp.tax_regime == 'new':
                if taxable_income <= 400000:
                    tds = 0.0
                elif taxable_income <= 800000:
                    tds = (taxable_income - 400000) * 0.05
                elif taxable_income <= 1200000:
                    tds = (400000 * 0.05) + (taxable_income - 800000) * 0.10
                elif taxable_income <= 1600000:
                    tds = (400000 * 0.05) + (400000 * 0.10) + (taxable_income - 1200000) * 0.15
                elif taxable_income <= 2000000:
                    tds = (400000 * 0.05) + (400000 * 0.10) + (400000 * 0.15) + (taxable_income - 1600000) * 0.20
                elif taxable_income <= 2400000:
                    tds = (400000 * 0.05) + (400000 * 0.10) + (400000 * 0.15) + (400000 * 0.20) + (
                            taxable_income - 2000000) * 0.25
                else:
                    tds = (
                            (400000 * 0.05)
                            + (400000 * 0.10)
                            + (400000 * 0.15)
                            + (400000 * 0.20)
                            + (400000 * 0.25)
                            + (taxable_income - 2400000) * 0.30
                    )

                # rebate
                rebate_relief = 0.0

                if taxable_income <= 1200000:
                    rebate_relief = tds
                    tds = 0.0

                # Surcharge
                surcharge = 0.0

                if taxable_income > 5000000 and taxable_income <= 10000000:
                    surcharge = tds * 0.10

                elif taxable_income > 10000000 and taxable_income <= 20000000:
                    surcharge = tds * 0.15

                elif taxable_income > 20000000 and taxable_income <= 50000000:
                    surcharge = tds * 0.25

                elif taxable_income > 50000000:
                    surcharge = tds * 0.25  # New Regime

                emp.surcharge_amount = round(surcharge, 2)

                # Add surcharge
                tds += surcharge

                # Marginal Relief u/s 156(b)
                marginal_relief = 0.0

                if 1200000 < taxable_income <= 1260000:
                    excess_income = taxable_income - 1200000

                    if tds > excess_income:
                        marginal_relief = tds - excess_income
                        tds = excess_income

                emp.relief_amount = round(
                    rebate_relief + marginal_relief,
                    2
                )

                # Add 4% cess
                tds += tds * 0.04

            else:
                tds = 0.0
                emp.surcharge_amount = 0.0
                emp.relief_amount = 0.0

            emp.tds_amount_new = round(tds, 2)

    @api.depends('tds_amount_new')
    def _compute_tds_amount_new_month(self):
        for emp in self:
            emp.tds_amount_new_month = round((emp.tds_amount_new or 0.0) / 12, 2)

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