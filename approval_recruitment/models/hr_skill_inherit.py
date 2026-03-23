from odoo import models, fields, api , _

class HRSkillInherit(models.Model):
    _inherit = 'hr.skill'
    _description = 'HR Skill Inherit'

    approval_request_id = fields.Many2one(comodel_name='approval.request', string="Approval Request")