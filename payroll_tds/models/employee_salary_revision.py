from datetime import date
from calendar import monthrange
from odoo import models, fields, api


class EmployeeSalaryRevision(models.Model):
    _name = 'employee.salary.revision'
    _description = 'Employee Salary Revision'
    _order = 'effective_date desc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        ondelete='cascade'
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

    # =====================================================
    # PREVIOUS WAGE
    # =====================================================

    previous_gross_wage = fields.Float(
        string='Previous Gross Wage'
    )

    previous_basic_percentage = fields.Float(
        string='Previous Basic %',
        default=50.0
    )

    previous_basic = fields.Float(
        string='Previous Basic Amount',
        compute='_compute_previous_salary',
        store=True
    )

    previous_hra = fields.Float(
        string='Previous HRA Amount',
        compute='_compute_previous_salary',
        store=True
    )

    previous_special_allowance = fields.Float(
        string='Previous Special Allowance Amount',
        compute='_compute_previous_salary',
        store=True
    )

    # =====================================================
    # REVISED WAGE
    # =====================================================

    revised_gross_wage = fields.Float(
        string='Revised Gross Wage'
    )

    fixed_basic_percentage = fields.Float(
        string='Revised Basic %',
        default=50.0
    )

    fixed_basic = fields.Float(
        string='Revised Basic Amount',
        compute='_compute_revised_salary',
        store=True
    )

    fixed_hra = fields.Float(
        string='Revised HRA Amount',
        compute='_compute_revised_salary',
        store=True
    )

    fixed_special_allowance = fields.Float(
        string='Revised Special Allowance Amount',
        compute='_compute_revised_salary',
        store=True
    )

    remarks = fields.Char(
        string='Remarks'
    )

    # =====================================================
    # ARREAR DETAILS
    # =====================================================

    salary_difference = fields.Float(
        string='Salary Difference',
        compute='_compute_salary_arrear',
        store=True
    )

    arrear_months = fields.Integer(
        string='Arrear Months',
        compute='_compute_salary_arrear',
        store=True
    )

    arrear_paid_days = fields.Float(
        string='Arrear Paid Days'
    )

    revised_salary_arrear = fields.Float(
        string='Revised Salary Arrear',
        compute='_compute_salary_arrear',
        store=True
    )

    basic_difference_arrear = fields.Float(
        string='Basic Difference Arrear',
        compute='_compute_salary_arrear',
        store=True
    )

    hra_difference_arrear = fields.Float(
        string='HRA Difference Arrear',
        compute='_compute_salary_arrear',
        store=True
    )

    special_allowance_difference_arrear = fields.Float(
        string='Special Allowance Difference Arrear',
        compute='_compute_salary_arrear',
        store=True
    )

    # =====================================================
    # PREVIOUS SALARY BREAKUP
    # =====================================================

    @api.depends(
        'previous_gross_wage',
        'previous_basic_percentage'
    )
    def _compute_previous_salary(self):
        for rec in self:

            gross = rec.previous_gross_wage or 0.0

            basic = gross * (
                rec.previous_basic_percentage / 100.0
            )

            hra = gross * 0.30

            special = gross - basic - hra

            rec.previous_basic = basic
            rec.previous_hra = hra
            rec.previous_special_allowance = special

    # =====================================================
    # REVISED SALARY BREAKUP
    # =====================================================

    @api.depends(
        'revised_gross_wage',
        'fixed_basic_percentage'
    )
    def _compute_revised_salary(self):
        for rec in self:

            gross = rec.revised_gross_wage or 0.0

            basic = gross * (
                rec.fixed_basic_percentage / 100.0
            )

            hra = gross * 0.30

            special = gross - basic - hra

            rec.fixed_basic = basic
            rec.fixed_hra = hra
            rec.fixed_special_allowance = special

    # =====================================================
    # ARREAR CALCULATION
    # =====================================================

    @api.depends(
        'previous_gross_wage',
        'revised_gross_wage',
        'previous_basic',
        'previous_hra',
        'previous_special_allowance',
        'fixed_basic',
        'fixed_hra',
        'fixed_special_allowance',
        'effective_date',
        'payout_month',
        'arrear_paid_days'
    )
    def _compute_salary_arrear(self):

        for rec in self:

            rec.salary_difference = 0.0
            rec.arrear_months = 0
            rec.revised_salary_arrear = 0.0
            rec.basic_difference_arrear = 0.0
            rec.hra_difference_arrear = 0.0
            rec.special_allowance_difference_arrear = 0.0

            if not rec.employee_id or not rec.effective_date or not rec.payout_month:
                continue

            salary_difference = rec.revised_gross_wage - rec.previous_gross_wage
            basic_difference = rec.fixed_basic - rec.previous_basic
            hra_difference = rec.fixed_hra - rec.previous_hra
            special_difference = (
                    rec.fixed_special_allowance -
                    rec.previous_special_allowance
            )

            rec.salary_difference = salary_difference

            effective_month = rec.effective_date.month
            payout_month = int(rec.payout_month)
            year = rec.effective_date.year

            arrear_months = max(
                payout_month - effective_month,
                0
            )

            rec.arrear_months = arrear_months

            if arrear_months == 0:
                rec.revised_salary_arrear = salary_difference
                rec.basic_difference_arrear = basic_difference
                rec.hra_difference_arrear = hra_difference
                rec.special_allowance_difference_arrear = special_difference
                continue

            salary_arrear = 0.0
            basic_arrear = 0.0
            hra_arrear = 0.0
            special_arrear = 0.0

            current_month = effective_month

            while current_month < payout_month:

                total_days = monthrange(year, current_month)[1]

                # Manual value only for Effective Month
                if (
                        current_month == effective_month
                        and rec.arrear_paid_days > 0
                ):
                    paid_days = rec.arrear_paid_days

                else:
                    paid_days = rec._get_paid_days_for_month(
                        year,
                        current_month
                    )

                salary_arrear += (
                                         salary_difference / total_days
                                 ) * paid_days

                basic_arrear += (
                                        basic_difference / total_days
                                ) * paid_days

                hra_arrear += (
                                      hra_difference / total_days
                              ) * paid_days

                special_arrear += (
                                          special_difference / total_days
                                  ) * paid_days

                current_month += 1

            rec.revised_salary_arrear = salary_arrear
            rec.basic_difference_arrear = basic_arrear
            rec.hra_difference_arrear = hra_arrear
            rec.special_allowance_difference_arrear = special_arrear


    @api.onchange('employee_id', 'effective_date')
    def _onchange_arrear_paid_days(self):
        if not self.employee_id or not self.effective_date:
            self.arrear_paid_days = 0
            return

        self.arrear_paid_days = self._get_paid_days_for_month(
            self.effective_date.year,
            self.effective_date.month
        )

    def _get_paid_days_for_month(self, year, month):

        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])

        payslip = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date_from', '<=', end_date),
            ('date_to', '>=', start_date),
        ], limit=1)

        total_days = monthrange(year, month)[1]

        if not payslip:
            print("No Payslip Found")
            return total_days

        print("===================================")
        print("Payslip :", payslip.display_name)
        print("===================================")

        unpaid_days = 0.0

        for line in payslip.worked_days_line_ids:

            print(
                "Name :", line.name,
                " Code :", line.code,
                " Days :", line.number_of_days
            )

            if line.code == "LEAVE90":
                unpaid_days += line.number_of_days

        paid_days = total_days - unpaid_days

        print("Total Days :", total_days)
        print("Unpaid Days :", unpaid_days)
        print("Paid Days :", paid_days)
        print("===================================")

        return max(paid_days, 0)

    def _update_employee_arrear(self):
        for rec in self:
            if not rec.employee_id:
                continue

            rec.employee_id.write({
                'basic_arrear': rec.basic_difference_arrear,
                'hra_arrear': rec.hra_difference_arrear,
                'special_allowance_arrear': rec.special_allowance_difference_arrear,

                # Salary Difference
                'salary_arrear': rec.salary_difference,
            })

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._update_employee_arrear()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._update_employee_arrear()
        return res