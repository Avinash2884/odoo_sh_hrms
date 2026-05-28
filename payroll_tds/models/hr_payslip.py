from odoo import models, fields


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

    def action_payslip_done(self):

        valid_slips = self.env['hr.payslip']
        blocked_count = 0

        for slip in self:

            employee = slip.employee_id

            annual_salary = employee.payslip_yearly_cost or 0.0

            applicable_tds = (
                employee.tds_amount_month
                if employee.tax_regime == 'old'
                else employee.tds_amount_new_month
            )

            if annual_salary > 1200000 and not applicable_tds:
                raise ValidationError(
                    f"TDS is applicable for employee {employee.name}.\n\n"
                    f"Please configure Monthly TDS before validating payslip."
                )

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
                    mail_values = {
                        'subject': 'Pending Leave Approval',
                        'body_html': f"""
                            <p>Dear {manager.name},</p>

                            <p>
                                Employee <b>{slip.employee_id.name}</b>
                                has a pending leave request which is still pending approval.
                            </p>

                            <p>
                                Please approve or reject the leave request before payroll validation.
                            </p>

                            <br/>
                            <p>Thanks</p>
                        """,
                        'email_to': manager.user_id.email,
                    }

                    self.env['mail.mail'].sudo().create(mail_values).send()

                # Employee Mail
                employee_email = (
                        slip.employee_id.work_email
                        or slip.employee_id.user_id.email
                )

                print("EMPLOYEE EMAIL:", employee_email)

                if employee_email:

                    print("EMPLOYEE MAIL SENDING")

                    employee_mail_values = {
                        'subject': 'Pending Time Off Request',
                        'body_html': f"""
                            <p>Dear {slip.employee_id.name},</p>

                            <p>
                                Your Time Off request is still pending approval.
                            </p>

                            <p>
                                Because of the pending request,
                                your payslip could not be validated
                                and moved to <b>Time Off Balance</b> state.
                            </p>

                            <p>
                                Kindly check with your reporting manager.
                            </p>

                            <br/>
                            <p>Thanks</p>
                        """,
                        'email_to': employee_email,
                    }

                    self.env['mail.mail'].sudo().create(
                        employee_mail_values
                    ).send()

                else:
                    print("NO EMPLOYEE EMAIL FOUND")

            else:
                valid_slips |= slip




        # Validate only valid payslips
        if valid_slips:
            super(HrPayslip, valid_slips).action_payslip_done()

        # Notification only
        if blocked_count:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Pending Time Off Leave Request',
                    'message': (
                        f'Count: {blocked_count}'
                    ),
                    'sticky': True,
                    'type': 'warning',
                }
            }

        return True

    def action_print_fnf_report(self):
        return self.env.ref(
            'payroll_tds.action_report_fnf'
        ).report_action(self)