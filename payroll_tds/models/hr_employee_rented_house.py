from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


# =============================================================
# MONTH-WISE HRA LINE
# =============================================================

class HrEmployeeRentedHouseMonth(models.Model):
    _name = 'hr.employee.rented.house.month'
    _description = 'HRA Rented House Monthly Calculation'
    _order = 'month_date asc, id asc'

    rented_house_id = fields.Many2one(
        'hr.employee.rented.house',
        string='Rented House',
        required=True,
        ondelete='cascade',
        index=True,
    )

    month_date = fields.Date(
        string='Month',
        required=True,
        index=True,
    )

    month_name = fields.Char(
        string='Months',
        compute='_compute_month_name',
        store=True,
    )

    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Payslip',
        readonly=True,
    )

    payslip_found = fields.Boolean(
        string='Payslip Available',
        readonly=True,
    )

    basic_salary = fields.Monetary(
        string='Basic',
        currency_field='currency_id',
        readonly=True,
    )

    basic_50_percent = fields.Monetary(
        string='% of Earned Basic',
        currency_field='currency_id',
        readonly=True,
    )

    hra_salary = fields.Monetary(
        string='HRA Received',
        currency_field='currency_id',
        readonly=True,
    )

    rent_paid = fields.Monetary(
        string='Rent Paid',
        currency_field='currency_id',
        readonly=True,
    )

    rent_less_10_basic = fields.Monetary(
        string='Rent - 10% Basic',
        currency_field='currency_id',
        readonly=True,
    )

    hra_exemption = fields.Monetary(
        string='HRA Exemption',
        currency_field='currency_id',
        readonly=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='rented_house_id.currency_id',
        store=True,
        readonly=True,
    )

    @api.depends('month_date')
    def _compute_month_name(self):
        for record in self:
            record.month_name = (
                record.month_date.strftime('%b %Y')
                if record.month_date
                else False
            )


# =============================================================
# RENTED HOUSE / HRA
# =============================================================

