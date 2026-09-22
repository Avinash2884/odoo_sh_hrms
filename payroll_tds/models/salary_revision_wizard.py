from odoo import models, fields, api


class SalaryRevisionWizard(models.TransientModel):
    _name = 'salary.revision.wizard'
    _description = 'Salary Revision Wizard'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        readonly=True
    )

    effective_date = fields.Date(
        string='Revise Payslip Effective From',
        required=True
    )

    payout_month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='Payout Month', required=True)

    previous_salary = fields.Float(
        string='Previous Salary',
        readonly=True
    )

    new_salary = fields.Float(
        string='New Salary',
        required=True
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        employee_id = self.env.context.get('default_employee_id')

        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)

            if employee.exists():
                res['employee_id'] = employee.id
                res['previous_salary'] = employee.wage
                res['new_salary'] = employee.wage

        return res

    def action_save_revision(self):
        self.ensure_one()

        employee = self.employee_id

        if not employee:
            return False

        previous_salary = employee.wage
        new_salary = self.new_salary

        # Create Salary Revision record first
        self.env['employee.salary.revision'].create({
            'employee_id': employee.id,
            'effective_date': self.effective_date,
            'payout_month': self.payout_month,
            'previous_gross_wage': previous_salary,
            'revised_gross_wage': new_salary,
        })

        # Update employee wage
        employee.write({
            'wage': new_salary,
        })

        return {
            'type': 'ir.actions.act_window_close',
        }