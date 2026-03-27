from odoo import models, fields, api
from datetime import timedelta

from odoo.exceptions import UserError


class HrAppraisalInherit(models.Model):
    _inherit = 'hr.appraisal'

    manager_decision = fields.Selection([
        ('extension', 'Extension of Probation'),
        ('confirmation', 'Confirmation'),
    ], string="Manager Decision", tracking=True)

    probation_reason = fields.Text(string="Reason for Extension", help="Reason for probation extension", tracking=True)

    # ✅ Appraisal-level probation extension count
    probation_extension_count = fields.Integer(
        string="Probation Extension Count",
        default=0,
        help="Number of times probation has been extended in this appraisal"
    )

    employee_id = fields.Many2one('hr.employee', string="Employee")

    hr_id = fields.Many2one(
        'hr.employee',
        string="HR",
        related='employee_id.hr_id',
        store=True,
        readonly=True
    )

    @api.onchange('manager_decision')
    def _onchange_manager_decision(self):
        if self.manager_decision == 'extension':
            self.probation_reason = ''  # Ensure reason field available

    @api.model
    def write(self, vals):
        res = super(HrAppraisalInherit, self).write(vals)
        for record in self:
            if vals.get('state') == 'done':
                record.action_apply_decision()
        return res

    def action_apply_decision(self):
        """Apply the manager decision: extension or confirmation"""
        for record in self:
            if not record.employee_id:
                continue

            employee = record.employee_id
            contract = employee  # Odoo 19 uses employee fields directly

            today = fields.Date.today()
            hr = record.hr_id
            if not hr or not hr.work_email:
                raise UserError(f"HR email not configured for employee: {employee.name}")

            hr_email = hr.work_email

            if record.manager_decision == 'extension':
                # 🔹 Max 2 extensions check
                if record.probation_extension_count >= 2:
                    raise UserError(
                        f"Probation period for {employee.name} cannot be extended more than 2 times in this appraisal."
                    )

                # 🔹 Extend probation
                probation_start = today
                probation_end = probation_start + timedelta(days=30)

                # Update employee probation fields
                contract.probation_date_start = probation_start
                contract.date_end = probation_end
                contract.contract_type_id = self.env.ref('approval_recruitment.contract_type_probation')
                contract.probation_reason = record.probation_reason
                contract.probation_status = 'extended'

                # Increment appraisal-level count
                record.probation_extension_count += 1

                # 🔹 Mail to HR
                body = f"""
                <p>Dear {hr.name},</p>
                <p>Probation period for employee <b>{employee.name}</b> has been extended for 1 month.</p>
                <p><b>Reason:</b> {record.probation_reason}</p>
                <p><b>New contract end date:</b> {contract.date_end}</p>
                """

                self.env['mail.mail'].sudo().create({
                    'subject': "Probation Extended",
                    'body_html': body,
                    'email_to': hr_email,
                    'auto_delete': True,
                }).send()

            elif record.manager_decision == 'confirmation':
                # Confirm employee as permanent
                contract.contract_type_id = self.env.ref('hr.contract_type_permanent')
                contract.probation_date_start = today
                contract.date_end = False
                contract.probation_status = 'confirmed'
                contract.probation_reason = record.probation_reason

                # 🔹 Mail to HR
                body = f"""
                <p>Dear {hr.name},</p>
                <p>Employee <b>{employee.name}</b> has been confirmed as a permanent employee.</p>
                <p><b>Contract start date:</b> {contract.probation_date_start}</p>
                """

                self.env['mail.mail'].sudo().create({
                    'subject': "Employee Confirmed",
                    'body_html': body,
                    'email_to': hr_email,
                    'auto_delete': True,
                }).send()