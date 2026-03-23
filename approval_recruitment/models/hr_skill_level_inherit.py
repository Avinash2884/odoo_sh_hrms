from odoo import models, fields, api , _

class HRSkillLevelInherit(models.Model):
    _inherit = 'hr.skill.level'
    _description = 'HR Skill Level Inherit'

    approval_request_id = fields.Many2one(comodel_name='approval.request', string="Approval Request")