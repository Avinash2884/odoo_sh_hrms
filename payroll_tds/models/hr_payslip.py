import calendar
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee Name',
    )

    pay_register_no = fields.Char(string="Pay Register No")
    pay_register_date = fields.Date(string="Pay Register Date")

    pay_period = fields.Char(
        string="Pay Period",
        compute="_compute_pay_period",
        store=True,
    )

    @api.depends('date_from')
    def _compute_pay_period(self):
        for rec in self:
            if rec.date_from:
                rec.pay_period = rec.date_from.strftime('%B %Y')
            else:
                rec.pay_period = ''

    dob_display = fields.Char(
        string='DOB',
        compute='_compute_display_dates'
    )

    date_of_joining_display = fields.Char(
        string='Date of Joining',
        compute='_compute_display_dates'
    )

    date_of_leaving_display = fields.Char(
        string='Date of Leaving',
        compute='_compute_display_dates'
    )

    @api.depends(
        'employee_id.birthday',
        'employee_id.contract_date_start',
        'employee_id.contract_date_end'
    )
    def _compute_display_dates(self):
        for rec in self:
            rec.dob_display = (
                rec.employee_id.birthday.strftime('%d/%m/%Y')
                if rec.employee_id.birthday else ''
            )

            rec.date_of_joining_display = (
                rec.employee_id.contract_date_start.strftime('%d/%m/%Y')
                if rec.employee_id.contract_date_start else ''
            )

            rec.date_of_leaving_display = (
                rec.employee_id.contract_date_end.strftime('%d/%m/%Y')
                if rec.employee_id.contract_date_end else ''
            )

    job_position_id = fields.Many2one(
        'hr.job',
        related='employee_id.job_id',
        string='Designation',
        readonly=True
    )

    gender = fields.Selection(
        related='employee_id.sex',
        string='Gender',
        readonly=True
    )

    # dob = fields.Date(
    #     related='employee_id.birthday',
    #     string='DOB',
    #     readonly=True
    # )

    department_id = fields.Many2one(
        'hr.department',
        related='employee_id.department_id',
        string='Department',
        readonly=True
    )

    pan = fields.Char(
        related='employee_id.l10n_in_pan',
        string='PAN',
        readonly=True
    )

    uan = fields.Char(
        related='employee_id.l10n_in_uan',
        string='UAN',
        readonly=True
    )

    state_id = fields.Many2one(
        'res.country.state',
        related='employee_id.private_state_id',
        string='Employee State',
        readonly=True
    )

    city = fields.Char(
        related='employee_id.private_city',
        string='City',
        readonly=True
    )

    salary_type_id = fields.Many2one(
        'hr.payroll.structure.type',
        related='employee_id.structure_type_id',
        string='Salary Type',
        readonly=True
    )

    bank_name = fields.Char(
        string="Bank Name",
        compute="_compute_bank_details",
    )
    #
    ifsc_code = fields.Char(
        string="IFSC Code",
        compute="_compute_bank_details",
    )

    account_number = fields.Char(
        string="Account Number",
        compute="_compute_bank_details",
    )

    # @api.depends(
    #     "employee_id.bank_account_ids",
    #     "employee_id.bank_account_ids.bank_name",
    #     "employee_id.bank_account_ids.ls_ifsc_code",
    #     "employee_id.bank_account_ids.acc_number",
    # )
    # def _compute_bank_details(self):
    #     for rec in self:
    #         bank = rec.employee_id.bank_account_ids[:1]
    #
    #         rec.bank_name = bank.bank_name if bank else ""
    #         rec.ifsc_code = bank.ls_ifsc_code if bank else ""
    #         rec.account_number = bank.acc_number if bank else ""

    basic = fields.Monetary(
        string="Basic",
        compute="_compute_basic_salary",
        currency_field="currency_id",
        store=True,
    )

    @api.depends('line_ids.total', 'line_ids.code')
    def _compute_basic_salary(self):
        for slip in self:
            basic_line = slip.line_ids.filtered(lambda l: l.code == 'BASIC')[:1]
            slip.basic = basic_line.total if basic_line else 0.0

    hra = fields.Monetary(
        string="HRA",
        compute="_compute_hra",
        currency_field="currency_id",
        store=True,
    )

    @api.depends('line_ids.total', 'line_ids.code')
    def _compute_hra(self):
        for slip in self:
            hra_line = slip.line_ids.filtered(lambda l: l.code == 'HRA')[:1]
            slip.hra = hra_line.total if hra_line else 0.0

    special_allowance = fields.Monetary(
        string="Special Allowance",
        compute="_compute_special_allowance",
        currency_field="currency_id",
        store=True,
    )

    @api.depends('line_ids.total', 'line_ids.code')
    def _compute_special_allowance(self):
        for slip in self:
            special_line = slip.line_ids.filtered(lambda l: l.code == 'SPI')[:1]
            slip.special_allowance = special_line.total if special_line else 0.0

    conveyance_allowance = fields.Monetary(
        string="Conveyance Allowance",
        compute="_compute_conveyance_allowance",
        currency_field="currency_id",
        store=True,
    )

    @api.depends('line_ids.total', 'line_ids.code')
    def _compute_conveyance_allowance(self):
        for slip in self:
            ca_line = slip.line_ids.filtered(lambda l: l.code == 'CA')[:1]
            slip.conveyance_allowance = ca_line.total if ca_line else 0.0

    salary_arrear_amount = fields.Monetary(
        string="Salary Arrear",
        compute="_compute_salary_arrear",
        currency_field="currency_id",
        store=True,
    )

    @api.depends('line_ids.total', 'line_ids.code')
    def _compute_salary_arrear(self):
        for slip in self:
            arrear_line = slip.line_ids.filtered(
                lambda l: l.code == 'SAP1'
            )[:1]
            slip.salary_arrear_amount = arrear_line.total if arrear_line else 0.0

    stipend = fields.Monetary(
        related='employee_id.stipend',
        string='Stipend',
        readonly=True
    )

    bonus = fields.Monetary(
        related='employee_id.variable_bonus',
        string='Bonus',
        readonly=True
    )

    incentive = fields.Monetary(
        string="Incentive",
        compute="_compute_incentive",
        currency_field="currency_id",
        store=True,
    )

    @api.depends('line_ids.total', 'line_ids.code')
    def _compute_incentive(self):
        for slip in self:
            incentive_line = slip.line_ids.filtered(
                lambda l: l.code == 'IN'
            )[:1]
            slip.incentive = incentive_line.total if incentive_line else 0.0

    other_earnings = fields.Monetary(
        string="Other Earnings",
        compute="_compute_other_earnings",
        currency_field="currency_id",
        store=True,
    )

    @api.depends('line_ids.total', 'line_ids.code')
    def _compute_other_earnings(self):
        for slip in self:
            other_line = slip.line_ids.filtered(
                lambda l: l.code == 'OE'
            )[:1]
            slip.other_earnings = other_line.total if other_line else 0.0


    hold_salary = fields.Monetary(
        string="Hold Salary",
        compute="_compute_hold_salary",
        currency_field="currency_id",
        store=True,
    )

    @api.depends('line_ids.total', 'line_ids.code')
    def _compute_hold_salary(self):
        for slip in self:
            hold_line = slip.line_ids.filtered(
                lambda l: l.code == 'HS'
            )[:1]
            slip.hold_salary = hold_line.total if hold_line else 0.0


    variable_pay = fields.Monetary(
        string="Variable Pay",
        compute="_compute_variable_pay",
        currency_field="currency_id",
        store=True,
    )

    @api.depends('line_ids.total', 'line_ids.code')
    def _compute_variable_pay(self):
        for slip in self:
            variable_line = slip.line_ids.filtered(
                lambda l: l.code == 'VP'
            )[:1]
            slip.variable_pay = variable_line.total if variable_line else 0.0


    pf_arrear = fields.Monetary(
        string="PF Arrear",
        compute="_compute_pf_arrear",
        currency_field="currency_id",
        store=True,
    )

    @api.depends('line_ids.total', 'line_ids.code')
    def _compute_pf_arrear(self):
        for slip in self:
            pf_arrear_line = slip.line_ids.filtered(
                lambda l: l.code == 'PFA'
            )[:1]
            slip.pf_arrear = pf_arrear_line.total if pf_arrear_line else 0.0


    nps_contribution = fields.Monetary(
        string="NPS Contribution",
        compute="_compute_nps_contribution",
        currency_field="currency_id",
        store=True,
    )

    @api.depends('line_ids.total', 'line_ids.code')
    def _compute_nps_contribution(self):
        for slip in self:
            nps_line = slip.line_ids.filtered(
                lambda l: l.code == 'NPS'
            )[:1]
            slip.nps_contribution = nps_line.total if nps_line else 0.0

    referral = fields.Monetary(
        related='employee_id.referral_incentive',
        string='Referral',
        readonly=True
    )

    leave_encashment = fields.Monetary(
        related='employee_id.leave_encashment',
        string='Leave Encashment',
        readonly=False,
        store=True,
    )

    notice_pay = fields.Monetary(
        related='employee_id.notice_period',
        string='Notice Pay',
        readonly=False,
        store=True,
    )

    other_deductions = fields.Monetary(
        related='employee_id.other_deductions',
        string='Other Deductions',
        readonly=True
    )

    gross = fields.Monetary(
        related='employee_id.wage',
        string='Fixed Monthly Earnings',
        readonly=True
    )

    epf_contribution = fields.Monetary(
        string="EPF Contribution",
        compute="_compute_epf_contribution",
        currency_field="currency_id",
        store=True,
    )

    @api.depends('line_ids.total', 'line_ids.code')
    def _compute_epf_contribution(self):
        for slip in self:
            pf_line = slip.line_ids.filtered(
                lambda l: l.code == 'PF'
            )[:1]
            slip.epf_contribution = abs(pf_line.total) if pf_line else 0.0

    pt = fields.Monetary(
        string="PT",
        compute="_compute_pt",
        currency_field="currency_id",
        store=True,
    )

    @api.depends('line_ids.total', 'line_ids.code')
    def _compute_pt(self):
        for slip in self:
            pt_line = slip.line_ids.filtered(
                lambda l: l.code == 'PT'
            )[:1]
            slip.pt = abs(pt_line.total) if pt_line else 0.0

            # pt = fields.Float(

    #     string="PT",
    # )

    # @api.onchange("employee_id")
    # def _onchange_pt(self):
    #     if self.employee_id.pt_rule_parameter_id and \
    #             self.employee_id.pt_rule_parameter_id.name == "Tamilnadu: Professional Tax":
    #         self.pt = 208.0

    pt_previous_deducted = fields.Float(
        string="Previous Half-Year PT",
        copy=False,
    )

    def _calculate_previous_pt(self):

        for slip in self:

            slip.pt_previous_deducted = 0.0

            if not slip.date_from:
                continue

            month = slip.date_from.month
            year = slip.date_from.year

            # April - September half year
            if 4 <= month <= 9:

                start_date = fields.Date.from_string(
                    f"{year}-04-01"
                )

                # October - March half year
            else:

                if month >= 10:
                    start_date = fields.Date.from_string(
                        f"{year}-10-01"
                    )
                else:
                    start_date = fields.Date.from_string(
                        f"{year - 1}-10-01"
                    )

            previous_slips = self.env['hr.payslip'].search([
                ('employee_id', '=', slip.employee_id.id),
                ('state', 'in', ['done', 'paid']),
                ('date_from', '>=', start_date),
                ('date_from', '<', slip.date_from),
            ])

            previous_pt = 0.0

            for prev in previous_slips:
                pt_line = prev.line_ids.filtered(
                    lambda x: x.code == 'PT'
                )

                previous_pt += abs(
                    sum(pt_line.mapped('total'))
                )

            slip.write({
                'pt_previous_deducted': previous_pt
            })

    def compute_sheet(self):

        for slip in self:
            slip._calculate_previous_pt()

        return super().compute_sheet()

    income_tax = fields.Float(
        string="Income Tax",
        compute="_compute_income_tax",
        store=True
    )

    loan_deduction = fields.Monetary(
        related='employee_id.loan_deduction',
        string='Loan Deduction',
        readonly=True
    )

    # total_deduction = fields.Monetary(
    #     string="Total Deduction",
    #     currency_field="currency_id",
    #     store=True,
    # )
    total_deduction = fields.Monetary(
        string="Total Deduction",
        compute="_compute_total_deduction",
        currency_field="currency_id",
        store=True,
    )

    @api.depends('line_ids.total', 'line_ids.category_id')
    def _compute_total_deduction(self):
        for slip in self:
            slip.total_deduction = sum(
                abs(line.total)
                for line in slip.line_ids
                if line.category_id.code == 'DED'
            )

    net_wage = fields.Monetary(
        string="Net Pay",
        currency_field="currency_id",
    )

    @api.depends(
        'employee_id.tds_amount_new_month',
        'employee_id.tds_amount_month'
    )
    def _compute_income_tax(self):
        for rec in self:
            rec.income_tax = (
                    rec.employee_id.tds_amount_new_month
                    or rec.employee_id.tds_amount_month
                    or 0.0
            )

            # @api.onchange(

    #     'epf_contribution',
    #     'pt',
    #     'income_tax',
    #     'other_deductions',
    #     'loan_deduction',
    #     'payslip_gross_wage',
    #     'net_wage'
    # )
    # def _onchange_total_deduction(self):
    #     for rec in self:
    #
    #         deduction_sum = (
    #                 (rec.epf_contribution or 0.0)
    #                 + (rec.pt or 0.0)
    #                 + (rec.income_tax or 0.0)
    #                 + (rec.other_deductions or 0.0)
    #                 + (rec.loan_deduction or 0.0)
    #         )
    #
    #         gross_net_diff = (
    #                 (rec.payslip_gross_wage or 0.0)
    #                 - (rec.net_wage or 0.0)
    #         )
    #
    #         if not rec.total_deduction:
    #             if round(deduction_sum, 2) == round(gross_net_diff, 2):
    #                 rec.total_deduction = deduction_sum
    #             else:
    #                 rec.total_deduction = gross_net_diff

    payslip_month = fields.Selection(
        related='employee_id.payslip_month',
        string='Payslip Month',
        readonly=True
    )

    payslip_gross_wage = fields.Monetary(
        string="Total Gross Earnings",
        currency_field="currency_id",
        compute="_compute_payslip_gross_wage",
        store=True
    )

    @api.depends('line_ids.total', 'line_ids.code')
    def _compute_payslip_gross_wage(self):
        for slip in self:
            gross_line = slip.line_ids.filtered(lambda l: l.code == 'GROSS')[:1]
            slip.payslip_gross_wage = gross_line.total if gross_line else 0.0

    total_period_days = fields.Integer(
        string='Working Days',
        compute='_compute_total_period_days',
        store=True
    )

    unpaid_days = fields.Float(
        string="LOP",
        compute="_compute_unpaid_days",
        store=True,
    )

    attendance_days = fields.Float(
        string="Paid Days",
        compute="_compute_attendance_days",
        store=True,
    )

    # state = fields.Selection(
    #     selection_add=[
    #         ('timeoff_balance', 'Time Off Balance')
    #     ]
    # )
    #
    # state_display = fields.Selection(
    #     selection_add=[
    #         ('timeoff_balance', 'Time Off Balance')
    #     ]
    # )

    @api.depends('date_from', 'date_to')
    def _compute_total_period_days(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                rec.total_period_days = (
                                                rec.date_to - rec.date_from
                                        ).days + 1
            else:
                rec.total_period_days = 0

                # @api.depends('worked_days_line_ids.number_of_days', 'worked_days_line_ids.code')

    # def _compute_attendance_days(self):
    #     for rec in self:
    #         rec.attendance_days = sum(
    #             line.number_of_days
    #             for line in rec.worked_days_line_ids
    #             if line.code == 'WORK100'
    #         )

    @api.depends(
        'date_from',
        'date_to',
        'employee_id.joining_date_recruit',
        'unpaid_days'
    )
    def _compute_attendance_days(self):
        for rec in self:

            rec.attendance_days = 0.0

            if not rec.date_from or not rec.date_to:
                continue

            total_days = (rec.date_to - rec.date_from).days + 1
            joining_date = rec.employee_id.joining_date_recruit

            if joining_date:

                # Joined after payslip period
                if joining_date > rec.date_to:
                    eligible_days = 0

                # Joined during payslip period
                elif rec.date_from <= joining_date <= rec.date_to:
                    eligible_days = (rec.date_to - joining_date).days + 1

                # Joined before payslip period
                else:
                    eligible_days = total_days

            else:
                eligible_days = total_days

            paid_days = eligible_days - (rec.unpaid_days or 0)

            rec.attendance_days = max(paid_days, 0)

    @api.depends('worked_days_line_ids.number_of_days', 'worked_days_line_ids.work_entry_type_id')
    def _compute_unpaid_days(self):
        for rec in self:
            rec.unpaid_days = sum(
                line.number_of_days
                for line in rec.worked_days_line_ids
                if line.work_entry_type_id.code == 'LEAVE90'
            )

    # ---------------------------------------------------------
    # Disable automatic payslip email during validation
    # ---------------------------------------------------------
    def _generate_pdf(self):
        """
        Generate the payslip PDF without sending any email.

        Odoo's standard hr_payroll _generate_pdf() generates the
        PDF and then automatically sends the payslip email.
        Email sending is intentionally disabled here.
        """
        # Original Odoo mail-sending code is intentionally disabled.
        #
        # The standard Odoo method contains logic similar to:
        #
        # template.send_mail(
        #     payslip.id,
        #     email_layout_xmlid='mail.mail_notification_light'
        # )
        #
        # We intentionally do NOT call super()._generate_pdf()
        # because it would trigger the automatic payslip email.

        return True

    def action_payslip_done(self):

        if self.env.context.get('install_demo'):
            return super().action_payslip_done()

            #
        # for slip in valid_slips:
        #
        #     fy_start = slip.date_from
        #
        #     if fy_start.month >= 4:
        #         fy_start = fy_start.replace(month=4, day=1)
        #     else:
        #         fy_start = fy_start.replace(
        #             year=fy_start.year - 1,
        #             month=4,
        #             day=1
        #         )
        #
        #     previous_slips = self.env['hr.payslip'].search([
        #         ('employee_id', '=', slip.employee_id.id),
        #         ('state', '=', 'done'),
        #         ('date_from', '>=', fy_start),
        #         ('date_to', '<', slip.date_from),
        #     ])
        #
        #     total_tds = 0.0
        #
        #     for pslip in previous_slips:
        #         tds_line = pslip.line_ids.filtered(
        #             lambda l: l.code in ('TDS', 'TDS_NEW')
        #         )
        #         total_tds += abs(sum(tds_line.mapped('total')))
        #
        #     # Store previous months TDS
        #     slip.employee_id.write({
        #         'tds_till_last_month': total_tds
        #     })
        #
        #     # Recompute monthly TDS immediately
        #     slip.employee_id._compute_tds_amount_month()

        valid_slips = self.env['hr.payslip']
        blocked_count = 0

        for slip in self:

            # 1. FORCE MONTH FROM PAYSLIP DATE
            if slip.date_from:
                month = slip.date_from.month

                # 2. GROSS WAGE FROM EMPLOYEE (NO contract_id)
            gross = slip.employee_id.payslip_gross_wage or 0.0
            slip.employee_id.write({
                'payslip_month': str(month),
                'payslip_gross_wage': gross,
                'payslip_paid_days': slip.attendance_days,
            })

            # 3. GET ANNUAL SALARY (IMPORTANT CHECK FIRST)

            annual_salary = slip.employee_id.payslip_yearly_cost or 0.0

            # 🚀 SKIP instead of error
            if annual_salary <= 1200000:
                valid_slips |= slip
                continue

                # 3. COMPUTE SHEET FIRST
            # Calculate previous PT first

            slip.compute_sheet()

            # 4. TDS CHECK (IMPORTANT FIX)
            tds_line = slip.line_ids.filtered(
                lambda l: l.code in ['TDS', 'TDS_NEW']
            )

            # Time Off Balance functionality disabled
            valid_slips |= slip

            # if not tds_line:
            #     slip.state = 'timeoff_balance'
            #     continue
            #
            # pending_leave = self.env['hr.leave'].search([
            #     ('employee_id', '=', slip.employee_id.id),
            #     ('state', 'in', ['confirm']),
            #     ('request_date_from', '<=', slip.date_to),
            #     ('request_date_to', '>=', slip.date_from),
            # ], limit=1)
            #
            # if pending_leave:
            #
            #     slip.state = 'timeoff_balance'
            #
            #     blocked_count += 1
            #
            #     # Employee Manager
            #     manager = pending_leave.employee_id.parent_id
            #
            #     if manager and manager.user_id and manager.user_id.email:
            #         self.env['mail.mail'].sudo().create({
            #             'subject': 'Pending Leave Approval',
            #             'body_html': f"""
            #                 <p>Dear {manager.name},</p>
            #                         <p>
            #                             Employee <b>{slip.employee_id.name}</b>
            #                             has a pending leave request.
            #                         </p>
            #                         <p>Kindly approve/reject before payroll validation.</p>
            #                         <p>Thanks</p>
            #                     """,
            #             'email_to': manager.user_id.email,
            #         }).send()
            #
            #
            #     # Employee Mail
            #     employee_email = (
            #             slip.employee_id.work_email
            #             or slip.employee_id.user_id.email
            #     )
            #
            #     if employee_email:
            #
            #         print("EMPLOYEE MAIL SENDING")
            #
            #         self.env['mail.mail'].sudo().create({
            #             'subject': 'Pending Time Off Request',
            #             'body_html': f"""
            #                 <p>Dear {slip.employee_id.name},</p>
            #                         <p>Your Time Off request is still pending.</p>
            #                         <p>Payslip moved to <b>Time Off Balance</b>.</p>
            #                         <p>Thanks</p>
            #                     """,
            #             'email_to': employee_email,
            #         }).send()
            #
            # else:
            #     valid_slips |= slip

        # Validate only valid payslips
        # if valid_slips:
        #     super(HrPayslip, valid_slips).action_payslip_done()
        #     res = super(HrPayslip, valid_slips).action_payslip_done()
        # else:
        #     res = True

        if valid_slips:

            for slip in valid_slips:
                employee = slip.employee_id

                # Refresh cached values
                employee.invalidate_recordset([
                    'net_taxable_income',
                    'tds_amount',
                ])

                employee._compute_net_taxable_income()
                employee._compute_tds_amount()
                employee._compute_tds_amount_new()

                gap_month_tds = self._get_gap_month_tds(slip)

                if gap_month_tds is not None:
                    # -------------------------------------------------
                    # GAP MONTH + CURRENT MONTH LOP
                    # Store the specially calculated monthly TDS
                    # -------------------------------------------------
                    employee.write({
                        'tds_amount_new_month': gap_month_tds
                    })

                else:
                    # -------------------------------------------------
                    # NORMAL TDS CALCULATION
                    # Existing logic remains unchanged
                    # -------------------------------------------------
                    employee._compute_tds_amount_month()

                # -----------------------------------------------------
                # IMPORTANT:
                # Recompute payslip AFTER tds_amount_new_month is set.
                #
                # The TDS salary rule reads the employee's monthly TDS
                # value during compute_sheet().
                # -----------------------------------------------------
                slip.compute_sheet()

                # Save Annual TDS only for new joiner (once)
                if (
                        employee.contract_date_start
                        and employee.contract_date_start.day > 1
                        and employee.contract_date_start.month == slip.date_from.month
                        and not employee.annual_tds_base
                ):
                    employee.annual_tds_base = employee.tds_amount_new

            res = super(HrPayslip, valid_slips).action_payslip_done()

            for slip in valid_slips:

                slip.employee_id._update_financial_year_incentive(
                    slip
                )

                fy_start = slip.date_from

                if fy_start.month >= 4:
                    fy_start = fy_start.replace(month=4, day=1)
                else:
                    fy_start = fy_start.replace(
                        year=fy_start.year - 1,
                        month=4,
                        day=1
                    )

                previous_slips = self.env['hr.payslip'].search([
                    ('employee_id', '=', slip.employee_id.id),
                    ('id', '!=', slip.id),
                    ('state', 'in', ['done', 'paid']),
                    ('date_from', '>=', fy_start),
                    ('date_to', '<', slip.date_from),
                ])

                total_previous_tds = 0

                for prev in previous_slips:
                    tds_line = prev.line_ids.filtered(
                        lambda l: l.code == 'TDS'
                    )

                    total_previous_tds += abs(
                        sum(tds_line.mapped('total'))
                    )

                slip.employee_id.write({
                    'tds_till_last_month': total_previous_tds
                })

                slip.employee_id._compute_tds_amount_month()

        else:
            res = True

            # Notification only
        # if blocked_count:
        #     return {
        #         'type': 'ir.actions.client',
        #         'tag': 'display_notification',
        #         'params': {
        #             'title': 'Pending Time Off Leave Request',
        #             'message': f'Blocked Payslips: {blocked_count}',
        #             'sticky': True,
        #             'type': 'warning',
        #         }
        #     }

        return res

    def action_print_payslip(self):
        return self.env.ref(
            'l10n_in_hr_payroll.payslip_details_report'
        ).report_action(self)

    def action_print_fnf_report(self):
        return self.env.ref(
            'payroll_tds.action_report_fnf'
        ).report_action(self)

    def action_payslip_paid(self):
        res = super().action_payslip_paid()

        for slip in self:

            employee = slip.employee_id

            # -----------------------------
            # Reset only for first payslip of new FY (April)
            # -----------------------------
            if slip.date_from.month == 4:
                employee.tds_till_last_month = 0.0

            if slip.date_from.month == 4:
                employee.annual_tds_base = 0.0

                # -----------------------------

            # Get current month's TDS
            # -----------------------------
            tds_line = slip.line_ids.filtered(
                lambda l: l.code == 'TDS'
            )

            current_tds = abs(sum(tds_line.mapped('total')))

            # -----------------------------
            # Store cumulative TDS
            # -----------------------------
            employee.write({
                'tds_till_last_month': employee.tds_till_last_month + current_tds
            })

            # -----------------------------
            # Recompute next month's TDS
            # -----------------------------
            # employee._compute_tds_amount_month()

        # Loan Logic
        for slip in self:
            if any(line.code == 'LOAN' for line in slip.line_ids):
                slip.employee_id.paid_installments += 1

        return res

    def _get_missing_payroll_months(self, slip):
        employee = slip.employee_id

        # Financial year start
        if slip.date_from.month >= 4:
            fy_start = slip.date_from.replace(
                month=4,
                day=1
            )
        else:
            fy_start = slip.date_from.replace(
                year=slip.date_from.year - 1,
                month=4,
                day=1
            )

        # Previous completed/paid payslips
        previous_slips = self.env['hr.payslip'].search([
            ('employee_id', '=', employee.id),
            ('id', '!=', slip.id),
            ('state', 'in', ['done', 'paid']),
            ('date_from', '>=', fy_start),
            ('date_to', '<', slip.date_from),
        ])

        paid_months = set()

        for prev in previous_slips:
            # Consider the month as paid only when the payslip
            # actually has gross earnings.
            gross_wage = sum(
                prev.line_ids.filtered(
                    lambda l: l.code == 'GROSS'
                ).mapped('total')
            )

            if gross_wage > 0:
                paid_months.add(
                    prev.date_from.strftime('%Y-%m')
                )

        # Find months between FY start and current month
        missing_months = []

        check_date = fy_start

        while check_date < slip.date_from:

            month_key = check_date.strftime('%Y-%m')

            if month_key not in paid_months:
                missing_months.append(month_key)

            if check_date.month == 12:
                check_date = check_date.replace(
                    year=check_date.year + 1,
                    month=1,
                    day=1
                )
            else:
                check_date = check_date.replace(
                    month=check_date.month + 1,
                    day=1
                )

        return missing_months

    def _has_current_month_lop(self, slip):

        total_days = (
                             slip.date_to - slip.date_from
                     ).days + 1

        paid_days = slip.attendance_days or 0.0

        return paid_days < total_days

    def _get_gap_month_tds(self, slip):
        """
        Special TDS handling only when:
        1. Current payslip has LOP
        2. One or more previous payroll months are missing

        Returns None for normal employees/months so the existing
        TDS calculation continues unchanged.
        """

        # Current month must have LOP
        if not self._has_current_month_lop(slip):
            return None

        # Check missing payroll months
        missing_months = self._get_missing_payroll_months(slip)

        if not missing_months:
            return None

        employee = slip.employee_id

        print("\n" + "=" * 70)
        print("GAP MONTH + LOP TDS CALCULATION")
        print("Employee:", employee.name)
        print("Current Month:", slip.date_from)
        print("Missing Months:", missing_months)
        print("Paid Days:", slip.attendance_days)
        print("LOP Days:", slip.unpaid_days)
        print("=" * 70)

        # -------------------------------------------------
        # Existing annual TDS
        # -------------------------------------------------
        annual_tds = employee.tds_amount_new or 0.0

        # -------------------------------------------------
        # TDS already deducted before current payslip
        # -------------------------------------------------
        previous_tds = employee.tds_till_last_month or 0.0

        remaining_tds = max(
            annual_tds - previous_tds,
            0.0
        )

        # -------------------------------------------------
        # Remaining payroll months INCLUDING current month
        #
        # IMPORTANT:
        # Missing previous months are NOT removed here.
        #
        # Missing months have already contributed ₹0 income.
        # Current month through March still has to be distributed
        # across all remaining payroll months.
        # -------------------------------------------------

        current_month = slip.date_from.month
        if current_month >= 4:
            remaining_months = 16 - current_month
        else:
            remaining_months = 4 - current_month

        remaining_months = max(
            remaining_months,
            1
        )

        # -------------------------------------------------
        # Normal monthly TDS
        # -------------------------------------------------
        normal_month_tds = (
            remaining_tds / remaining_months
            if remaining_months
            else 0.0
        )

        # -------------------------------------------------
        # Current month proration
        # -------------------------------------------------
        total_days = (
                             slip.date_to - slip.date_from
                     ).days + 1

        paid_days = slip.attendance_days or 0.0

        current_month_tds = (
            normal_month_tds * paid_days / total_days
            if total_days
            else 0.0
        )

        current_month_tds = round(current_month_tds)

        print("--- GAP TDS RESULT ---")
        print("Annual TDS:", annual_tds)
        print("Previous TDS:", previous_tds)
        print("Remaining TDS:", remaining_tds)
        print("Missing Months:", missing_months)
        print("Remaining Months:", remaining_months)
        print("Normal Monthly TDS:", normal_month_tds)
        print("Total Days:", total_days)
        print("Paid Days:", paid_days)
        print("LOP Days:", slip.unpaid_days)
        print("Current Month TDS:", current_month_tds)
        print("=" * 70)

        return current_month_tds

    # # ==========================================================================
    # # TDS SHEET - added on top of existing code (nothing above this line
    # # was changed). Visible only when the employee has a Tax Regime set.
    # # ==========================================================================
    #
    # tax_regime = fields.Selection(
    #     related='employee_id.tax_regime',
    #     string='Tax Regime',
    #     readonly=True,
    # )
    #
    # def action_print_tds_sheet(self):
    #     return self.env.ref(
    #         'payroll_tds.action_report_tds_sheet'
    #     ).report_action(self)
    #
    # def get_tds_sheet_values(self):
    #     """
    #     Build every value needed for the TDS Sheet report.
    #
    #     IMPORTANT: this method only READS already-computed / stored
    #     fields from hr.employee and hr.payslip. It never recalculates
    #     TDS from scratch. This guarantees the number printed on the
    #     TDS Sheet always matches:
    #       - payslip.income_tax        (what THIS payslip deducted)
    #       - employee.tds_amount_new   (annual TDS - new regime)
    #       - employee.tds_amount       (annual TDS - old regime)
    #     """
    #     self.ensure_one()
    #
    #     emp = self.employee_id
    #
    #     # -----------------------------------------------------
    #     # Remaining months - SAME formula as
    #     # employee._compute_tds_amount_new_month()
    #     # -----------------------------------------------------
    #     month = int(self.date_from.month) if self.date_from else 0
    #
    #     if month >= 4:
    #         remaining_months = 16 - month
    #     else:
    #         remaining_months = 4 - month
    #     remaining_months = max(remaining_months, 1)
    #
    #     # months still left AFTER this current payslip month
    #     future_months = max(remaining_months - 1, 0)
    #
    #     # -----------------------------------------------------
    #     # 1) GROSS EARNINGS  (Actual / Projection / Total)
    #     # -----------------------------------------------------
    #     basic_actual = self.basic or 0.0
    #     hra_actual = self.hra or 0.0
    #     sa_actual = self.special_allowance or 0.0
    #
    #     basic_projection = (emp.l10n_in_basic_salary_amount or 0.0) * future_months
    #     hra_projection = (emp.l10n_in_hra or 0.0) * future_months
    #     # NOTE: there is no separate "monthly Special Allowance" field
    #     # stored on hr.employee today, so this assumes the current
    #     # payslip's Special Allowance repeats every remaining month.
    #     # Confirm this assumption / adjust if you have a better source.
    #     sa_projection = sa_actual * future_months
    #
    #     gross_earnings = {
    #         'basic': {
    #             'actual': basic_actual,
    #             'projection': basic_projection,
    #             'total': basic_actual + basic_projection,
    #         },
    #         'hra': {
    #             'actual': hra_actual,
    #             'projection': hra_projection,
    #             'total': hra_actual + hra_projection,
    #         },
    #         'special_allowance': {
    #             'actual': sa_actual,
    #             'projection': sa_projection,
    #             'total': sa_actual + sa_projection,
    #         },
    #     }
    #
    #     total_income_row = {
    #         'actual': basic_actual + hra_actual + sa_actual,
    #         'projection': basic_projection + hra_projection + sa_projection,
    #         'total': sum(v['total'] for v in gross_earnings.values()),
    #     }
    #
    #     # -----------------------------------------------------
    #     # 2) Allowance exempt under Section 10 - not tracked -> 0
    #     #    (add a field later if you start tracking this)
    #     # -----------------------------------------------------
    #     section_10_exempt = 0.0
    #     total_after_exemption = total_income_row['total'] - section_10_exempt
    #
    #     # -----------------------------------------------------
    #     # 4) Previous employment income
    #     # -----------------------------------------------------
    #     prev_income_after_exemption = emp.previous_employment_income or 0.0
    #     prev_professional_tax = emp.previous_employment_professional_tax or 0.0
    #     prev_employment_total = prev_income_after_exemption + prev_professional_tax
    #
    #     # -----------------------------------------------------
    #     # 5) Gross Total (3 + 4)
    #     # -----------------------------------------------------
    #     gross_total = total_after_exemption + prev_employment_total
    #
    #     # -----------------------------------------------------
    #     # 6) Section 19 deductions
    #     # -----------------------------------------------------
    #     entertainment_allowance = emp.entertainment_allowance or 0.0
    #     tax_on_employment = emp.tax_on_employment or 0.0
    #     standard_deduction = emp.standard_deduction or 0.0
    #     section_19_total = (
    #         entertainment_allowance
    #         + tax_on_employment
    #         + standard_deduction
    #     )
    #
    #     # -----------------------------------------------------
    #     # 7) Income Chargeable Under Salaries (5 - 6)
    #     # -----------------------------------------------------
    #     income_chargeable_salaries = gross_total - section_19_total
    #
    #     # -----------------------------------------------------
    #     # 8) Other income reported - not tracked -> 0
    #     # -----------------------------------------------------
    #     other_income = 0.0
    #
    #     # -----------------------------------------------------
    #     # 9) Gross Total Income (7 + 8)
    #     # -----------------------------------------------------
    #     gross_total_income = income_chargeable_salaries + other_income
    #
    #     # -----------------------------------------------------
    #     # 10) Chapter VI-A deductions (Old regime only)
    #     # -----------------------------------------------------
    #     chapter_via_total = 0.0
    #     if emp.tax_regime == 'old':
    #         chapter_via_total = (
    #             (emp.section_80c or 0.0)
    #             + (emp.section_80d or 0.0)
    #             + (emp.section_80g or 0.0)
    #             + (emp.nps or 0.0)
    #             + (emp.section_123_80ccc or 0.0)
    #             + (emp.section_124_1_80ccd_1 or 0.0)
    #             + (emp.section_124_1b_80ccd_1b or 0.0)
    #             + (emp.section_126_80d or 0.0)
    #             + (emp.section_127_80dd or 0.0)
    #             + (emp.section_128_80ddb or 0.0)
    #             + (emp.section_129_80e or 0.0)
    #             + (emp.section_130_80ee or 0.0)
    #             + (emp.section_131_80eea or 0.0)
    #             + (emp.section_132_80eeb or 0.0)
    #             + (emp.section_133_80g or 0.0)
    #             + (emp.section_134_80gg or 0.0)
    #             + (emp.section_137_80ggc or 0.0)
    #             + (emp.section_153_80tta or 0.0)
    #             + (emp.section_154_80u or 0.0)
    #             + min(emp.home_loan_interest or 0.0, 200000.0)
    #         )
    #
    #     # -----------------------------------------------------
    #     # 11) Total Income (9 - 10), rounded to nearest 10
    #     #     -> this is ALREADY emp.net_taxable_income, reused
    #     #        directly so nothing drifts from the real TDS calc.
    #     # -----------------------------------------------------
    #     net_taxable_income = emp.net_taxable_income or 0.0
    #
    #     # -----------------------------------------------------
    #     # 12) Tax slab breakdown
    #     # -----------------------------------------------------
    #     slab_lines = emp._get_tds_slab_breakdown()
    #     tax_on_total_income = sum(l['tax_amount'] for l in slab_lines)
    #
    #     rebate_amount = 0.0
    #     if emp.tax_regime == 'new' and net_taxable_income <= 1200000:
    #         rebate_amount = tax_on_total_income
    #
    #     # -----------------------------------------------------
    #     # 13) Surcharge / Relief / Cess (already stored)
    #     # -----------------------------------------------------
    #     surcharge_amount = emp.surcharge_amount or 0.0
    #     relief_amount = emp.relief_amount or 0.0
    #     cess_amount = round(
    #         (tax_on_total_income - rebate_amount + surcharge_amount) * 0.04,
    #         2,
    #     )
    #
    #     # -----------------------------------------------------
    #     # 14) Tax Payable (already stored, annual)
    #     # -----------------------------------------------------
    #     if emp.tax_regime == 'new':
    #         tax_payable = emp.tds_amount_new or 0.0
    #     else:
    #         tax_payable = emp.tds_amount or 0.0
    #
    #     # -----------------------------------------------------
    #     # 15) Tax Deducted at Source
    #     # -----------------------------------------------------
    #     tds_till_last_month = emp.tds_till_last_month or 0.0
    #
    #     # SAME value the payslip itself deducted this month
    #     # (hr_payslip._compute_income_tax) - guarantees match.
    #     tds_this_month = self.income_tax or 0.0
    #
    #     tds_previous_employer = 0.0  # not tracked separately yet
    #
    #     total_tds_deducted = (
    #         tds_till_last_month
    #         + tds_this_month
    #         + tds_previous_employer
    #     )
    #
    #     tax_payable_refundable = tax_payable - total_tds_deducted
    #
    #     remaining_months_after_current = max(remaining_months - 1, 1)
    #     tds_per_month_remaining = round(
    #         (tax_payable - total_tds_deducted) / remaining_months_after_current,
    #         2,
    #     )
    #
    #     return {
    #         'employee': emp,
    #         'payslip': self,
    #         'gross_earnings': gross_earnings,
    #         'total_income_row': total_income_row,
    #         'section_10_exempt': section_10_exempt,
    #         'total_after_exemption': total_after_exemption,
    #         'prev_income_after_exemption': prev_income_after_exemption,
    #         'prev_professional_tax': prev_professional_tax,
    #         'prev_employment_total': prev_employment_total,
    #         'gross_total': gross_total,
    #         'entertainment_allowance': entertainment_allowance,
    #         'tax_on_employment': tax_on_employment,
    #         'standard_deduction': standard_deduction,
    #         'section_19_total': section_19_total,
    #         'income_chargeable_salaries': income_chargeable_salaries,
    #         'other_income': other_income,
    #         'gross_total_income': gross_total_income,
    #         'chapter_via_total': chapter_via_total,
    #         'net_taxable_income': net_taxable_income,
    #         'slab_lines': slab_lines,
    #         'tax_on_total_income': tax_on_total_income,
    #         'rebate_amount': rebate_amount,
    #         'surcharge_amount': surcharge_amount,
    #         'cess_amount': cess_amount,
    #         'relief_amount': relief_amount,
    #         'tax_payable': tax_payable,
    #         'tds_till_last_month': tds_till_last_month,
    #         'tds_this_month': tds_this_month,
    #         'tds_previous_employer': tds_previous_employer,
    #         'total_tds_deducted': total_tds_deducted,
    #         'tax_payable_refundable': tax_payable_refundable,
    #         'tds_per_month_remaining': tds_per_month_remaining,
    #     }