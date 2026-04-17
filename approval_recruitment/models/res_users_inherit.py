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
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        employee_url = f"{base_url}/web#id={employee.id}&model=hr.employee&view_type=form"

        mail_values = {
            'subject': "New Employee Created – Buddy Assignment Required",
            'body_html': f"""
                <p>Dear {manager.name},</p>

                <p>A new employee <b>{employee.name}</b> has been created in the system.</p>

                <p>You are assigned as the <b>Reporting Manager</b>.</p>

                <p>Please kindly assign a <b>Buddy</b> for the new employee.</p>

                <p>
                    <a href="{employee_url}" style="
                        display:inline-block;
                        padding:10px 18px;
                        background-color:#0a6ebd;
                        color:white;
                        text-decoration:none;
                        border-radius:4px;">
                        Open Employee Record
                    </a>
                </p>

                <p>Regards,<br/>HR Team</p>
            """,
            'email_from': employee.company_id.email or 'info@company.com',
            'email_to': manager.work_email,
        }

        self.env['mail.mail'].create(mail_values).send()
