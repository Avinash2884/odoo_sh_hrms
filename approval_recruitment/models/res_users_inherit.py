from odoo import models, api, _
from odoo.exceptions import ValidationError

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):

        # Create user normally
        users = super().create(vals_list)

        # Get employee from context
        employee_id = self.env.context.get('default_create_employee_id')

        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)

            # Link user (only if not already linked)
            if not employee.user_id:
                employee.user_id = users[0].id

            # Send mail
            manager = employee.parent_id
            if manager and manager.work_email:
                self._send_manager_mail(employee, manager)

        return users

    def _send_manager_mail(self, employee, manager):
        template = self.env.ref('approval_recruitment.email_template_manager_buddy_assign')

        email_to = employee.work_email

        template.send_mail(
            employee.id,
            force_send=True,
            email_values={
                'email_to': email_to
            }
        )
