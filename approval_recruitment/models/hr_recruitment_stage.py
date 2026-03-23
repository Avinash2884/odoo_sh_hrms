from odoo import models, fields

class HrRecruitmentStage(models.Model):
    _inherit = 'hr.recruitment.stage'

    job_ids = fields.Many2many(
        'hr.job',
        string="Applicable Job Positions",
        help="Stages applicable for selected job roles"
    )