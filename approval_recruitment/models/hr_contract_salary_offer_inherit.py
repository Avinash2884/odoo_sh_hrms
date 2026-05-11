from odoo import models, fields


class HrContractSalaryOffer(models.Model):
    _inherit = 'hr.contract.salary.offer'

    offer_letter_type = fields.Selection([
        ('cmt_full_time_appointment_letter', 'CMT Full Time Appointment Letter'),
        ('full_time_appointment_letter', 'Full Time Appointment Letter'),
        ('hse_time_appointment_letter', 'HSE Time Appointment Letter'),
        ('internship_letter', 'Internship Letter'),
        ('offer_of_appointment', 'Offer Of Appointment'),
        ('cmt_offer_of_internship_and_subsequent_appointment', 'CMT Offer Of Internship and Subsequent Appointment'),
        ('hse_offer_of_internship_and_subsequent_appointment', 'HSE Offer Of Internship and Subsequent Appointment'),
    ], string="Offer Letter Type")
    hospital_name = fields.Char(string="Hospital Name")
    hospital_city = fields.Char(string="Hospital City")

    #internship letter
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")

    #Full time appointment letter
    full_time_hospital_name = fields.Char(string="Hospital Name")
    full_time_hospital_city = fields.Char(string="Hospital City")

    #HSE appointment letter
    hse_hospital_name = fields.Char(string="Hospital Name")
    hse_hospital_city = fields.Char(string="Hospital City")

    #offer of appointment
    designation = fields.Char(string="Designation")
    variable_pay_ctc = fields.Float(string="Variable Pay CTC")
    offer_hospital_name = fields.Char(string="Hospital Name")
    offer_hospital_city = fields.Char(string="Hospital City")

    #cmt offer internship
    cmt_designation = fields.Char(string="Designation")

    # hse offer internship
    hse_designation = fields.Char(string="Designation")
    hse_intern_hospital_name = fields.Char(string="Hospital Name")
    hse_intern_hospital_city = fields.Char(string="Hospital City")

    # def write(self, vals):
    #     res = super().write(vals)
    #
    #     if 'state' in vals:
    #         for record in self:
    #             if record.state == 'full_signed':
    #                 template = self.env.ref('approval_recruitment.mail_template_offer_acceptance')
    #                 template.send_mail(record.id, force_send=True)
    #
    #     return res