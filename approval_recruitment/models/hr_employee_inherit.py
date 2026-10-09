import re

from odoo import models, fields, api, _
from datetime import timedelta, date

from odoo.exceptions import ValidationError, UserError, RedirectWarning


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
    wage_appointment_letter = fields.Monetary(
        string="Wage (Appointment Letter)",
        compute="_compute_wage_appointment_letter",
        inverse="_inverse_wage_appointment_letter",
        currency_field='currency_id',
        store=True
    )
    appointment_letter_type = fields.Selection([
        ('cmt_appointment_letter', 'CMT Appointment Letter'),
        ('hse_appointment_letter', 'HSE Appointment Letter'),
        ('full_time_appointment_letter', 'Full Time Appointment Letter'),
    ],string="Appointment Letter",tracking=True)
    cmt_hospital_name = fields.Char(string="CMT Hospital Name",tracking=True)
    cmt_hospital_city = fields.Char(string="CMT Hospital City",tracking=True)

    hse_hospital_name = fields.Char(string="HSE Hospital Name", tracking=True)
    hse_hospital_city = fields.Char(string="HSE Hospital City", tracking=True)

    full_time_hospital_name = fields.Char(string="Full Time Hospital Name", tracking=True)
    full_time_hospital_city = fields.Char(string="Full Time Hospital City", tracking=True)

    employee_notice_period = fields.Integer(string="Probation Notice Period",tracking=True)
    confirmed_employee_notice_period = fields.Integer(string="Confirmed Notice Period",tracking=True)
    probation_in_months = fields.Integer(string="Probation in Months",tracking=True)
    # last_working_date_employee = fields.Date(
    #     string="Last Working Date",
    #     compute="_compute_last_working_date",
    #     store=True,
    #     tracking=True
    # )
    #
    # @api.depends('confirmed_employee_notice_period')
    # def _compute_last_working_date(self):
    #     for rec in self:
    #         if rec.confirmed_employee_notice_period:
    #             rec.last_working_date_employee = fields.Date.today() + timedelta(
    #                 days=rec.confirmed_employee_notice_period
    #             )
    #         else:
    #             rec.last_working_date_employee = False

    @api.depends('wage')
    def _compute_wage_appointment_letter(self):
        for rec in self:
            rec.wage_appointment_letter = rec.wage or 0.0

    def _inverse_wage_appointment_letter(self):
        for rec in self:
            rec.wage = rec.wage_appointment_letter

    probation_status = fields.Selection([
        ('extended', 'Extension of Probation'),
        ('confirmed', 'Confirmed Employee'),
    ], string="Probation Status", tracking=True)

    probation_reason = fields.Text(string="Probation Reason", tracking=True)
    probation_date_start = fields.Date(string="Probation Start Date",tracking=True)
    probation_date_end = fields.Date(string="Probation End Date",tracking=True)

    buddy_id = fields.Many2one('res.users', 'Buddy',tracking=True)
    ls_employee_id = fields.Char(string="Employee ID",tracking=True, store=True)
    hr_contract_type_id = fields.Many2one('hr.contract.type', 'Employment Type',tracking=True)
    entity_name_id = fields.Many2one('entity.name', 'Entity Name',tracking=True)
    base_location_id = fields.Many2one('base.location', 'Base Location',tracking=True)
    deputed_location_id = fields.Many2one('deputed.location', 'Deputed Location',tracking=True)
    band_id = fields.Many2one('band', 'Band',tracking=True)
    level_id = fields.Many2one('level', 'Level',tracking=True)
    vertical_id = fields.Many2one('vertical', 'Vertical',tracking=True)
    function_id = fields.Many2one('function', 'Function',tracking=True)
    parent_account_id = fields.Many2one('parent.account', 'Parent Account',tracking=True)
    account_office_name_ids = fields.Many2many(
        'account.office.name',
        'approval_account_office_rel',  # relation table name
        'approval_id',  # current model field
        'office_id',  # related model field
        string='Account/Office Name',
        tracking=True
    )
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

    dependant_name_1 = fields.Char(string="Dependant Name 1", tracking=True)
    dependant_dob_1 = fields.Char(string="Dependant DOB 1", tracking=True)
    relationship_status_1 = fields.Char(string="Relationships Status 1", tracking=True)

    dependant_name_2 = fields.Char(string="Dependant Name 2", tracking=True)
    dependant_dob_2 = fields.Char(string="Dependant DOB 2", tracking=True)
    relationship_status_2 = fields.Char(string="Relationships Status 2", tracking=True)

    dependant_name_3 = fields.Char(string="Dependant Name 3", tracking=True)
    dependant_dob_3 = fields.Char(string="Dependant DOB 3", tracking=True)
    relationship_status_3 = fields.Char(string="Relationships Status 3", tracking=True)

    permanent_street = fields.Char(string="Street", tracking=True)
    permanent_street2 = fields.Char(string="Street 2", tracking=True)
    permanent_city = fields.Char(string="City", tracking=True)
    permanent_state_id = fields.Many2one(
        'res.country.state',
        string="State", tracking=True
    )
    permanent_zip = fields.Char(string="ZIP", tracking=True)
    permanent_country_id = fields.Many2one(
        'res.country',
        string="Country", tracking=True
    )
    probation_extension_count = fields.Integer(
        string="Probation Extension Count",
        default=0,
        help="Number of times probation period has been extended", tracking=True
    )
    education_ids = fields.One2many(
        'hr.employee.education',
        'employee_id',
    )
    nominee_name = fields.Char(string="Nominee Name", tracking=True)
    relationship = fields.Selection([
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('guardian', 'Guardian'),
    ],string="Relationships", tracking=True)
    pf_percentage = fields.Float(string="Percentage", tracking=True)
    pf_payment_mode = fields.Selection([
        ('cheque', 'Cheque'),
        ('account_transfer', 'Account Transfer'),
        ('cash', 'Cash'),
    ],string="Payment Mode", tracking=True)
    applicant_id = fields.Many2one(
        'hr.applicant',
        string="Applicant", tracking=True
    )
    # account_id = fields.Many2one(
    #     'account.sync',
    #     string="Account"
    # )

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

    def _check_appointment_template(self, report_name):
        for rec in self:

            mapping = {
                'approval_recruitment.template_cmt_full_time_appointment_letter': 'cmt_appointment_letter',
                'approval_recruitment.template_hse_appointment_letter': 'hse_appointment_letter',
                'approval_recruitment.template_full_time_appointment_letter': 'full_time_appointment_letter',
            }

            expected_type = mapping.get(report_name)

            if expected_type and rec.appointment_letter_type != expected_type:
                raise UserError(_(
                    "❌ You selected '%s' in Appointment Letter Type.\n\n"
                    "Please print the correct template only."
                ) % (rec.appointment_letter_type))

    def action_print_cmt_appointment_letter(self):
        for record in self:
            missing_fields = []

            if not record.cmt_hospital_name:
                missing_fields.append("CMT Hospital Name")

            if not record.cmt_hospital_city:
                missing_fields.append("CMT Hospital City")

            if not record.joining_date_recruit:
                missing_fields.append("Date of Joining")

            if not record.band_id:
                missing_fields.append("Band")

            if not record.level_id:
                missing_fields.append("Level")

            if not record.wage:
                missing_fields.append("Salary")

            # Employee / HR Details
            if not record.job_id:
                missing_fields.append("Job Position")

            else:
                if not record.job_id.hr_head_name:
                    missing_fields.append("HR Head Name")

                if not record.job_id.hr_description:
                    missing_fields.append("HR Description")

            if not record.company_id:
                missing_fields.append("Company")

            else:
                if not record.company_id.name:
                    missing_fields.append("Company Name")

                if not record.company_id.street:
                    missing_fields.append("Company Street")

                if not record.company_id.street2:
                    missing_fields.append("Company Street 2")

                if not record.company_id.city:
                    missing_fields.append("Company City")

                if not record.company_id.state_id:
                    missing_fields.append("Company State")

                if not record.company_id.zip:
                    missing_fields.append("Company ZIP")

            if missing_fields:
                raise UserError(
                    _(
                        "Please fill in the following fields before printing "
                        "the CMT Appointment Letter:\n\n- %s"
                    )
                    % "\n- ".join(missing_fields)
                )

            record._check_appointment_template(
                'approval_recruitment.template_cmt_full_time_appointment_letter'
            )

            return self.env.ref(
                'approval_recruitment.action_report_cmt_full_time_appointment_letter'
            ).report_action(record)

    def action_print_hse_appointment_letter(self):
        for record in self:
            missing_fields = []

            if not record.hse_hospital_name:
                missing_fields.append("HSE Hospital Name")

            if not record.hse_hospital_city:
                missing_fields.append("HSE Hospital City")

            if not record.joining_date_recruit:
                missing_fields.append("Date of Joining")

            if not record.band_id:
                missing_fields.append("Band")

            if not record.level_id:
                missing_fields.append("Level")

            if not record.wage:
                missing_fields.append("Salary")

            # Employee / HR Details
            if not record.job_id:
                missing_fields.append("Job Position")

            else:
                if not record.job_id.hr_head_name:
                    missing_fields.append("HR Head Name")

                if not record.job_id.hr_description:
                    missing_fields.append("HR Description")

            if not record.company_id:
                missing_fields.append("Company")

            else:
                if not record.company_id.name:
                    missing_fields.append("Company Name")

                if not record.company_id.street:
                    missing_fields.append("Company Street")

                if not record.company_id.street2:
                    missing_fields.append("Company Street 2")

                if not record.company_id.city:
                    missing_fields.append("Company City")

                if not record.company_id.state_id:
                    missing_fields.append("Company State")

                if not record.company_id.zip:
                    missing_fields.append("Company ZIP")

            if missing_fields:
                raise UserError(
                    _(
                        "Please fill in the following fields before printing "
                        "the HSE Appointment Letter:\n\n- %s"
                    )
                    % "\n- ".join(missing_fields)
                )

            record._check_appointment_template(
                'approval_recruitment.template_hse_appointment_letter'
            )

            return self.env.ref(
                'approval_recruitment.action_report_hse_appointment_letter'
            ).report_action(record)

    def action_print_full_time_appointment_letter(self):
        for record in self:
            missing_fields = []

            if not record.full_time_hospital_name:
                missing_fields.append("Full Time Hospital Name")

            if not record.full_time_hospital_city:
                missing_fields.append("Full Time Hospital City")

            if not record.joining_date_recruit:
                missing_fields.append("Joining Date Recruit")

            if not record.joining_date_recruit:
                missing_fields.append("Date of Joining")

            if not record.band_id:
                missing_fields.append("Band")

            if not record.level_id:
                missing_fields.append("Level")

            if not record.wage:
                missing_fields.append("Salary")

            # Employee / HR Details
            if not record.job_id:
                missing_fields.append("Job Position")

            else:
                if not record.job_id.hr_head_name:
                    missing_fields.append("HR Head Name")

                if not record.job_id.hr_description:
                    missing_fields.append("HR Description")

            if not record.company_id:
                missing_fields.append("Company")

            else:
                if not record.company_id.name:
                    missing_fields.append("Company Name")

                if not record.company_id.street:
                    missing_fields.append("Company Street")

                if not record.company_id.street2:
                    missing_fields.append("Company Street 2")

                if not record.company_id.city:
                    missing_fields.append("Company City")

                if not record.company_id.state_id:
                    missing_fields.append("Company State")

                if not record.company_id.zip:
                    missing_fields.append("Company ZIP")

            if missing_fields:
                raise UserError(
                    _(
                        "Please fill in the following fields before printing "
                        "the Full Time Appointment Letter:\n\n- %s"
                    )
                    % "\n- ".join(missing_fields)
                )

            record._check_appointment_template(
                'approval_recruitment.template_full_time_appointment_letter'
            )

            return self.env.ref(
                'approval_recruitment.action_report_full_time_appointment_letter'
            ).report_action(record)

    basic_pay = fields.Float(
        string="Basic Pay",
        compute="_compute_salary_breakup",
        store=True, tracking=True
    )
    hra = fields.Float(
        string="HRA",
        compute="_compute_salary_breakup",
        store=True, tracking=True
    )
    special_allowance = fields.Float(
        string="Special Allowances",
        compute="_compute_salary_breakup",
        store=True, tracking=True
    )
    total_gross_pay = fields.Float(
        string="Total Gross Pay",
        compute="_compute_salary_breakup",
        store=True, tracking=True
    )
    employer_pf = fields.Float(
        string="Employer PF",
        compute="_compute_salary_breakup",
        store=True, tracking=True
    )

    basic_pay_annual = fields.Float(
        string="Basic Pay (Annual)",
        compute="_compute_salary_breakup",
        store=True, tracking=True
    )

    hra_annual = fields.Float(
        string="HRA (Annual)",
        compute="_compute_salary_breakup",
        store=True, tracking=True
    )

    special_allowance_annual = fields.Float(
        string="Special Allowance (Annual)",
        compute="_compute_salary_breakup",
        store=True, tracking=True
    )

    total_gross_pay_annual = fields.Float(
        string="Total Gross Pay (Annual)",
        compute="_compute_salary_breakup",
        store=True, tracking=True
    )

    employer_pf_annual = fields.Float(
        string="Employer PF (Annual)",
        compute="_compute_employer_pf_annual",
        store=True, tracking=True
    )

    @api.depends('wage')
    def _compute_salary_breakup(self):
        for rec in self:
            monthly_gross = rec.wage or 0.0  # ✅ direct monthly

            if not monthly_gross:
                rec.basic_pay = 0.0
                rec.hra = 0.0
                rec.special_allowance = 0.0
                rec.total_gross_pay = 0.0
                rec.employer_pf = 0.0

                rec.basic_pay_annual = 0.0
                rec.hra_annual = 0.0
                rec.special_allowance_annual = 0.0
                rec.total_gross_pay_annual = 0.0
                rec.employer_pf_annual = 0.0
                continue

            # ✅ Monthly breakup
            monthly_basic = monthly_gross * 0.50
            monthly_hra = monthly_gross * 0.30
            monthly_special = monthly_gross * 0.20

            # ✅ Employer PF
            if monthly_basic > 15000:
                monthly_pf = 1800.0
            else:
                monthly_pf = monthly_basic * 0.12

            # Monthly values
            rec.total_gross_pay = monthly_gross
            rec.basic_pay = monthly_basic
            rec.hra = monthly_hra
            rec.special_allowance = monthly_special
            rec.employer_pf = monthly_pf

            # ✅ Annual values
            rec.basic_pay_annual = monthly_basic * 12
            rec.hra_annual = monthly_hra * 12
            rec.special_allowance_annual = monthly_special * 12
            rec.total_gross_pay_annual = monthly_gross * 12
            rec.employer_pf_annual = monthly_pf * 12

    @api.depends('employer_pf')
    def _compute_employer_pf_annual(self):
        for rec in self:
            rec.employer_pf_annual = (rec.employer_pf or 0.0) * 12

    def action_create_users_confirmation(self):
        total_users = self.env['res.users'].search_count([])

        raise RedirectWarning(
            message=_(
                "Total allowed users: 300.\n"
                "Currently %s users exist in the system.\n"
                "You are about to create %s new users.\n\n"
                "Do you wish to continue?"
            ) % (total_users, len(self.ids)),
            action=self.env.ref('hr.action_hr_employee_create_users').id,
            button_text=_('Confirm'),
            additional_context={
                'selected_ids': self.ids,
            },
        )