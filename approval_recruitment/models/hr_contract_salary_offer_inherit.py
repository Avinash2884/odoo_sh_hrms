from num2words import num2words

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrContractSalaryOffer(models.Model):
    _inherit = 'hr.contract.salary.offer'

    offer_letter_type = fields.Selection([
        ('internship_letter', 'Internship Offer Template'),
        ('offer_of_appointment', 'Full Time Employee Offer Letter'),
        ('cmt_offer_of_internship_and_subsequent_appointment', 'CMT Offer Letter Template'),
        ('hse_offer_of_internship_and_subsequent_appointment', 'HSE Offer Letter Template'),
    ], string="Offer Letter Type")
    hospital_name = fields.Char(string="Hospital Name")
    hospital_city = fields.Char(string="Hospital City")

    #cmt offer internship
    cmt_designation = fields.Many2one('hr.job',string="CMT Designation")
    band_id = fields.Many2one('band',string="CMT Band")
    level_id = fields.Many2one('level',string="CMT Level")


    # hse offer internship
    hse_designation = fields.Many2one('hr.job',string="HSE Designation")
    hse_intern_hospital_name = fields.Char(string="HSE Intern (Hospital Name)")
    hse_intern_hospital_city = fields.Char(string="HSE Intern (Hospital City)")
    hse_band_id = fields.Many2one('band', string="HSE Band")
    hse_level_id = fields.Many2one('level', string="HSE Level")

    # offer of appointment
    designation = fields.Many2one('hr.job',string="Offer Designation")
    variable_pay_ctc = fields.Float(string="Variable Pay CTC")
    offer_hospital_name = fields.Char(string="Offer of Appointment (Hospital Name)")
    offer_hospital_city = fields.Char(string="Offer of Appointment (Hospital City)")
    offer_band_id = fields.Many2one('band', string="Offer Band")
    offer_level_id = fields.Many2one('level', string="Offer Level")

    # internship letter
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")

    basic_pay = fields.Float(
        string="Basic Pay",
        compute="_compute_salary_breakup",
        store=True
    )
    hra = fields.Float(
        string="HRA",
        compute="_compute_salary_breakup",
        store=True
    )
    special_allowance = fields.Float(
        string="Special Allowances",
        compute="_compute_salary_breakup",
        store=True
    )
    total_gross_pay = fields.Float(
        string="Total Gross Pay",
        compute="_compute_salary_breakup",
        store=True
    )
    employer_pf = fields.Float(
        string="Employer PF",
        compute="_compute_salary_breakup",
        store=True
    )

    basic_pay_annual = fields.Float(
        string="Basic Pay (Annual)",
        compute="_compute_salary_breakup",
        store=True
    )

    hra_annual = fields.Float(
        string="HRA (Annual)",
        compute="_compute_salary_breakup",
        store=True
    )

    special_allowance_annual = fields.Float(
        string="Special Allowance (Annual)",
        compute="_compute_salary_breakup",
        store=True
    )

    total_gross_pay_annual = fields.Float(
        string="Total Gross Pay (Annual)",
        compute="_compute_salary_breakup",
        store=True
    )

    employer_pf_annual = fields.Float(
        string="Employer PF (Annual)",
        compute="_compute_salary_breakup",
        store=True
    )
    offer_letter_notice_period = fields.Integer(string="Probation Notice Period",tracking=True)
    confirmed_notice_period = fields.Integer(string="Confirmed Notice Period",tracking=True)

    def get_notice_period_words(self):
        for rec in self:
            if rec.offer_letter_notice_period:
                return num2words(rec.offer_letter_notice_period).capitalize()
            return '-'

    @api.depends('final_yearly_costs')
    def _compute_salary_breakup(self):
        for rec in self:

            # ---------------------------------
            # Fixed CTC / Month
            # Excel B7
            # ---------------------------------
            monthly_ctc = rec.final_yearly_costs or 0.0

            if not monthly_ctc:
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

            # ---------------------------------
            # Basic Pay
            # Excel B2
            #
            # =IF((B7*50%)>=21500,B7*50%,21075)
            # ---------------------------------
            basic_50_percent = monthly_ctc * 0.50

            if basic_50_percent >= 21500:
                monthly_basic = basic_50_percent
            else:
                monthly_basic = 21075.0

            # ---------------------------------
            # Employer PF
            # Excel B6
            #
            # =ROUND(
            #   IF((B2*13%)>=3250,3250,B2*13%),
            #   0
            # )
            # ---------------------------------
            pf_calculated = monthly_basic * 0.13

            if pf_calculated >= 3250:
                monthly_pf = 3250.0
            else:
                monthly_pf = pf_calculated

            # Excel ROUND(..., 0)
            monthly_pf = math.floor(monthly_pf + 0.5)

            # ---------------------------------
            # Gross
            # Excel B5
            #
            # =ROUND(B7-B6,0)
            # ---------------------------------
            monthly_gross = monthly_ctc - monthly_pf

            # Excel ROUND(..., 0)
            monthly_gross = math.floor(monthly_gross + 0.5)

            # ---------------------------------
            # HRA
            # Excel B3
            #
            # =ROUND(
            #   IF(
            #      (B2*60%)>(B5-B2),
            #      B5-B2,
            #      B2*60%
            #   ),
            #   -1
            # )
            # ---------------------------------

            hra_60_percent = monthly_basic * 0.60
            gross_minus_basic = monthly_gross - monthly_basic

            if hra_60_percent > gross_minus_basic:
                monthly_hra = gross_minus_basic
            else:
                monthly_hra = hra_60_percent

            # Excel ROUND(..., -1)
            # Nearest 10
            monthly_hra = math.floor(
                (monthly_hra / 10) + 0.5
            ) * 10

            # ---------------------------------
            # Conveyance
            # Excel B4
            #
            # =ROUNDDOWN((B5-B2-B3),-1)
            # ---------------------------------

            monthly_conveyance = (
                    monthly_gross
                    - monthly_basic
                    - monthly_hra
            )

            # Excel ROUNDDOWN(..., -1)
            # Always round DOWN to nearest 10
            monthly_conveyance = (
                    math.floor(monthly_conveyance / 10) * 10
            )

            # ---------------------------------
            # Monthly Values
            # ---------------------------------

            rec.basic_pay = monthly_basic
            rec.hra = monthly_hra
            rec.special_allowance = monthly_conveyance
            rec.total_gross_pay = monthly_gross
            rec.employer_pf = monthly_pf

            # ---------------------------------
            # Annual Values
            # ---------------------------------

            rec.basic_pay_annual = monthly_basic * 12
            rec.hra_annual = monthly_hra * 12
            rec.special_allowance_annual = monthly_conveyance * 12
            rec.total_gross_pay_annual = monthly_gross * 12
            rec.employer_pf_annual = monthly_pf * 12

    def _check_offer_template(self, report_name):
        for rec in self:

            # Mapping report பெயர் vs selection
            mapping = {
                'approval_recruitment.template_internship_offer': 'internship_letter',
                'approval_recruitment.template_cmt_offer': 'cmt_offer_of_internship_and_subsequent_appointment',
                'approval_recruitment.template_hse_offer': 'hse_offer_of_internship_and_subsequent_appointment',
                'approval_recruitment.template_offer_of_appointment': 'offer_of_appointment',
            }

            expected_type = mapping.get(report_name)

            if expected_type and rec.offer_letter_type != expected_type:
                raise UserError(_(
                    "❌ You selected '%s' in Offer Letter Type.\n\n"
                    "Please print the correct template only."
                ) % (rec.offer_letter_type))

    def action_print_cmt_offer_letter(self):
        for record in self:
            missing_fields = []

            if not record.cmt_designation:
                missing_fields.append("CMT Designation")

            if not record.band_id:
                missing_fields.append("CMT Band")

            if not record.level_id:
                missing_fields.append("CMT Level")

            if not record.final_yearly_costs:
                missing_fields.append("Salary")

            # Applicant / Job / HR Details
            if not record.applicant_id:
                missing_fields.append("Applicant")

            elif not record.applicant_id.job_id:
                missing_fields.append("Job Position")

            else:
                if not record.applicant_id.ls_date_of_joining:
                    missing_fields.append("Date of Joining")

                # if not record.applicant_id.job_id.hr_head_name:
                #     missing_fields.append("HR Head Name")
                #
                # if not record.applicant_id.job_id.hr_description:
                #     missing_fields.append("HR Description")

            # Company Details
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
                    _("Please fill in the following fields before printing the CMT Offer Letter:\n\n- %s")
                    % "\n- ".join(missing_fields)
                )

            record._check_offer_template(
                'approval_recruitment.action_report_cmt_offer_letter_template'
            )

            return self.env.ref(
                'approval_recruitment.action_report_cmt_offer_letter_template'
            ).report_action(record)

    def action_print_hse_offer_letter(self):
        for record in self:
            missing_fields = []

            if not record.hse_designation:
                missing_fields.append("HSE Designation")

            if not record.hse_intern_hospital_name:
                missing_fields.append("HSE Intern (Hospital Name)")

            if not record.hse_intern_hospital_city:
                missing_fields.append("HSE Intern (Hospital City)")

            if not record.hse_band_id:
                missing_fields.append("HSE Band")

            if not record.hse_level_id:
                missing_fields.append("HSE Level")

            if not record.final_yearly_costs:
                missing_fields.append("Salary")

            # Applicant / Job / HR Details
            if not record.applicant_id:
                missing_fields.append("Applicant")

            elif not record.applicant_id.job_id:
                missing_fields.append("Job Position")

            else:
                if not record.applicant_id.ls_date_of_joining:
                    missing_fields.append("Date of Joining")

                # if not record.applicant_id.job_id.hr_head_name:
                #     missing_fields.append("HR Head Name")
                #
                # if not record.applicant_id.job_id.hr_description:
                #     missing_fields.append("HR Description")

            # Company Details
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
                        "the HSE Offer Letter:\n\n- %s"
                    )
                    % "\n- ".join(missing_fields)
                )

            record._check_offer_template(
                'approval_recruitment.action_report_hse_offer_letter_template'
            )

            return self.env.ref(
                'approval_recruitment.action_report_hse_offer_letter_template'
            ).report_action(record)

    def action_print_offer(self):
        for record in self:
            missing_fields = []

            if not record.designation:
                missing_fields.append("Offer Designation")

            if record.variable_pay_ctc is False:
                missing_fields.append("Variable Pay CTC")

            if not record.offer_hospital_name:
                missing_fields.append("Offer of Appointment (Hospital Name)")

            if not record.offer_hospital_city:
                missing_fields.append("Offer of Appointment (Hospital City)")

            if not record.offer_band_id:
                missing_fields.append("Offer Band")

            if not record.offer_level_id:
                missing_fields.append("Offer Level")

            if not record.final_yearly_costs:
                missing_fields.append("Salary")

            # Applicant / Job / HR Details
            if not record.applicant_id:
                missing_fields.append("Applicant")

            elif not record.applicant_id.job_id:
                missing_fields.append("Job Position")

            else:
                if not record.applicant_id.ls_date_of_joining:
                    missing_fields.append("Date of Joining")

                # if not record.applicant_id.job_id.hr_head_name:
                #     missing_fields.append("HR Head Name")
                #
                # if not record.applicant_id.job_id.hr_description:
                #     missing_fields.append("HR Description")

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
                    _("Please fill in the following fields before printing the Full Time Employee Offer Letter:\n\n- %s")
                    % "\n- ".join(missing_fields)
                )

            record._check_offer_template(
                'approval_recruitment.action_report_offer_of_appointment'
            )

            return self.env.ref(
                'approval_recruitment.action_report_offer_of_appointment'
            ).report_action(record)

    def action_print_internship(self):
        for record in self:
            missing_fields = []

            # Internship Details
            if not record.start_date:
                missing_fields.append("Start Date")

            if not record.end_date:
                missing_fields.append("End Date")

            if not record.department_id:
                missing_fields.append("Department")

            if not record.final_yearly_costs:
                missing_fields.append("Salary")

            # Applicant / Job / HR Details
            if not record.applicant_id:
                missing_fields.append("Applicant")

            elif not record.applicant_id.job_id:
                missing_fields.append("Job Position")

            else:
                pass
                # if not record.applicant_id.job_id.hr_head_name:
                #     missing_fields.append("HR Head Name")
                #
                # if not record.applicant_id.job_id.hr_description:
                #     missing_fields.append("HR Description")

            # Company Details
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

            # Validation Error
            if missing_fields:
                raise UserError(
                    _(
                        "Please fill in the following fields before printing "
                        "the Internship Letter:\n\n- %s"
                    )
                    % "\n- ".join(missing_fields)
                )

            # Check Template
            record._check_offer_template(
                'approval_recruitment.action_report_internship_letter'
            )

            # Print Report
            return self.env.ref(
                'approval_recruitment.action_report_internship_letter'
            ).report_action(record)


