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

    @api.depends('final_yearly_costs')
    def _compute_salary_breakup(self):
        for rec in self:
            ctc = rec.final_yearly_costs or 0.0

            if not ctc:
                rec.basic_pay = 0.0
                rec.hra = 0.0
                rec.special_allowance = 0.0
                rec.total_gross_pay = 0.0
                rec.employer_pf = 0.0
                continue

            # Monthly Gross
            monthly_gross = ctc / 12

            # Salary Breakup
            monthly_basic = monthly_gross * 0.50
            monthly_hra = monthly_gross * 0.30
            monthly_special = monthly_gross * 0.20

            # Employer PF
            if monthly_basic > 15000:
                monthly_pf = 1800.0
            else:
                monthly_pf = monthly_basic * 0.12

            rec.total_gross_pay = monthly_gross
            rec.basic_pay = monthly_basic
            rec.hra = monthly_hra
            rec.special_allowance = monthly_special
            rec.employer_pf = monthly_pf

            rec.basic_pay_annual = monthly_basic * 12
            rec.hra_annual = monthly_hra * 12
            rec.special_allowance_annual = monthly_special * 12
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
        self._check_offer_template('approval_recruitment.action_report_cmt_offer_letter_template')
        return self.env.ref('approval_recruitment.action_report_cmt_offer_letter_template').report_action(self)

    def action_print_hse_offer_letter(self):
        self._check_offer_template('approval_recruitment.action_report_hse_offer_letter_template')
        return self.env.ref('approval_recruitment.action_report_hse_offer_letter_template').report_action(self)

    def action_print_offer(self):
        self._check_offer_template('approval_recruitment.action_report_offer_of_appointment')
        return self.env.ref('approval_recruitment.action_report_offer_of_appointment').report_action(self)

    def action_print_internship(self):
        self._check_offer_template('approval_recruitment.action_report_internship_letter')
        return self.env.ref('approval_recruitment.action_report_internship_letter').report_action(self)


