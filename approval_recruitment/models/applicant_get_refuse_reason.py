from odoo import api, fields, models, _


class ApplicantGetRefuseReason(models.TransientModel):
    _inherit = 'applicant.get.refuse.reason'
    _description = 'Get Refuse Reason'

