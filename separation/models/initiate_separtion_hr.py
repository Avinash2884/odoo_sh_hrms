from datetime import timedelta

from odoo import models, fields, api, _

class InitiateSeparationHR(models.Model):
    _name = 'initiate.separation.hr'
    _description = 'Initiate Separation HR'
    _inherit = ['mail.thread']
    _rec_name = 'employee_id'
    _order = "create_date desc"

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        index=True,
        tracking=True,
    )
    ls_employee_id = fields.Char(string="Employee ID", related='employee_id.ls_employee_id', tracking=True)
    ls_designation_id = fields.Many2one('hr.job', 'Designation', related='employee_id.job_id', tracking=True)
    department_id = fields.Many2one('hr.department', 'Department', related='employee_id.department_id', tracking=True)
    joining_date_recruit = fields.Date(string="Date of Joining", copy=False, related='employee_id.joining_date_recruit',
                                       tracking=True)
    last_working_date = fields.Date(string="Last Working Date", copy=False, tracking=True,
                                    default=lambda self: fields.Date.today() + timedelta(days=30))
    resignation_reason = fields.Selection([
        ('career', 'Better Career Opportunity'),
        ('compensation', 'Compensation'),
        ('personal', 'Personal Reasons'),
        ('higher_studies', 'Higher Studies'),
        ('relocation', 'Relocation'),
        ('health', 'Health Reasons'),
        ('wlb', 'Work-Life Balance'),
        ('manager_issue', 'Managerial Issues'),
        ('other', 'Other')
    ], required=True, tracking=True)
    detailed_reason = fields.Text(string="Detailed Reason", tracking=True)

    def action_submit(self):
        for rec in self:
            self.env['initiate.separation'].create({
                'employee_id': rec.employee_id.id,
                'last_working_date': rec.last_working_date,
                'resignation_reason': rec.resignation_reason,
                'detailed_reason': rec.detailed_reason,
            })