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

    ifsc_code = fields.Char(
        string="IFSC Code",
        compute="_compute_bank_details",
    )

    account_number = fields.Char(
        string="Account Number",
        compute="_compute_bank_details",
    )

    @api.depends(
        "employee_id.bank_account_ids",
        "employee_id.bank_account_ids.bank_name",
        "employee_id.bank_account_ids.ls_ifsc_code",
        "employee_id.bank_account_ids.acc_number",
    )
    def _compute_bank_details(self):
        for rec in self:
            bank = rec.employee_id.bank_account_ids[:1]

            rec.bank_name = bank.bank_name if bank else ""
            rec.ifsc_code = bank.ls_ifsc_code if bank else ""
            rec.account_number = bank.acc_number if bank else ""


    basic = fields.Monetary(
        related='employee_id.l10n_in_basic_salary_amount',
        string='Basic',
        readonly=True
    )

    hra = fields.Monetary(
        related='employee_id.l10n_in_hra',
        string='HRA',
        readonly=True
    )

    special_allowance = fields.Monetary(
        related='employee_id.l10n_in_fixed_allowance',
        string='Special Allowance',
        readonly=True
    )

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
        related='employee_id.employee_incentive',
        string='Incentive',
        readonly=True
    )

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
        related='employee_id.l10n_in_pf_employee_amount',
        string='EPF Contribution',
        readonly=True
    )

    pt = fields.Float(
        string="PT",
    )

    @api.onchange("employee_id")
    def _onchange_pt(self):
        if self.employee_id.pt_rule_parameter_id and \
                self.employee_id.pt_rule_parameter_id.name == "Tamilnadu: Professional Tax":
            self.pt = 208.0

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

    total_deduction = fields.Monetary(
        string="Total Deduction",
        currency_field="currency_id",
        store=True,
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

    # @api.depends('payslip_gross_wage', 'net_wage')
    # def _compute_total_deduction(self):
    #     for rec in self:
    #         rec.total_deduction = (
    #                 (rec.payslip_gross_wage or 0.0)
    #                 - (rec.net_wage or 0.0)
    #         )

    @api.onchange(
        'epf_contribution',
        'pt',
        'income_tax',
        'other_deductions',
        'loan_deduction',
        'payslip_gross_wage',
        'net_wage'
    )
    def _onchange_total_deduction(self):
        for rec in self:

            deduction_sum = (
                    (rec.epf_contribution or 0.0)
                    + (rec.pt or 0.0)
                    + (rec.income_tax or 0.0)
                    + (rec.other_deductions or 0.0)
                    + (rec.loan_deduction or 0.0)
            )

            gross_net_diff = (
                    (rec.payslip_gross_wage or 0.0)
                    - (rec.net_wage or 0.0)
            )

            if not rec.total_deduction:
                if round(deduction_sum, 2) == round(gross_net_diff, 2):
                    rec.total_deduction = deduction_sum
                else:
                    rec.total_deduction = gross_net_diff

    payslip_month = fields.Selection(
        related='employee_id.payslip_month',
        string='Payslip Month',
        readonly=True
    )

    payslip_gross_wage = fields.Monetary(
        related='employee_id.payslip_gross_wage',
        string='Total Gross Earnings',
        readonly=True
    )

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

    @api.depends('worked_days_line_ids.number_of_days', 'worked_days_line_ids.code')
    def _compute_attendance_days(self):
        for rec in self:
            rec.attendance_days = sum(
                line.number_of_days
                for line in rec.worked_days_line_ids
                if line.code == 'WORK100'
            )

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

        valid_slips = self.env['hr.payslip']
        blocked_count = 0

        for slip in self:

            # 1. FORCE MONTH FROM PAYSLIP DATE
            if slip.date_from:
                month = slip.date_from.month
                slip.employee_id.write({
                    'payslip_month': str(month),
                })

            # 2. GROSS WAGE FROM EMPLOYEE (NO contract_id)
            gross = slip.employee_id.payslip_gross_wage or 0.0

            slip.employee_id.write({
                'payslip_gross_wage': gross,
            })

            # 3. GET ANNUAL SALARY (IMPORTANT CHECK FIRST)
            annual_salary = slip.employee_id.payslip_yearly_cost or 0.0

            # 🚀 SKIP instead of error
            if annual_salary <= 1200000:
                valid_slips |= slip
                continue

            # 3. COMPUTE SHEET FIRST
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
        if valid_slips:
            super(HrPayslip, valid_slips).action_payslip_done()
            res = super(HrPayslip, valid_slips).action_payslip_done()
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
            loan_exists = any(line.code == 'LOAN' for line in slip.line_ids)

            if loan_exists:
                slip.employee_id.paid_installments = (
                                                             slip.employee_id.paid_installments or 0
                                                     ) + 1

        return res



