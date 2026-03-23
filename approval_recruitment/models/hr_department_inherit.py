from odoo import models, fields, api

class HrDepartmentInherit(models.Model):
    _inherit = 'hr.department'

    approval_hr_id = fields.Many2one('hr.employee',string='HR')
