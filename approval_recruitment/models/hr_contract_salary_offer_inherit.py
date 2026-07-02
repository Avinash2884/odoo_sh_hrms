from odoo import models, fields, api


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
        string="Special Allowance",
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

            # Annual Basic
            annual_basic = ctc * 0.40

            # Annual HRA
            annual_hra = annual_basic * 0.40

            # Monthly Basic
            monthly_basic = annual_basic / 12

            # Monthly HRA
            monthly_hra = annual_hra / 12

            # Monthly Employer PF
            if monthly_basic <= 15000:
                monthly_pf = monthly_basic * 0.12
            else:
                monthly_pf = 1800.0

            # Annual Gross
            annual_gross = ctc - (monthly_pf * 12)

            # Monthly Gross
            monthly_gross = annual_gross / 12

            # Monthly Special Allowance
            monthly_special = monthly_gross - monthly_basic - monthly_hra

            rec.basic_pay = monthly_basic
            rec.hra = monthly_hra
            rec.special_allowance = monthly_special
            rec.total_gross_pay = monthly_gross
            rec.employer_pf = monthly_pf


