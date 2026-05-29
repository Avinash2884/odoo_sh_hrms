import re

from odoo import models, fields, api, _
from datetime import timedelta, date

from odoo.exceptions import ValidationError


class HrEmployeeInherit(models.Model):
    _inherit = 'hr.employee'
    _description = 'HR Employee'

    joining_date_recruit = fields.Date(string="Date of Joining", copy=False, tracking=True)
    date_of_confirmation = fields.Date(string="Date of Confirmation", copy=False, tracking=True)
    hr_id = fields.Many2one('hr.employee', 'HR',tracking=True)
    hr_head_id = fields.Many2one('hr.employee', 'HR Head',tracking=True)
    it_asset_head_id = fields.Many2one('hr.employee', 'IT Asset Head',tracking=True)
    admin_head_id = fields.Many2one('hr.employee', 'Admin Head',tracking=True)
    payroll_head_id = fields.Many2one('hr.employee', 'Payroll Head',tracking=True)

    probation_status = fields.Selection([
        ('extended', 'Extension of Probation'),
        ('confirmed', 'Confirmed Employee'),
    ], string="Probation Status", tracking=True)

    probation_reason = fields.Text(string="Probation Reason", tracking=True)
    probation_date_start = fields.Date(string="Probation Start Date",tracking=True)
    probation_date_end = fields.Date(string="Probation End Date",tracking=True)

    buddy_id = fields.Many2one('res.users', 'Buddy',tracking=True)
    ls_employee_id = fields.Char(string="Employee ID",tracking=True)
    hr_contract_type_id = fields.Many2one('hr.contract.type', 'Employment Type',tracking=True)
    entity_name_id = fields.Many2one('entity.name', 'Entity Name',tracking=True)
    base_location_id = fields.Many2one('base.location', 'Base Location',tracking=True)
    deputed_location_id = fields.Many2one('deputed.location', 'Deputed Location',tracking=True)
    band_id = fields.Many2one('band', 'Band',tracking=True)
    level_id = fields.Many2one('level', 'Level',tracking=True)
    vertical_id = fields.Many2one('vertical', 'Vertical',tracking=True)
    function_id = fields.Many2one('function', 'Function',tracking=True)
    parent_account_id = fields.Many2one('parent.account', 'Parent Account',tracking=True)
    account_office_name_id = fields.Many2one('account.office.name', 'Account/Office Name',tracking=True)
    region_id = fields.Many2one('region', 'Region',tracking=True)
    employee_status_id = fields.Many2one('employee.status', 'Employee Status',tracking=True)
    ls_designation_id = fields.Many2one('designation', 'Designation',tracking=True)
    ls_role_id = fields.Many2one('ls.role', 'Role',tracking=True)
    ls_source_of_hire_id = fields.Many2one('source.of.hire', 'Source of Hire',tracking=True)
    blood_group_id = fields.Many2one('blood.group', 'Blood Group',tracking=True)

    current_experience = fields.Integer(string="Current Experience",tracking=True)
    previous_experience = fields.Integer(string="Previous Experience",tracking=True)
    total_experience = fields.Integer(
        string="Total Experience",
        compute="_compute_total_experience",
        store=True,
        tracking=True
    )

    age = fields.Integer(string="Age", compute="_compute_age", store=True,tracking=True)
    guardian_type = fields.Selection([
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('guardian', 'Guardian'),
    ],tracking=True)

    # Father
    father_name = fields.Char("Father Name",tracking=True)
    father_mobile = fields.Char("Father Mobile",tracking=True)

    # Mother
    mother_name = fields.Char("Mother Name",tracking=True)
    mother_mobile = fields.Char("Mother Mobile",tracking=True)

    # Guardian
    guardian_relationship = fields.Char("Guardian Relationships",tracking=True)
    guardian_name = fields.Char("Guardian Name",tracking=True)
    guardian_mobile = fields.Char("Guardian Mobile",tracking=True)
    ls_aadhar = fields.Char(string="AADHAR",tracking=True)
    ls_pan = fields.Char(string="LS PAN",tracking=True)
    ls_uan = fields.Char(string="LS UAN",tracking=True)

    ls_date_of_exit = fields.Date(string="Date of Exit", copy=False, tracking=True)
    ls_date_of_resignation = fields.Date(string="Date of Resignation", copy=False, tracking=True)

    dependant_name_1 = fields.Char(string="Dependant Name 1")
    dependant_dob_1 = fields.Char(string="Dependant DOB 1")
    relationship_status_1 = fields.Char(string="Relationships Status 1")

    dependant_name_2 = fields.Char(string="Dependant Name 2")
    dependant_dob_2 = fields.Char(string="Dependant DOB 2")
    relationship_status_2 = fields.Char(string="Relationships Status 2")

    dependant_name_3 = fields.Char(string="Dependant Name 3")
    dependant_dob_3 = fields.Char(string="Dependant DOB 3")
    relationship_status_3 = fields.Char(string="Relationships Status 3")

    permanent_street = fields.Char(string="Street")
    permanent_street2 = fields.Char(string="Street 2")
    permanent_city = fields.Char(string="City")
    permanent_state_id = fields.Many2one(
        'res.country.state',
        string="State"
    )
    permanent_zip = fields.Char(string="ZIP")
    permanent_country_id = fields.Many2one(
        'res.country',
        string="Country"
    )
    probation_extension_count = fields.Integer(
        string="Probation Extension Count",
        default=0,
        help="Number of times probation period has been extended"
    )
    education_ids = fields.One2many(
        'hr.employee.education',
        'employee_id',
    )
    nominee_name = fields.Char(string="Nominee Name")
    relationship = fields.Selection([
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('guardian', 'Guardian'),
    ],string="Relationships")
    pf_percentage = fields.Float(string="Percentage")
    pf_payment_mode = fields.Selection([
        ('cheque', 'Cheque'),
        ('account_transfer', 'Account Transfer'),
        ('cash', 'Cash'),
    ],string="Payment Mode")

    # Validations
    @api.constrains('ls_aadhar')
    def _check_aadhar(self):
        for emp in self:
            if emp.ls_aadhar:
                # Remove spaces
                aadhar = emp.ls_aadhar.replace(" ", "")
                if not re.match(r'^\d{12}$', aadhar):
                    raise ValidationError("AADHAR must be a 12-digit number.")

    @api.constrains('ls_pan')
    def _check_pan(self):
        for emp in self:
            if emp.ls_pan:
                if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', emp.ls_pan.upper()):
                    raise ValidationError("PAN must be in valid format: ABCDE1234F")

    @api.constrains('ls_uan')
    def _check_uan(self):
        for emp in self:
            if emp.ls_uan:
                uan = emp.ls_uan.replace(" ", "")
                if not re.match(r'^\d{12}$', uan):
                    raise ValidationError("UAN must be a 12-digit number.")

    @api.depends('birthday')
    def _compute_age(self):
        for rec in self:
            if rec.birthday:
                today = date.today()
                rec.age = today.year - rec.birthday.year - (
                        (today.month, today.day) < (rec.birthday.month, rec.birthday.day)
                )
            else:
                rec.age = 0


    @api.depends('current_experience', 'previous_experience')
    def _compute_total_experience(self):
        for rec in self:
            rec.total_experience = (rec.current_experience or 0) + (rec.previous_experience or 0)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if res.get('joining_date_recruit'):
            res['probation_date_start'] = res['joining_date_recruit']
        return res

    @api.onchange('probation_date_start')
    def _onchange_probation_date_start(self):
        """Auto calculate probation end date as 30 days after start"""
        for record in self:
            if record.probation_date_start:
                record.probation_date_end = record.probation_date_start + timedelta(days=30)
            else:
                record.probation_date_end = False

    @api.model
    def _cron_probation_expiry_reminder(self):
        """Send reminder email 2 days before probation end date"""

        today = date.today()
        target_date = today + timedelta(days=1)

        employees = self.env['hr.employee'].search([])
        print(employees, "Employees with probation expiring soon")

        template = self.env.ref('approval_recruitment.email_template_probation_reminder')

        for emp in employees:
            if emp.work_email:

                # Base URL
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

                # Appraisal கண்டுபிடிக்க
                appraisal = self.env['hr.appraisal'].search(
                    [('employee_id', '=', emp.id), ('state', 'in', ['new', 'pending'])],
                    limit=1
                )

                if appraisal:
                    action_id = self.env.ref('hr_appraisal.open_view_hr_appraisal_tree2').id
                    appraisal_url = f"{base_url}/web#id={appraisal.id}&model=hr.appraisal&view_type=form&action={action_id}"
                else:
                    action_id = self.env.ref('hr_appraisal.open_view_hr_appraisal_tree').id
                    appraisal_url = f"{base_url}/web#action={action_id}"

                print(
                    f"Sending probation expiry mail to: {emp.work_email} for probation ending on {emp.probation_date_end}")

                # ✅ Template render (context important)
                template_ctx = template.with_context(appraisal_url=appraisal_url)

                body = template_ctx._render_field('body_html', emp.ids)[emp.id]
                subject = template_ctx._render_field('subject', emp.ids)[emp.id]
                email_from = template_ctx._render_field('email_from', emp.ids)[emp.id]
                email_to = template_ctx._render_field('email_to', emp.ids)[emp.id]
                email_cc = template_ctx._render_field('email_cc', emp.ids)[emp.id]

                mail_values = {
                    'subject': subject,
                    'body_html': body,
                    'email_from': email_from,
                    'email_to': email_to,
                    'email_cc': email_cc,
                }

                self.env['mail.mail'].create(mail_values).send()

    def action_assign_buddy(self):
        emails_sent = []

        for emp in self:
            if not emp.buddy_id:
                raise ValidationError(_("Please select a Buddy before assigning."))

            # Buddy mail
            if emp.buddy_id.email:
                template = self.env.ref('approval_recruitment.email_template_buddy_assign')
                body = template._render_field('body_html', emp.ids)[emp.id]
                subject = template._render_field('subject', emp.ids)[emp.id]

                self.env['mail.mail'].create({
                    'subject': subject,
                    'body_html': body,
                    'email_from': emp.company_id.email or 'info@yourcompany.com',
                    'email_to': emp.buddy_id.email,
                }).send()

            # Employee mail
            if emp.work_email:
                template = self.env.ref('approval_recruitment.email_template_employee_buddy')
                body = template._render_field('body_html', emp.ids)[emp.id]
                subject = template._render_field('subject', emp.ids)[emp.id]

                self.env['mail.mail'].create({
                    'subject': subject,
                    'body_html': body,
                    'email_from': emp.company_id.email or 'info@yourcompany.com',
                    'email_to': emp.work_email,
                }).send()

            emails_sent.append(emp.name)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Mail Sent!',
                'message': f'Buddy & Employee mail sent for: {", ".join(emails_sent)}',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_send_employee_email(self):
        self.ensure_one()

        partner = False

        if self.work_email:
            # Check if partner already exists
            partner = self.env['res.partner'].search([
                ('email', '=', self.work_email)
            ], limit=1)

            # If not found → create new partner
            if not partner:
                partner = self.env['res.partner'].create({
                    'name': self.name,
                    'email': self.work_email,
                })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Send Email',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model': 'hr.employee',
                'default_res_ids': self.ids,
                'default_composition_mode': 'comment',
                'default_partner_ids': [(6, 0, [partner.id])] if partner else [],
                'default_email_to': self.work_email,
            }
        }