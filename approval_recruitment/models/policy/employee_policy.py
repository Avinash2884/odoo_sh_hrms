from odoo import models, fields
from odoo.exceptions import ValidationError


class EmployeePolicy(models.Model):
    _name = 'employee.policy'
    _description = 'Employee Policy Document'
    _inherit = ['mail.thread']

    name = fields.Char("Policy Name")
    document = fields.Binary("Policy Document")
    file_name = fields.Char("File Name")
    active = fields.Boolean(default=True)

    is_acknowledged = fields.Boolean(
        "I Acknowledge",
        compute="_compute_is_acknowledged",
        inverse="_inverse_is_acknowledged"
    )

    # ---------------- COMPUTE ----------------
    def _compute_is_acknowledged(self):
        company_policy = self.env['company.policy']

        for rec in self:
            policy = company_policy.search([
                ('employee_policy_id', '=', rec.id)
            ], limit=1)

            rec.is_acknowledged = (
                self.env.user in policy.acknowledged_user_ids
                if policy else False
            )

    # ---------------- INVERSE ----------------
    def _inverse_is_acknowledged(self):
        for rec in self:

            company_policy = self.env['company.policy'].search([
                ('employee_policy_id', '=', rec.id)
            ], limit=1)

            if not company_policy:
                continue

            user = self.env.user

            already_ack = user in company_policy.acknowledged_user_ids

            # ❌ prevent uncheck
            if not rec.is_acknowledged and already_ack:
                raise ValidationError(
                    "You cannot unacknowledge once accepted."
                )

            # ✅ acknowledge flow
            if rec.is_acknowledged and not already_ack:
                company_policy.write({
                    'acknowledged_user_ids': [(4, user.id)]
                })

                user_time = fields.Datetime.context_timestamp(
                    self, fields.Datetime.now()
                )

                log_line = f"{user.name} - {user_time.strftime('%d-%m-%Y %I:%M %p')}\n"

                company_policy.acknowledged_log = (
                    (company_policy.acknowledged_log or "") + log_line
                )

    def write(self, vals):
        if 'active' in vals:
            # ✅ Allow only HR & Administrator
            if not self.env.user.has_group('approval_recruitment.group_policy_hr'):
                raise ValidationError(
                    "You are not allowed to archive or unarchive policies."
                )

        return super(EmployeePolicy, self).write(vals)