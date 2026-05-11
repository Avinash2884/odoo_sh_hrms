from odoo import models, fields


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

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
        blocked_employees = []

        for slip in self:

            pending_leave = self.env['hr.leave'].search([
                ('employee_id', '=', slip.employee_id.id),
                ('state', 'in', ['confirm']),
                ('request_date_from', '<=', slip.date_to),
                ('request_date_to', '>=', slip.date_from),
            ], limit=1)

            if pending_leave:

                slip.state = 'timeoff_balance'

                blocked_employees.append(slip.employee_id.name)

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

            else:
                valid_slips |= slip

        # Validate only valid payslips
        if valid_slips:
            super(HrPayslip, valid_slips).action_payslip_done()

        # Notification only
        if blocked_employees:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Pending Leave Found',
                    'message': (
                        'Payslip skipped for:\n%s'
                        % ', '.join(blocked_employees)
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