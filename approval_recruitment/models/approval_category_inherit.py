from odoo import models, fields, api

CATEGORY_SELECTION = [
    ('required', 'Required'),
    ('optional', 'Optional'),
    ('no', 'None')]


class ApprovalCategoryInherit(models.Model):
    _inherit = 'approval.category'
    _description = 'Approval Category'

    has_total_no_of_positions = fields.Selection(CATEGORY_SELECTION, string="Total No of Position", default="no",
                                                 required=True)
    has_job_position = fields.Selection(CATEGORY_SELECTION, string="Job Position", default="no",
                                                 required=True)
    has_experience_min = fields.Selection(CATEGORY_SELECTION, string="Experience Minimum", default="no",
                                        required=True)
    has_experience_max = fields.Selection(CATEGORY_SELECTION, string="Experience Maximum", default="no",
                                        required=True)
    has_overall_budget_for_all_posting = fields.Selection(CATEGORY_SELECTION, string="Budget for All Posting", default="no",
                                        required=True)
    has_budget_for_each_employee_position = fields.Selection(CATEGORY_SELECTION, string="Budget for Per Employee",default="no",
                                                          required=True)
    has_start_date = fields.Selection(CATEGORY_SELECTION, string="Start Date",default="no",
                                                          required=True)
    has_end_date = fields.Selection(CATEGORY_SELECTION, string="End Date", default="no",
                                      required=True)

    hr_department_id = fields.Many2one('hr.department', string="HR Department")

    department_manager_id = fields.Many2one(
        'hr.employee',
        string="Department Manager",
        readonly=True
    )

    hr_employee_id = fields.Many2one(
        'hr.employee',
        string="HR",
        readonly=True
    )

    interviewer_ids = fields.Many2many(
        'res.users',
        'approval_category_interviewer_rel',
        'category_id',
        'user_id',
        string="Interviewers"
    )

    def _prepare_department_data(self, department):
        vals = {}
        approver_commands = []

        if not department:
            return vals, approver_commands

        # Manager & HR
        vals.update({
            'department_manager_id': department.manager_id.id if department.manager_id else False,
            'hr_employee_id': department.approval_hr_id.id if department.approval_hr_id else False,
        })

        sequence = 1

        # Manager approver
        if department.manager_id and department.manager_id.user_id:
            approver_commands.append((0, 0, {
                'user_id': department.manager_id.user_id.id,
                'required': True,
                'sequence': sequence,
            }))
            sequence += 1

        # HR approver
        if department.approval_hr_id and department.approval_hr_id.user_id:
            approver_commands.append((0, 0, {
                'user_id': department.approval_hr_id.user_id.id,
                'required': True,
                'sequence': sequence,
            }))

        return vals, approver_commands

    # -----------------------------
    # CREATE
    # -----------------------------
    @api.model
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        for vals in vals_list:
            if vals.get('hr_department_id'):
                department = self.env['hr.department'].browse(vals['hr_department_id'])

                dept_vals, approvers = self._prepare_department_data(department)

                vals.update(dept_vals)
                vals['approver_ids'] = [(5, 0, 0)] + approvers

        return super().create(vals_list)

    # -----------------------------
    # WRITE
    # -----------------------------
    def write(self, vals):
        # جلوگیری recursion
        if self.env.context.get('skip_auto_update'):
            return super().write(vals)

        res = super().write(vals)

        for rec in self:
            if rec.hr_department_id:
                department = rec.hr_department_id

                dept_vals, approvers = rec._prepare_department_data(department)

                update_vals = {
                    **dept_vals,
                    'approver_ids': [(5, 0, 0)] + approvers
                }

                # ✅ Prevent recursion using context
                rec.with_context(skip_auto_update=True).write(update_vals)

        return res






