import re

from odoo import models, fields, api, _
from odoo.orm.commands import Command


class HrEmployeeInherits(models.Model):
    _inherit = 'hr.employee.public'
    _description = 'HR Employee Public'

    joining_date_recruit = fields.Date(related='employee_id.joining_date_recruit', readonly=True)
    date_of_confirmation = fields.Date(related='employee_id.date_of_confirmation', readonly=True)

    hr_id = fields.Many2one(
        'hr.employee',
        related='employee_id.hr_id',
        readonly=True
    )
    hr_head_id = fields.Many2one(
        'hr.employee',
        related='employee_id.hr_head_id',
        readonly=True
    )
    it_asset_head_id = fields.Many2one(
        'hr.employee',
        related='employee_id.it_asset_head_id',
        readonly=True
    )
    admin_head_id = fields.Many2one(
        'hr.employee',
        related='employee_id.admin_head_id',
        readonly=True
    )
    payroll_head_id = fields.Many2one(
        'hr.employee',
        related='employee_id.payroll_head_id',
        readonly=True
    )


    probation_status = fields.Selection(related='employee_id.probation_status', readonly=True)
    probation_reason = fields.Text(related='employee_id.probation_reason', readonly=True)
    probation_date_start = fields.Date(related='employee_id.probation_date_start', readonly=True)
    probation_date_end = fields.Date(related='employee_id.probation_date_end', readonly=True)

    buddy_id = fields.Many2one('res.users', related='employee_id.buddy_id', readonly=True)
    ls_employee_id = fields.Char(related='employee_id.ls_employee_id', readonly=True)

    hr_contract_type_id = fields.Many2one('hr.contract.type', related='employee_id.hr_contract_type_id', readonly=True)
    entity_name_id = fields.Many2one('entity.name', related='employee_id.entity_name_id', readonly=True)
    base_location_id = fields.Many2one('base.location', related='employee_id.base_location_id', readonly=True)
    deputed_location_id = fields.Many2one('deputed.location', related='employee_id.deputed_location_id', readonly=True)

    band_id = fields.Many2one('band', related='employee_id.band_id', readonly=True)
    level_id = fields.Many2one('level', related='employee_id.level_id', readonly=True)
    vertical_id = fields.Many2one('vertical', related='employee_id.vertical_id', readonly=True)
    function_id = fields.Many2one('function', related='employee_id.function_id', readonly=True)

    parent_account_id = fields.Many2one('parent.account', related='employee_id.parent_account_id', readonly=True)
    account_office_name_ids = fields.Many2many(
        'account.office.name',
        'approval_account_office_rel',  # relation table name
        'approval_id',  # current model field
        'office_id',  # related model field
        string='Account/Office Name',
        readonly = True
    )
    region_id = fields.Many2one('region', related='employee_id.region_id', readonly=True)

    employee_status_id = fields.Many2one('employee.status', related='employee_id.employee_status_id', readonly=True)
    ls_designation_id = fields.Many2one('designation', related='employee_id.ls_designation_id', readonly=True)
    ls_role_id = fields.Many2one('ls.role', related='employee_id.ls_role_id', readonly=True)
    ls_source_of_hire_id = fields.Many2one('source.of.hire', related='employee_id.ls_source_of_hire_id', readonly=True)

    blood_group_id = fields.Many2one('blood.group', related='employee_id.blood_group_id', readonly=True)

    current_experience = fields.Integer(related='employee_id.current_experience', readonly=True)
    previous_experience = fields.Integer(related='employee_id.previous_experience', readonly=True)
    total_experience = fields.Integer(related='employee_id.total_experience', readonly=True)

    age = fields.Integer(related='employee_id.age', readonly=True)

    guardian_type = fields.Selection(related='employee_id.guardian_type', readonly=True)
    father_name = fields.Char(related='employee_id.father_name', readonly=True)
    father_mobile = fields.Char(related='employee_id.father_mobile', readonly=True)
    mother_name = fields.Char(related='employee_id.mother_name', readonly=True)
    mother_mobile = fields.Char(related='employee_id.mother_mobile', readonly=True)

    guardian_relationship = fields.Char(related='employee_id.guardian_relationship', readonly=True)
    guardian_name = fields.Char(related='employee_id.guardian_name', readonly=True)
    guardian_mobile = fields.Char(related='employee_id.guardian_mobile', readonly=True)

    ls_aadhar = fields.Char(related='employee_id.ls_aadhar', readonly=True)
    ls_pan = fields.Char(related='employee_id.ls_pan', readonly=True)
    ls_uan = fields.Char(related='employee_id.ls_uan', readonly=True)

    ls_date_of_exit = fields.Date(related='employee_id.ls_date_of_exit', readonly=True)
    ls_date_of_resignation = fields.Date(related='employee_id.ls_date_of_resignation', readonly=True)

    dependant_name_1 = fields.Char(related='employee_id.dependant_name_1', readonly=True)
    dependant_dob_1 = fields.Char(related='employee_id.dependant_dob_1', readonly=True)
    relationship_status_1 = fields.Char(related='employee_id.relationship_status_1', readonly=True)

    dependant_name_2 = fields.Char(related='employee_id.dependant_name_2', readonly=True)
    dependant_dob_2 = fields.Char(related='employee_id.dependant_dob_2', readonly=True)
    relationship_status_2 = fields.Char(related='employee_id.relationship_status_2', readonly=True)

    dependant_name_3 = fields.Char(related='employee_id.dependant_name_3', readonly=True)
    dependant_dob_3 = fields.Char(related='employee_id.dependant_dob_3', readonly=True)
    relationship_status_3 = fields.Char(related='employee_id.relationship_status_3', readonly=True)

    permanent_street = fields.Char(related='employee_id.permanent_street', readonly=True)
    permanent_street2 = fields.Char(related='employee_id.permanent_street2', readonly=True)
    permanent_city = fields.Char(related='employee_id.permanent_city', readonly=True)
    permanent_state_id = fields.Many2one('res.country.state', related='employee_id.permanent_state_id', readonly=True)
    permanent_zip = fields.Char(related='employee_id.permanent_zip', readonly=True)
    permanent_country_id = fields.Many2one('res.country', related='employee_id.permanent_country_id', readonly=True)

    probation_extension_count = fields.Integer(related='employee_id.probation_extension_count', readonly=True)

    nominee_name = fields.Char(related='employee_id.nominee_name', readonly=True)
    relationship = fields.Selection(related='employee_id.relationship', readonly=True)

    pf_percentage = fields.Float(related='employee_id.pf_percentage', readonly=True)
    pf_payment_mode = fields.Selection(related='employee_id.pf_payment_mode', readonly=True)

    currency_id = fields.Many2one(
        'res.currency',
        related='employee_id.currency_id',
        readonly=True
    )

    wage_appointment_letter = fields.Monetary(
        string="Wage (Appointment Letter)",
        related='employee_id.wage_appointment_letter',
        readonly=True
    )
    appointment_letter_type = fields.Selection(
        related='employee_id.appointment_letter_type',
        readonly=True
    )
    last_working_date_employee = fields.Date(
        related='employee_id.last_working_date_employee',
        readonly=True
    )

    employee_notice_period = fields.Integer(
        related='employee_id.employee_notice_period',
        readonly=True
    )

    confirmed_employee_notice_period = fields.Integer(
        related='employee_id.confirmed_employee_notice_period',
        readonly=True
    )

    probation_in_months = fields.Integer(
        related='employee_id.probation_in_months',
        readonly=True
    )

    cmt_hospital_name = fields.Char(
        related='employee_id.cmt_hospital_name',
        readonly=True
    )

    cmt_hospital_city = fields.Char(
        related='employee_id.cmt_hospital_city',
        readonly=True
    )

    hse_hospital_name = fields.Char(
        related='employee_id.hse_hospital_name',
        readonly=True
    )

    hse_hospital_city = fields.Char(
        related='employee_id.hse_hospital_city',
        readonly=True
    )

    full_time_hospital_name = fields.Char(
        related='employee_id.full_time_hospital_name',
        readonly=True
    )

    full_time_hospital_city = fields.Char(
        related='employee_id.full_time_hospital_city',
        readonly=True
    )
    applicant_id = fields.Many2one(
        'hr.applicant',
        related='employee_id.applicant_id',
        readonly=True
    )

    basic_pay = fields.Float(
        string="Basic Pay",
    )
    hra = fields.Float(
        string="HRA",
    )
    special_allowance = fields.Float(
        string="Special Allowances",
    )
    total_gross_pay = fields.Float(
        string="Total Gross Pay",
    )
    employer_pf = fields.Float(
        string="Employer PF",
    )

    basic_pay_annual = fields.Float(
        string="Basic Pay (Annual)",
    )

    hra_annual = fields.Float(
        string="HRA (Annual)",
    )

    special_allowance_annual = fields.Float(
        string="Special Allowance (Annual)",
    )

    total_gross_pay_annual = fields.Float(
        string="Total Gross Pay (Annual)",
    )

    employer_pf_annual = fields.Float(
        string="Employer PF (Annual)",
    )

    personal_email = fields.Char(
        string="Personal Email",
        compute="_compute_private_contact",compute_sudo=True,
    )

    contact_number = fields.Char(
        string="Contact Number",
        compute="_compute_private_contact",compute_sudo=True,
    )

    aadhar = fields.Char(
        string="AADHAR ",
        compute="_compute_private_contact",compute_sudo=True,
    )

    bank_accounts_display = fields.Char(
        string="Bank Accounts",
        compute="_compute_private_contact",compute_sudo=True,
    )

    @api.depends()
    def _compute_private_contact(self):
        Employee = self.env["hr.employee"].sudo()

        for employee_public in self:
            employee = Employee.browse(employee_public.id)

            employee_public.personal_email = employee.private_email
            employee_public.contact_number = employee.private_phone
            employee_public.aadhar = employee.ls_aadhar

            bank_names = employee.bank_account_ids.sudo().mapped(
                lambda bank: f"{bank.bank_id.name or ''} - {bank.acc_number or ''}"
            )

            employee_public.bank_accounts_display = ", ".join(bank_names)

    legal_name_public = fields.Char(
        string="Legal Name",
        compute="_compute_personal_information",
        compute_sudo=True,
    )

    birthday_public = fields.Date(
        string="Date of Birth",
        compute="_compute_personal_information",
        compute_sudo=True,
    )

    age_public = fields.Integer(
        string="Age ",
        compute="_compute_personal_information",
        compute_sudo=True,
    )

    place_of_birth_public = fields.Char(
        string="Place of Birth",
        compute="_compute_personal_information",
        compute_sudo=True,
    )

    country_of_birth_public = fields.Char(
        string="Country of Birth",
        compute="_compute_personal_information",
        compute_sudo=True,
    )

    blood_group_public = fields.Char(
        string="Blood Group ",
        compute="_compute_personal_information",
        compute_sudo=True,
    )

    gender_public = fields.Selection(
        selection=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
        ],
        string="Gender",
        compute="_compute_personal_information",
        compute_sudo=True,
    )

    @api.depends()
    def _compute_personal_information(self):
        Employee = self.env["hr.employee"].sudo()

        for employee_public in self:
            employee = Employee.browse(employee_public.id)

            employee_public.legal_name_public = employee.legal_name
            employee_public.birthday_public = employee.birthday
            employee_public.age_public = employee.age
            employee_public.place_of_birth_public = employee.place_of_birth
            employee_public.country_of_birth_public = (
                employee.country_of_birth.name
            )
            employee_public.blood_group_public = employee.blood_group_id.name
            employee_public.gender_public = employee.sex

    guardian_type_public = fields.Char(
        string="Guardian Type ",
        compute="_compute_emergency_contact",
        compute_sudo=True,
    )

    father_name_public = fields.Char(
        string="Father Name ",
        compute="_compute_emergency_contact",
        compute_sudo=True,
    )

    father_mobile_public = fields.Char(
        string="Father Mobile ",
        compute="_compute_emergency_contact",
        compute_sudo=True,
    )

    mother_name_public = fields.Char(
        string="Mother Name ",
        compute="_compute_emergency_contact",
        compute_sudo=True,
    )

    mother_mobile_public = fields.Char(
        string="Mother Mobile ",
        compute="_compute_emergency_contact",
        compute_sudo=True,
    )

    guardian_relationship_public = fields.Char(
        string="Guardian Relationships ",
        compute="_compute_emergency_contact",
        compute_sudo=True,
    )

    guardian_name_public = fields.Char(
        string="Guardian Name ",
        compute="_compute_emergency_contact",
        compute_sudo=True,
    )

    guardian_mobile_public = fields.Char(
        string="Guardian Mobile ",
        compute="_compute_emergency_contact",
        compute_sudo=True,
    )

    @api.depends()
    def _compute_emergency_contact(self):
        Employee = self.env["hr.employee"].sudo()

        for employee_public in self:
            employee = Employee.browse(employee_public.id)

            employee_public.guardian_type_public = employee.guardian_type

            employee_public.father_name_public = employee.father_name
            employee_public.father_mobile_public = employee.father_mobile

            employee_public.mother_name_public = employee.mother_name
            employee_public.mother_mobile_public = employee.mother_mobile

            employee_public.guardian_relationship_public = employee.guardian_relationship
            employee_public.guardian_name_public = employee.guardian_name
            employee_public.guardian_mobile_public = employee.guardian_mobile

    visa_no_public = fields.Char(
        string="Visa No ",
        compute="_compute_visa_work_permit",
        compute_sudo=True,
    )

    visa_expire_public = fields.Date(
        string="Expires on ",
        compute="_compute_visa_work_permit",
        compute_sudo=True,
    )

    work_permit_no_public = fields.Char(
        string="Work Permit No ",
        compute="_compute_visa_work_permit",
        compute_sudo=True,
    )

    work_permit_expiration_date_public = fields.Date(
        string="Expires on  ",
        compute="_compute_visa_work_permit",
        compute_sudo=True,
    )

    has_work_permit_public = fields.Binary(
        string="Document ",
        compute="_compute_visa_work_permit",
        compute_sudo=True,
    )

    @api.depends()
    def _compute_visa_work_permit(self):
        Employee = self.env["hr.employee"].sudo()

        for employee_public in self:
            employee = Employee.browse(employee_public.id)

            employee_public.visa_no_public = employee.visa_no
            employee_public.visa_expire_public = employee.visa_expire

            employee_public.work_permit_no_public = employee.permit_no
            employee_public.work_permit_expiration_date_public = (
                employee.work_permit_expiration_date
            )

            employee_public.has_work_permit_public = employee.has_work_permit

    # Citizenship

    nationality_public = fields.Char(
        string="Nationality (Country) ",
        compute="_compute_citizenship_location",
        compute_sudo=True,
    )

    non_resident_public = fields.Boolean(
        string="Non-resident ",
        compute="_compute_citizenship_location",
        compute_sudo=True,
    )

    identification_no_public = fields.Char(
        string="Identification No ",
        compute="_compute_citizenship_location",
        compute_sudo=True,
    )

    passport_no_public = fields.Char(
        string="Passport No ",
        compute="_compute_citizenship_location",
        compute_sudo=True,
    )

    passport_expiration_public = fields.Date(
        string="Expires on   ",
        compute="_compute_citizenship_location",
        compute_sudo=True,
    )

    # Present Address

    present_street_public = fields.Char(
        string="Street ",
        compute="_compute_citizenship_location",
        compute_sudo=True,
    )

    present_street2_public = fields.Char(
        string="Street 2 ",
        compute="_compute_citizenship_location",
        compute_sudo=True,
    )

    present_city_public = fields.Char(
        string="City ",
        compute="_compute_citizenship_location",
        compute_sudo=True,
    )

    present_state_public = fields.Char(
        string="State ",
        compute="_compute_citizenship_location",
        compute_sudo=True,
    )

    present_zip_public = fields.Char(
        string="ZIP ",
        compute="_compute_citizenship_location",
        compute_sudo=True,
    )

    present_country_public = fields.Char(
        string="Country ",
        compute="_compute_citizenship_location",
        compute_sudo=True,
    )

    # Permanent Address

    permanent_street_public = fields.Char(
        string="Street  ",
        compute="_compute_citizenship_location",
        compute_sudo=True,
    )

    permanent_street2_public = fields.Char(
        string="Street 2  ",
        compute="_compute_citizenship_location",
        compute_sudo=True,
    )

    permanent_city_public = fields.Char(
        string="City  ",
        compute="_compute_citizenship_location",
        compute_sudo=True,
    )

    permanent_state_public = fields.Char(
        string="State  ",
        compute="_compute_citizenship_location",
        compute_sudo=True,
    )

    permanent_zip_public = fields.Char(
        string="ZIP  ",
        compute="_compute_citizenship_location",
        compute_sudo=True,
    )

    permanent_country_public = fields.Char(
        string="Country  ",
        compute="_compute_citizenship_location",
        compute_sudo=True,
    )

    distance_home_work_public = fields.Char(
        string="Distance ",
        compute="_compute_citizenship_location",
        compute_sudo=True,
    )

    @api.depends()
    def _compute_citizenship_location(self):
        Employee = self.env["hr.employee"].sudo()

        for employee_public in self:
            employee = Employee.browse(employee_public.id)

            # Citizenship
            employee_public.nationality_public = (
                employee.country_id.name if employee.country_id else ""
            )

            employee_public.non_resident_public = employee.is_non_resident

            employee_public.identification_no_public = (
                    employee.identification_id or ""
            )

            employee_public.passport_no_public = (
                    employee.passport_id or ""
            )

            employee_public.passport_expiration_public = (
                employee.passport_expiration_date
            )

            # Present Address
            employee_public.present_street_public = employee.private_street or ""
            employee_public.present_street2_public = employee.private_street2 or ""
            employee_public.present_city_public = employee.private_city or ""

            employee_public.present_state_public = (
                employee.private_state_id.name
                if employee.private_state_id
                else ""
            )

            employee_public.present_zip_public = employee.private_zip or ""

            employee_public.present_country_public = (
                employee.private_country_id.name
                if employee.private_country_id
                else ""
            )

            # Permanent Address
            employee_public.permanent_street_public = (
                    employee.permanent_street or ""
            )

            employee_public.permanent_street2_public = (
                    employee.permanent_street2 or ""
            )

            employee_public.permanent_city_public = (
                    employee.permanent_city or ""
            )

            employee_public.permanent_state_public = (
                employee.permanent_state_id.name
                if employee.permanent_state_id
                else ""
            )

            employee_public.permanent_zip_public = (
                    employee.permanent_zip or ""
            )

            employee_public.permanent_country_public = (
                employee.permanent_country_id.name
                if employee.permanent_country_id
                else ""
            )

            # Distance
            employee_public.distance_home_work_public = (
                str(employee.distance_home_work)
                if employee.distance_home_work
                else ""
            )

    pf_nominee_name_public = fields.Char(
        string="Nominee Name ",
        compute="_compute_pf_details",
        compute_sudo=True,
    )

    pf_nominee_relationship_public = fields.Char(
        string="Relationships ",
        compute="_compute_pf_details",
        compute_sudo=True,
    )

    pf_nominee_percentage_public = fields.Char(
        string="Percentage ",
        compute="_compute_pf_details",
        compute_sudo=True,
    )

    pf_payment_mode_public = fields.Char(
        string="Payment Mode ",
        compute="_compute_pf_details",
        compute_sudo=True,
    )

    @api.depends()
    def _compute_pf_details(self):
        Employee = self.env["hr.employee"].sudo()

        for employee_public in self:
            employee = Employee.browse(employee_public.id)

            employee_public.pf_nominee_name_public = (
                    employee.nominee_name or ""
            )

            employee_public.pf_nominee_relationship_public = (
                    employee.relationship or ""
            )

            employee_public.pf_nominee_percentage_public = (
                str(employee.pf_percentage)
                if employee.pf_percentage
                else ""
            )

            payment_selection = (
                employee._fields["pf_payment_mode"]
                ._description_selection(employee.env)
            )

            employee_public.pf_payment_mode_public = dict(
                payment_selection
            ).get(
                employee.pf_payment_mode,
                ""
            )

    disabled_public = fields.Boolean(
        string="Disabled ",
        compute="_compute_family_information",
        compute_sudo=True,
    )

    marital_status_public = fields.Char(
        string="Marital Status ",
        compute="_compute_family_information",
        compute_sudo=True,
    )

    spouse_legal_name_public = fields.Char(
        string="Spouse Legal Name ",
        compute="_compute_family_information",
        compute_sudo=True,
    )

    spouse_birthdate_public = fields.Date(
        string="Spouse Birthdate ",
        compute="_compute_family_information",
        compute_sudo=True,
    )

    dependent_children_public = fields.Char(
        string="Dependent Children ",
        compute="_compute_family_information",
        compute_sudo=True,
    )

    @api.depends()
    def _compute_family_information(self):
        Employee = self.env["hr.employee"].sudo()

        for employee_public in self:
            employee = Employee.browse(employee_public.id)

            employee_public.disabled_public = employee.disabled

            # Selection value -> Selection label
            marital_selection = (
                employee._fields["marital"]
                ._description_selection(employee.env)
            )

            employee_public.marital_status_public = dict(
                marital_selection
            ).get(
                employee.marital,
                ""
            )

            # Spouse details
            employee_public.spouse_legal_name_public = (
                    employee.spouse_complete_name or ""
            )

            employee_public.spouse_birthdate_public = (
                employee.spouse_birthdate
            )

            employee_public.dependent_children_public = str(
                employee.children
                if employee.children is not None
                else ""
            )

    education_public_ids = fields.One2many(
        "hr.employee.public.education",
        "employee_public_id",
        string="Education ",
        readonly=True,
    )

    # self employee tab
    is_my_employee = fields.Boolean(
        compute="_compute_is_my_employee",
        compute_sudo=True,
    )

    @api.depends("user_id")
    def _compute_is_my_employee(self):
        current_user = self.env.user

        for employee in self:
            employee.is_my_employee = employee.user_id == current_user