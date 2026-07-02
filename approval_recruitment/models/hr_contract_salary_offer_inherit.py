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
    cmt_designation = fields.Many2one('hr.job',string="Designation")
    band_id = fields.Many2one('band',string="Band")
    level_id = fields.Many2one('level',string="Level")


    # hse offer internship
    hse_designation = fields.Many2one('hr.job',string="Designation")
    hse_intern_hospital_name = fields.Char(string="HSE Intern (Hospital Name)")
    hse_intern_hospital_city = fields.Char(string="HSE Intern (Hospital City)")
    hse_band_id = fields.Many2one('band', string="Band")
    hse_level_id = fields.Many2one('level', string="Level")

    # offer of appointment
    designation = fields.Many2one('hr.job',string="Designation")
    variable_pay_ctc = fields.Float(string="Variable Pay CTC")
    offer_hospital_name = fields.Char(string="Offer of Appointment (Hospital Name)")
    offer_hospital_city = fields.Char(string="Offer of Appointment (Hospital City)")
    offer_band_id = fields.Many2one('band', string="Band")
    offer_level_id = fields.Many2one('level', string="Level")

    # internship letter
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")

    manual_ctc = fields.Float(string="Employer Budget (CTC)")

    # -------------------------------
    # Salary Breakdown
    # -------------------------------
    basic = fields.Float(compute="_compute_salary", store=True)
    hra = fields.Float(compute="_compute_salary", store=True)
    special_allowance = fields.Float(compute="_compute_salary", store=True)
    employer_pf = fields.Float(compute="_compute_salary", store=True)
    monthly_ctc = fields.Float(compute="_compute_salary", store=True)

    # -------------------------------
    # ✅ COMPUTE METHOD (FIXED)
    # -------------------------------
    @api.depends('manual_ctc')
    def _compute_salary(self):
        for rec in self:

            ctc = rec.manual_ctc or 0.0

            if not ctc:
                rec.basic = 0.0
                rec.hra = 0.0
                rec.special_allowance = 0.0
                rec.employer_pf = 0.0
                rec.monthly_ctc = 0.0
                continue

            basic = ctc * 0.5
            hra = basic * 0.4

            if basic <= 15000:
                pf = basic * 0.12
            else:
                pf = 1800

            special = ctc - (basic + hra + pf)

            rec.basic = basic
            rec.hra = hra
            rec.employer_pf = pf
            rec.special_allowance = special
            rec.monthly_ctc = ctc / 12