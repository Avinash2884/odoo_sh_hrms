from odoo import models, fields, api


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    ls_employee_code = fields.Char(
        string='Employee ID',
        compute='_compute_employee_details',
        store=True
    )

    ls_department_id = fields.Many2one(
        'hr.department',
        string='Department',
        compute='_compute_employee_details',
        store=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id
    )
    approved_date = fields.Datetime(
        string="Approved On",
        readonly=True,
        copy=False
    )
    category_id = fields.Many2one('approval.category', string="Category", required=True)

    @api.depends('request_owner_id')
    def _compute_employee_details(self):
        for rec in self:
            rec.ls_employee_code = False
            rec.ls_department_id = False

            if rec.request_owner_id:
                employee = self.env['hr.employee'].search([
                    ('user_id', '=', rec.request_owner_id.id)
                ], limit=1)

                if employee:
                    rec.ls_employee_code = employee.ls_employee_id
                    rec.ls_department_id = employee.department_id.id
