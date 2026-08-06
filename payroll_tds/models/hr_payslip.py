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

    state = fields.Selection(
        selection_add=[
            ('timeoff_balance', 'Time Off Balance')
        ]
    )

    state_display = fields.Selection(
        selection_add=[
            ('timeoff_balance', 'Time Off Balance')
        ]
    )

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

            if not tds_line:
                slip.state = 'timeoff_balance'
                continue

            pending_leave = self.env['hr.leave'].search([
                ('employee_id', '=', slip.employee_id.id),
                ('state', 'in', ['confirm']),
                ('request_date_from', '<=', slip.date_to),
                ('request_date_to', '>=', slip.date_from),
            ], limit=1)

            if pending_leave:

                slip.state = 'timeoff_balance'

                blocked_count += 1

                # Employee Manager
                manager = pending_leave.employee_id.parent_id

                if manager and manager.user_id and manager.user_id.email:
                    self.env['mail.mail'].sudo().create({
                        'subject': 'Pending Leave Approval',
                        'body_html': f"""
                            <p>Dear {manager.name},</p>
                                    <p>
                                        Employee <b>{slip.employee_id.name}</b>
                                        has a pending leave request.
                                    </p>
                                    <p>Kindly approve/reject before payroll validation.</p>
                                    <p>Thanks</p>
                                """,
                        'email_to': manager.user_id.email,
                    }).send()


                # Employee Mail
                employee_email = (
                        slip.employee_id.work_email
                        or slip.employee_id.user_id.email
                )

                if employee_email:

                    print("EMPLOYEE MAIL SENDING")

                    self.env['mail.mail'].sudo().create({
                        'subject': 'Pending Time Off Request',
                        'body_html': f"""
                            <p>Dear {slip.employee_id.name},</p>
                                    <p>Your Time Off request is still pending.</p>
                                    <p>Payslip moved to <b>Time Off Balance</b>.</p>
                                    <p>Thanks</p>
                                """,
                        'email_to': employee_email,
                    }).send()

            else:
                valid_slips |= slip

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

                # Recompute
                employee._compute_net_taxable_income()
                employee._compute_tds_amount()
                employee._compute_tds_amount_new()

                # Save Annual TDS only for new joiner (once)
                if (
                        employee.contract_date_start
                        and employee.contract_date_start.day > 1
                        and employee.contract_date_start.month == slip.date_from.month
                        and not employee.annual_tds_base
                ):
                    employee.annual_tds_base = employee.tds_amount_new

                # Compute Monthly TDS
                employee._compute_tds_amount_month()

            res = super(HrPayslip, valid_slips).action_payslip_done()


            for slip in valid_slips:

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
        if blocked_count:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Pending Time Off Leave Request',
                    'message': f'Blocked Payslips: {blocked_count}',
                    'sticky': True,
                    'type': 'warning',
                }
            }

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
