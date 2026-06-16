from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    payslip_month = fields.Selection(
        related='employee_id.payslip_month',
        string='Payslip Month',
        readonly=True
    )

    payslip_gross_wage = fields.Monetary(
        related='employee_id.payslip_gross_wage',
        string='Payslip Gross Wage',
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



