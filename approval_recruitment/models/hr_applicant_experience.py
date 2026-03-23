from odoo import models, fields

class HrApplicantExperience(models.Model):
    _name = 'hr.applicant.experience'
    _description = 'Work Experience'

    applicant_id = fields.Many2one(
        'hr.applicant',
        string='Applicant',
        required=True,
        ondelete='cascade'
    )

    # ===== EXPERIENCE FIELDS =====
    employer_name = fields.Char(string="Employer Name & Address")
    from_date = fields.Char(string="From Date")
    to_date = fields.Char(string="To Date")
    designation = fields.Char(string="Position / Designation")
    duties = fields.Text(string="Nature of Duties")
    gross_salary = fields.Float(string="Gross Annual Salary")
    pay_scale = fields.Char(string="Pay Scale")