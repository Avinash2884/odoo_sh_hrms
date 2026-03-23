from odoo import models, fields, api, _


class HrEmployeeEducation(models.Model):
    _name = 'hr.employee.education'
    _description = 'Employee Education'

    employee_id = fields.Many2one('hr.employee', ondelete='cascade')

    ls_degree = fields.Selection([
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('doctor', 'Doctor'),
        ('other', 'Other'),
    ], string="Degree")

    specialisation = fields.Char(string="Specialisation")
    college_university_name = fields.Char(string="College / University")