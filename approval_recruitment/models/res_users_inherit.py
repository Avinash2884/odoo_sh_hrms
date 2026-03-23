from odoo import models, api, _
from odoo.exceptions import ValidationError

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def create(self, vals_list):

        employee_id = self.env.context.get('default_create_employee_id')
        employee = False

        # ---------------------------------
        # 1️⃣ Employee Validation
        # ---------------------------------
        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)

            if not employee.exists():
                raise ValidationError(_("Invalid Employee reference."))

            if not employee.parent_id:
                raise ValidationError(
                    _("Reporting Manager is not set for this Employee.")
                )

            if 'hr_id' in employee._fields and not employee.hr_id:
                raise ValidationError(
                    _("HR Manager is not set for this Employee.")
                )

        # ---------------------------------
        # 2️⃣ Prevent duplicate login
        # ---------------------------------
        for vals in vals_list:
            login = vals.get('login')

            if login:
                existing_user = self.search(
                    [('login', '=', login)], limit=1
                )

                if existing_user:
                    raise ValidationError(
                        _("User with this login already exists.")
                    )

        # ---------------------------------
        # 3️⃣ Create Users (default flow)
        # ---------------------------------
        users = super().create(vals_list)

        # ---------------------------------
        # 4️⃣ Send mail after success
        # ---------------------------------
        if employee:
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