class HrEmployeeRentedHouse(models.Model):
    _name = 'hr.employee.rented.house'
    _description = 'Employee Rented House Details'
    _order = 'rent_start_date desc, id desc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )

    rent_start_date = fields.Date(
        string='Rental Period From',
        required=True,
    )

    rent_end_date = fields.Date(
        string='Rental Period To',
        required=True,
    )

    monthly_rent = fields.Monetary(
        string='Amount / Month',
        currency_field='currency_id',
        required=True,
    )

    total_rent = fields.Monetary(
        string='Total Rent',
        currency_field='currency_id',
        compute='_compute_total_rent',
        store=True,
    )

    address = fields.Text(
        string='Address'
    )

    landlord_name = fields.Char(
        string='Landlord Name'
    )

    urbanization_type = fields.Selection(
        [
            ('metro', 'Metro'),
            ('non_metro', 'Non Metro'),
        ],
        string='Urbanization Type',
    )

    landlord_pan = fields.Char(
        string='Landlord PAN'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='employee_id.currency_id',
        store=True,
        readonly=True,
    )

    # =========================================================
    # VALIDATION
    # =========================================================

    @api.constrains('rent_start_date', 'rent_end_date')
    def _check_rental_period(self):
        for record in self:
            if (
                record.rent_start_date
                and record.rent_end_date
                and record.rent_end_date < record.rent_start_date
            ):
                raise ValidationError(
                    'Rental Period To must be greater than or equal to '
                    'Rental Period From.'
                )

    @api.constrains('monthly_rent', 'landlord_pan')
    def _check_landlord_pan(self):
        for record in self:
            if (
                record.monthly_rent
                and record.monthly_rent >= 100000
                and not record.landlord_pan
            ):
                raise ValidationError(
                    'Landlord PAN is mandatory when Amount / Month '
                    'is ₹1,00,000 or more.'
                )

    # =========================================================
    # DOCUMENTS
    # =========================================================

    rent_receipt = fields.Binary(
        string='Rent Receipt',
        attachment=True,
    )

    rental_agreement = fields.Binary(
        string='Rental Agreement',
        attachment=True,
    )

    pan_declaration = fields.Binary(
        string='PAN Declaration',
        attachment=True,
    )

    # =========================================================
    # EMPLOYEE JOINING DATE
    # =========================================================

    employee_joining_date = fields.Date(
        string='Employee Joining Date',
        related='employee_id.contract_date_start',
        readonly=True,
    )

    calculation_start_date = fields.Date(
        string='Calculation Start Date',
        compute='_compute_calculation_period',
        store=True,
    )

    eligible_months = fields.Integer(
        string='Eligible Months',
        compute='_compute_calculation_period',
        store=True,
    )

    # =========================================================
    # CURRENT BASIC
    #
    # Basic comes directly from:
    # l10n_in_basic_salary_amount
    # =========================================================

    monthly_basic = fields.Monetary(
        string='Current Basic / Month',
        currency_field='currency_id',
        related='employee_id.l10n_in_basic_salary_amount',
        readonly=True,
    )

    # =========================================================
    # CURRENT HRA
    #
    # IMPORTANT:
    # Full HRA comes directly from:
    # l10n_in_hra
    #
    # Do NOT apply 50% / 40% to this field.
    # =========================================================

    monthly_hra = fields.Monetary(
        string='Current HRA / Month',
        currency_field='currency_id',
        related='employee_id.l10n_in_hra',
        readonly=True,
    )

    # =========================================================
    # METRO / NON-METRO %
    #
    # Metro     = 50% of Basic
    # Non Metro = 40% of Basic
    #
    # This percentage is ONLY used for
    # "% of Earned Basic".
    #
    # It does NOT reduce HRA Received.
    # =========================================================

    hra_percentage = fields.Float(
        string='HRA %',
        compute='_compute_hra_percentage',
        store=True,
        readonly=True,
    )

    @api.depends('urbanization_type')
    def _compute_hra_percentage(self):
        for record in self:

            if record.urbanization_type == 'metro':
                record.hra_percentage = 50.0

            elif record.urbanization_type == 'non_metro':
                record.hra_percentage = 40.0

            else:
                record.hra_percentage = 0.0

    # =========================================================
    # TOTALS
    # =========================================================

    earned_basic = fields.Monetary(
        string='Total % of Earned Basic',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
    )

    hra_amount = fields.Monetary(
        string='Total HRA',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
    )

    total_hra_exemption = fields.Monetary(
        string='Total HRA Exemption',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
    )

    least_hra_exemption = fields.Monetary(
        string='Least Amount for HRA Tax Exemption',
        currency_field='currency_id',
        compute='_compute_least_hra_exemption',
        store=True,
    )

    @api.depends(
        'monthly_line_ids',
        'monthly_line_ids.basic_50_percent',
        'monthly_line_ids.hra_salary',
        'monthly_line_ids.rent_less_10_basic',
    )
    def _compute_least_hra_exemption(self):
        for record in self:
            earned_basic = sum(
                record.monthly_line_ids.mapped(
                    'basic_50_percent'
                )
            )

            hra_received = sum(
                record.monthly_line_ids.mapped(
                    'hra_salary'
                )
            )

            excess_rent = sum(
                record.monthly_line_ids.mapped(
                    'rent_less_10_basic'
                )
            )

            # Least of the three values
            record.least_hra_exemption = min(
                earned_basic,
                hra_received,
                excess_rent,
            )
    # =========================================================
    # MONTHLY LINES
    # =========================================================

    monthly_line_ids = fields.One2many(
        'hr.employee.rented.house.month',
        'rented_house_id',
        string='Monthly HRA Calculation',
        copy=False,
    )

    # =========================================================
    # CREATE
    # =========================================================

    @api.model_create_multi
    def create(self, vals_list):

        records = super().create(vals_list)

        for record in records:
            record._rebuild_monthly_lines()

        return records

    # =========================================================
    # WRITE
    # =========================================================

    def write(self, vals):

        result = super().write(vals)

        rebuild_fields = {
            'employee_id',
            'rent_start_date',
            'rent_end_date',
            'monthly_rent',
            'urbanization_type',
        }

        if rebuild_fields.intersection(vals.keys()):

            for record in self:
                record._rebuild_monthly_lines()

        return result

    # =========================================================
    # MANUAL REFRESH BUTTON
    # =========================================================

    def action_recalculate_hra(self):

        for record in self:
            record._rebuild_monthly_lines()

        return True

    # =========================================================
    # CALCULATION PERIOD
    # =========================================================

    @api.depends(
        'rent_start_date',
        'rent_end_date',
        'employee_id',
        'employee_id.contract_date_start',
    )
    def _compute_calculation_period(self):

        for record in self:

            record.calculation_start_date = False
            record.eligible_months = 0

            if not record.rent_start_date or not record.rent_end_date:
                continue

            joining_date = record.employee_id.contract_date_start

            calculation_start = record.rent_start_date

            if joining_date and joining_date > calculation_start:
                calculation_start = joining_date

            if calculation_start > record.rent_end_date:
                continue

            record.calculation_start_date = calculation_start

            record.eligible_months = (
                (record.rent_end_date.year - calculation_start.year) * 12
                + record.rent_end_date.month
                - calculation_start.month
                + 1
            )

    # =========================================================
    # FIND DONE / PAID PAYSLIP FOR PARTICULAR MONTH
    # =========================================================

    def _get_paid_payslip(self, employee, month_date):

        if not employee or not month_date:
            return self.env['hr.payslip']

        month_start = month_date.replace(day=1)

        next_month = month_start + relativedelta(months=1)

        month_end = next_month - relativedelta(days=1)

        payslip = self.env['hr.payslip'].search(
            [
                ('employee_id', '=', employee.id),
                ('date_from', '<=', month_end),
                ('date_to', '>=', month_start),
                ('state', 'in', ['done', 'paid']),
            ],
            order='date_to desc, id desc',
            limit=1,
        )

        return payslip

    # =========================================================
    # GET BASIC FROM PAYSLIP
    #
    # This method is kept for existing monthly calculation.
    # But if payslip value is not available, employee
    # l10n_in_basic_salary_amount is used.
    # =========================================================

    def _get_basic_from_payslip(self, payslip):

        if not payslip:
            return 0.0

        basic_line = payslip.line_ids.filtered(
            lambda line: line.code == 'BASIC'
        )[:1]

        if basic_line:
            return basic_line.total

        return 0.0

    # =========================================================
    # GET HRA FROM PAYSLIP
    #
    # Kept for compatibility with existing code.
    # But the main calculation below uses employee
    # l10n_in_hra as requested.
    # =========================================================

    def _get_hra_from_payslip(self, payslip):

        if not payslip:
            return 0.0

        hra_line = payslip.line_ids.filtered(
            lambda line: line.code == 'HRA'
        )[:1]

        if hra_line:
            return hra_line.total

        return 0.0

    # =========================================================
    # FINANCIAL YEAR START
    #
    # April to March
    # =========================================================

    def _get_financial_year_start(self):

        self.ensure_one()

        if not self.rent_start_date:
            return False

        if self.rent_start_date.month >= 4:

            return self.rent_start_date.replace(
                month=4,
                day=1,
            )

        return self.rent_start_date.replace(
            year=self.rent_start_date.year - 1,
            month=4,
            day=1,
        )

    # =========================================================
    # PREPARE FINANCIAL YEAR LINES
    # =========================================================

    def _prepare_financial_year_lines(self):

        self.ensure_one()

        if not self.employee_id:
            return []

        if not self.rent_start_date:
            return []

        if not self.rent_end_date:
            return []

        financial_year_start = self._get_financial_year_start()

        if not financial_year_start:
            return []

        employee = self.employee_id

        joining_date = employee.contract_date_start

        values_list = []

        # =====================================================
        # 12 MONTHS - APRIL TO MARCH
        # =====================================================

        for month_number in range(12):

            current_month = (
                financial_year_start
                + relativedelta(months=month_number)
            )

            month_start = current_month.replace(day=1)

            month_end = (
                month_start
                + relativedelta(months=1)
                - relativedelta(days=1)
            )

            # =================================================
            # CHECK RENT ACTIVE
            # =================================================

            rent_active = True

            # Employee has not joined yet.
            if joining_date and month_end < joining_date:
                rent_active = False

            # Rental period has not started.
            if (
                self.rent_start_date
                and month_end < self.rent_start_date
            ):
                rent_active = False

            # Rental period has ended.
            if (
                self.rent_end_date
                and month_start > self.rent_end_date
            ):
                rent_active = False

            # =================================================
            # OUTSIDE RENTAL PERIOD
            # =================================================

            if not rent_active:

                values_list.append({
                    'rented_house_id': self.id,
                    'month_date': month_start,
                    'payslip_id': False,
                    'payslip_found': False,
                    'basic_salary': 0.0,
                    'basic_50_percent': 0.0,
                    'hra_salary': 0.0,
                    'rent_paid': 0.0,
                    'rent_less_10_basic': 0.0,
                    'hra_exemption': 0.0,
                })

                continue

            # =================================================
            # RENT PAID
            # =================================================

            rent_paid = self.monthly_rent or 0.0

            # =================================================
            # FIND PAYSLIP
            # =================================================

            payslip = self._get_paid_payslip(
                employee,
                month_start,
            )

            payslip_found = bool(payslip)

            # =================================================
            # BASIC
            #
            # Requirement:
            # Basic = employee.l10n_in_basic_salary_amount
            #
            # We use employee Basic directly.
            # =================================================

            basic = (
                employee.l10n_in_basic_salary_amount
                or 0.0
            )

            # =================================================
            # % OF EARNED BASIC
            #
            # Metro:
            #     Basic × 50%
            #
            # Non Metro:
            #     Basic × 40%
            # =================================================

            percentage = self.hra_percentage or 0.0

            basic_percentage_amount = (
                basic * percentage / 100.0
            )

            # =================================================
            # HRA RECEIVED
            #
            # IMPORTANT:
            #
            # FULL HRA:
            #     employee.l10n_in_hra
            #
            # DO NOT multiply HRA by 50% or 40%.
            # =================================================

            hra = (
                employee.l10n_in_hra
                or 0.0
            )

            # =================================================
            # RENT - 10% BASIC
            # =================================================

            rent_less_10_basic = max(
                rent_paid - (basic * 0.10),
                0.0,
            )

            # =================================================
            # HRA EXEMPTION
            #
            # Least of:
            #
            # 1. Full Actual HRA
            # 2. 50% / 40% of Basic
            # 3. Rent - 10% Basic
            # =================================================

            hra_exemption = min(
                hra,
                basic_percentage_amount,
                rent_less_10_basic,
            )

            # =================================================
            # MONTHLY VALUES
            # =================================================

            values_list.append({
                'rented_house_id': self.id,
                'month_date': month_start,
                'payslip_id': payslip.id if payslip else False,
                'payslip_found': payslip_found,

                # Full Basic
                'basic_salary': basic,

                # 50% Metro / 40% Non Metro
                'basic_50_percent': basic_percentage_amount,

                # FULL HRA
                'hra_salary': hra,

                # Monthly Rent
                'rent_paid': rent_paid,

                # Rent - 10% Basic
                'rent_less_10_basic': rent_less_10_basic,

                # Least of 3
                'hra_exemption': hra_exemption,
            })

        return values_list

    # =========================================================
    # CREATE ACTUAL DATABASE LINES
    # =========================================================

    def _rebuild_monthly_lines(self):

        Month = self.env['hr.employee.rented.house.month']

        for record in self:

            # Delete old lines.
            record.monthly_line_ids.unlink()

            # Create new lines.
            values_list = (
                record._prepare_financial_year_lines()
            )

            if values_list:
                Month.create(values_list)

    # =========================================================
    # TOTAL RENT
    # =========================================================

    @api.depends(
        'monthly_rent',
        'rent_start_date',
        'rent_end_date',
        'employee_id.contract_date_start',
    )
    def _compute_total_rent(self):

        for record in self:

            record.total_rent = 0.0

            if not (
                record.monthly_rent
                and record.rent_start_date
                and record.rent_end_date
            ):
                continue

            joining_date = (
                record.employee_id.contract_date_start
            )

            calculation_start = record.rent_start_date

            if (
                joining_date
                and joining_date > calculation_start
            ):
                calculation_start = joining_date

            if calculation_start > record.rent_end_date:
                continue

            months = (
                (record.rent_end_date.year - calculation_start.year)
                * 12
                + record.rent_end_date.month
                - calculation_start.month
                + 1
            )

            record.total_rent = (
                record.monthly_rent * months
            )

    # =========================================================
    # TOTAL TABLE VALUES
    # =========================================================

    @api.depends(
        'monthly_line_ids.basic_50_percent',
        'monthly_line_ids.hra_salary',
        'monthly_line_ids.hra_exemption',
    )
    def _compute_totals(self):

        for record in self:

            lines = record.monthly_line_ids

            record.earned_basic = sum(
                lines.mapped('basic_50_percent')
            )

            record.hra_amount = sum(
                lines.mapped('hra_salary')
            )

            record.total_hra_exemption = sum(
                lines.mapped('hra_exemption')
            )


# =============================================================
# EMPLOYEE INVESTMENT / RENTED HOUSE
# =============================================================

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_rented_house = fields.Boolean(
        string='Are you staying in a rented house?'
    )

    rented_house_ids = fields.One2many(
        'hr.employee.rented.house',
        'employee_id',
        string='Rented House Details',
        copy=False,
    )

    # =========================================================
    # ADD DETAILS BUTTON
    # =========================================================

    def action_add_rental_details(self):

        self.ensure_one()

        rented_house = self.env[
            'hr.employee.rented.house'
        ].search(
            [
                ('employee_id', '=', self.id),
            ],
            order='rent_start_date desc, id desc',
            limit=1,
        )

        return {
            'type': 'ir.actions.act_window',
            'name': 'Rental House Details',
            'res_model': 'hr.employee.rented.house',
            'view_mode': 'form',
            'view_id': self.env.ref(
                'payroll_tds.view_hr_employee_rented_house_form'
            ).id,
            'target': 'new',
            'res_id': (
                rented_house.id
                if rented_house
                else False
            ),
            'context': {
                'default_employee_id': self.id,
            },
        }
