from odoo import models, fields


class HrEmployeePublicEducation(models.Model):
    _name = "hr.employee.public.education"
    _description = "Public Employee Education"

    employee_public_id = fields.Many2one(
        "hr.employee.public",
        string="Employee",
        required=True,
        ondelete="cascade",
    )

    education_id = fields.Many2one(
        "hr.employee.education",
        string="Education",
        required=True,
        ondelete="cascade",
    )

    degree = fields.Char(
        string="Degree",
    )

    specialisation = fields.Char(
        string="Specialisation",
    )

    college_university = fields.Char(
        string="College / University",
    )