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

    # =========================================================
    # CREATE - New education
    # =========================================================

    @api.model_create_multi
    def create(self, vals_list):

        records = super().create(vals_list)

        self._sync_public_education(records)

        return records

    # =========================================================
    # WRITE - Existing education updated
    # =========================================================

    def write(self, vals):

        result = super().write(vals)

        fields_to_sync = {
            "ls_degree",
            "specialisation",
            "college_university_name",
            "employee_id",
        }

        if fields_to_sync.intersection(vals):
            self._sync_public_education(self)

        return result

    # =========================================================
    # UNLINK - Delete public education also
    # =========================================================

    def unlink(self):

        PublicEducation = self.env[
            "hr.employee.public.education"
        ].sudo()

        PublicEducation.search([
            ("education_id", "in", self.ids)
        ]).unlink()

        return super().unlink()

    # =========================================================
    # SYNC METHOD
    # =========================================================

    def _sync_public_education(self, education_records):

        PublicEmployee = self.env[
            "hr.employee.public"
        ].sudo()

        PublicEducation = self.env[
            "hr.employee.public.education"
        ].sudo()

        for education in education_records:

            employee = education.employee_id

            if not employee:
                continue

            public_employee = PublicEmployee.browse(
                employee.id
            )

            if not public_employee.exists():
                continue

            public_education = PublicEducation.search([
                ("education_id", "=", education.id)
            ], limit=1)

            vals = {
                "employee_public_id": public_employee.id,
                "education_id": education.id,
                "degree": education.ls_degree or "",
                "specialisation": education.specialisation or "",
                "college_university": (
                        education.college_university_name or ""
                ),
            }

            if public_education:
                public_education.write(vals)
            else:
                PublicEducation.create(vals)