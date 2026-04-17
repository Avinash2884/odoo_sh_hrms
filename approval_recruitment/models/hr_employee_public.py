import re

from odoo import models, fields, api, _


class HrEmployeeInherit(models.Model):
    _inherit = 'hr.employee.public'
    _description = 'HR Employee Public'

    joining_date_recruit = fields.Date(related='employee_id.joining_date_recruit', readonly=True)
    date_of_confirmation = fields.Date(related='employee_id.date_of_confirmation', readonly=True)

    # ✅ IMPORTANT: Match SAME TYPE as hr.employee
    hr_id = fields.Many2one(
        'hr.employee',
        related='employee_id.hr_id',
        readonly=True
    )
    hr_head_id = fields.Many2one(
        'hr.employee',
        related='employee_id.hr_head_id',
        readonly=True
    )
    it_asset_head_id = fields.Many2one(
        'hr.employee',
        related='employee_id.it_asset_head_id',
        readonly=True
    )
    admin_head_id = fields.Many2one(
        'hr.employee',
        related='employee_id.admin_head_id',
        readonly=True
    )
    payroll_head_id = fields.Many2one(
        'hr.employee',
        related='employee_id.payroll_head_id',
        readonly=True
    )


    probation_status = fields.Selection(related='employee_id.probation_status', readonly=True)
    probation_reason = fields.Text(related='employee_id.probation_reason', readonly=True)
    probation_date_start = fields.Date(related='employee_id.probation_date_start', readonly=True)
    probation_date_end = fields.Date(related='employee_id.probation_date_end', readonly=True)

    buddy_id = fields.Many2one('res.users', related='employee_id.buddy_id', readonly=True)
    ls_employee_id = fields.Char(related='employee_id.ls_employee_id', readonly=True)

    hr_contract_type_id = fields.Many2one('hr.contract.type', related='employee_id.hr_contract_type_id', readonly=True)
    entity_name_id = fields.Many2one('entity.name', related='employee_id.entity_name_id', readonly=True)
    base_location_id = fields.Many2one('base.location', related='employee_id.base_location_id', readonly=True)
    deputed_location_id = fields.Many2one('deputed.location', related='employee_id.deputed_location_id', readonly=True)

    band_id = fields.Many2one('band', related='employee_id.band_id', readonly=True)
    level_id = fields.Many2one('level', related='employee_id.level_id', readonly=True)
    vertical_id = fields.Many2one('vertical', related='employee_id.vertical_id', readonly=True)
    function_id = fields.Many2one('function', related='employee_id.function_id', readonly=True)

    parent_account_id = fields.Many2one('parent.account', related='employee_id.parent_account_id', readonly=True)
    account_office_name_id = fields.Many2one('account.office.name', related='employee_id.account_office_name_id', readonly=True)
    region_id = fields.Many2one('region', related='employee_id.region_id', readonly=True)

    employee_status_id = fields.Many2one('employee.status', related='employee_id.employee_status_id', readonly=True)
    ls_designation_id = fields.Many2one('designation', related='employee_id.ls_designation_id', readonly=True)
    ls_role_id = fields.Many2one('ls.role', related='employee_id.ls_role_id', readonly=True)
    ls_source_of_hire_id = fields.Many2one('source.of.hire', related='employee_id.ls_source_of_hire_id', readonly=True)

    blood_group_id = fields.Many2one('blood.group', related='employee_id.blood_group_id', readonly=True)

    current_experience = fields.Integer(related='employee_id.current_experience', readonly=True)
    previous_experience = fields.Integer(related='employee_id.previous_experience', readonly=True)
    total_experience = fields.Integer(related='employee_id.total_experience', readonly=True)

    age = fields.Integer(related='employee_id.age', readonly=True)

    guardian_type = fields.Selection(related='employee_id.guardian_type', readonly=True)
    father_name = fields.Char(related='employee_id.father_name', readonly=True)
    father_mobile = fields.Char(related='employee_id.father_mobile', readonly=True)
    mother_name = fields.Char(related='employee_id.mother_name', readonly=True)
    mother_mobile = fields.Char(related='employee_id.mother_mobile', readonly=True)

    guardian_relationship = fields.Char(related='employee_id.guardian_relationship', readonly=True)
    guardian_name = fields.Char(related='employee_id.guardian_name', readonly=True)
    guardian_mobile = fields.Char(related='employee_id.guardian_mobile', readonly=True)

    ls_aadhar = fields.Char(related='employee_id.ls_aadhar', readonly=True)
    ls_pan = fields.Char(related='employee_id.ls_pan', readonly=True)
    ls_uan = fields.Char(related='employee_id.ls_uan', readonly=True)

    ls_date_of_exit = fields.Date(related='employee_id.ls_date_of_exit', readonly=True)
    ls_date_of_resignation = fields.Date(related='employee_id.ls_date_of_resignation', readonly=True)

    dependant_name_1 = fields.Char(related='employee_id.dependant_name_1', readonly=True)
    dependant_dob_1 = fields.Char(related='employee_id.dependant_dob_1', readonly=True)
    relationship_status_1 = fields.Char(related='employee_id.relationship_status_1', readonly=True)

    dependant_name_2 = fields.Char(related='employee_id.dependant_name_2', readonly=True)
    dependant_dob_2 = fields.Char(related='employee_id.dependant_dob_2', readonly=True)
    relationship_status_2 = fields.Char(related='employee_id.relationship_status_2', readonly=True)

    dependant_name_3 = fields.Char(related='employee_id.dependant_name_3', readonly=True)
    dependant_dob_3 = fields.Char(related='employee_id.dependant_dob_3', readonly=True)
    relationship_status_3 = fields.Char(related='employee_id.relationship_status_3', readonly=True)

    permanent_street = fields.Char(related='employee_id.permanent_street', readonly=True)
    permanent_street2 = fields.Char(related='employee_id.permanent_street2', readonly=True)
    permanent_city = fields.Char(related='employee_id.permanent_city', readonly=True)
    permanent_state_id = fields.Many2one('res.country.state', related='employee_id.permanent_state_id', readonly=True)
    permanent_zip = fields.Char(related='employee_id.permanent_zip', readonly=True)
    permanent_country_id = fields.Many2one('res.country', related='employee_id.permanent_country_id', readonly=True)

    probation_extension_count = fields.Integer(related='employee_id.probation_extension_count', readonly=True)

    nominee_name = fields.Char(related='employee_id.nominee_name', readonly=True)
    relationship = fields.Selection(related='employee_id.relationship', readonly=True)

    pf_percentage = fields.Float(related='employee_id.pf_percentage', readonly=True)
    pf_payment_mode = fields.Selection(related='employee_id.pf_payment_mode', readonly=True)