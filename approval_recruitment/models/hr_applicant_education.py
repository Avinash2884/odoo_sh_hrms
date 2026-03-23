from odoo import models, fields

class HrApplicantEducation(models.Model):
    _name = 'hr.applicant.education'
    _description = 'Educational Qualification'

    applicant_id = fields.Many2one(
        'hr.applicant',
        string='Applicant',
        required=True,
        ondelete='cascade'
    )

    # ===== EDUCATION FIELDS =====
    exam_name = fields.Char(string="Exam / Qualification")
    passing_date = fields.Char(string="Passing Date")
    university = fields.Char(string="University / Institution")
    marks_percentage = fields.Float(string="Percentage / CGPA")
    main_subject = fields.Char(string="Main Subject")