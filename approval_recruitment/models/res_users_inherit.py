from odoo import models, api, _
from odoo.exceptions import ValidationError

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):

        employee_id = self.env.context.get('default_create_employee_id')

        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)

            # ✅ VALIDATION BEFORE CREATE
            if not employee.parent_id:
                raise ValidationError(_("Please assign a Reporting Manager before creating the user."))

        # Create user
        users = super().create(vals_list)

        # Post-create logic
        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)

            if not employee.user_id:
                employee.user_id = users[0].id

            manager = employee.parent_id
            if manager and manager.work_email:
                self._send_manager_mail(employee, manager)

        return users

    def _send_manager_mail(self, employee, manager):
        template = self.env.ref('approval_recruitment.email_template_manager_buddy_assign')

        template.send_mail(
            employee.id,
            force_send=True,
            email_values={
                'email_to': manager.work_email  # ✅ correct
            }
        )
        template.send_mail(
            employee.id,
            force_send=True,
            email_values={
                'email_to': manager.work_email,
                'partner_ids': [],
            }
        )
