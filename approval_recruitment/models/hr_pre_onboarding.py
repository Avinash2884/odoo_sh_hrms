from odoo import models, fields

class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    # --- Mandatory Identity ---
    aadhaar_no = fields.Char("Aadhaar Number")
    aadhaar_card = fields.Binary("Aadhaar Card Copy")
    pan_no = fields.Char("PAN Number")
    pan_card = fields.Binary("PAN Card Copy")

    # --- Bank Details ---
    bank_name = fields.Char("Bank Name")
    bank_acc_no = fields.Char("Account Number")
    bank_ifsc = fields.Char("IFSC Code")
    bank_branch = fields.Char("Branch Name")
    bank_doc = fields.Binary("Cancelled Cheque / Passbook")

    # --- Educational (Common for All) ---
    marksheet_10 = fields.Binary("10th Marksheet")
    marksheet_12 = fields.Binary("12th Marksheet")
    diploma_cert = fields.Binary("Diploma Certificate")
    ug_degree = fields.Binary("UG Degree Certificate")
    pg_degree = fields.Binary("PG Degree Certificate")

    # --- Experienced Specific ---
    payslips = fields.Binary("Last 3 Months Payslips")
    salary_revision_letter = fields.Binary("Salary Revision Letter")
    relieving_letter = fields.Binary("Relieving Letter")
    exp_appointment_letter = fields.Binary("Experience Letter")

    joining_category = fields.Selection([
        ('fresher', 'Fresher'),
        ('experienced', 'Experienced')
    ], string="Joining Category")