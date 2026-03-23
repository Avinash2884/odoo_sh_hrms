from odoo import models, fields

class EmployeeStatus(models.Model):
    _name = 'employee.status'
    _description = 'Employee Status'

    name = fields.Char(string="Name", required=True)