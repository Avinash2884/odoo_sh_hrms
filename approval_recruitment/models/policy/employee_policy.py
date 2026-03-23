from odoo import models, fields


class EmployeePolicy(models.Model):
    _name = 'employee.policy'
    _description = 'Employee Policy Document'
    _inherit = ['mail.thread']

    name = fields.Char("Policy Name")
    document = fields.Binary("Policy Document")
    file_name = fields.Char("File Name")