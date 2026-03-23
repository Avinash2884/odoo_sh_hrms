from odoo import models, fields

class HrJobInherit(models.Model):
    _inherit = 'hr.job'
    _description = 'HR Job'

    approval_experience_minimum = fields.Integer(string="Experience Min")
    approval_experience_maximum = fields.Integer(string="Experience Max")
    approval_overall_budget_for_all_posting = fields.Integer(string="Budget for All Posting")
    approval_budget_for_each_employee_position = fields.Integer(string="Budget for Per Employee")
    hr_head = fields.Many2one('hr.employee',string="HR head")
