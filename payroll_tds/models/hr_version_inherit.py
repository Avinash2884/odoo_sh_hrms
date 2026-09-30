from odoo import models, fields, api, _


class HrVersion(models.Model):
    _inherit = "hr.version"

    # =========================================================
    # EMPLOYEE ID
    # =========================================================

    ls_employee_id = fields.Char(
        related='employee_id.ls_employee_id',
        string='Employee ID',
        store=True,
        readonly=True,
    )

    # =========================================================
    # PF SELECTION
    # =========================================================

    def _l10n_in_get_pf_selection(self):
        selection = super()._l10n_in_get_pf_selection()

        # Remove the old fixed / ₹15,000 restriction
        selection = [s for s in selection if s[0] != 'fixed']

        # Keep Custom Wage
        selection.append(
            ('custom', _('Custom Wage'))
        )

        # New ₹25,000 PF restriction
        selection.append(
            (
                'restrict_25000',
                _('Restrict Contribution to ₹25,000.00 of PF Wage')
            )
        )

        return selection

    # =========================================================
    # PF EMPLOYEE TYPE
    # =========================================================

    l10n_in_pf_employee_type = fields.Selection(
        selection=_l10n_in_get_pf_selection,
        default='restrict_25000',
        groups="hr_payroll.group_hr_payroll_user"
    )

    # =========================================================
    # PF EMPLOYER TYPE
    # =========================================================

    l10n_in_pf_employer_type = fields.Selection(
        selection=_l10n_in_get_pf_selection,
        default='restrict_25000',
        groups="hr_payroll.group_hr_payroll_user"
    )

    # =========================================================
    # DEARNESS ALLOWANCE
    # =========================================================

    dearness_allowance = fields.Monetary(
        string="Dearness Allowance",
        store=True,
        readonly=False,
        tracking=True,
        groups="hr_payroll.group_hr_payroll_user",
        help="Dearness Allowance (DA)"
    )

    # =========================================================
    # CONVEYANCE ALLOWANCE
    # =========================================================

    conveyance_allowance = fields.Monetary(
        string="Conveyance Allowance",
        store=True,
        readonly=False,
        tracking=True,
        groups="hr_payroll.group_hr_payroll_user",
        help="Conveyance Allowance"
    )

    # =========================================================
    # PF EMPLOYEE AMOUNT
    # =========================================================

    @api.depends(
        'l10n_in_basic_salary_amount',
        'l10n_in_pf_employee_type',
        'l10n_in_pf_employee_percentage',
        'wage',
        'hourly_wage'
    )
    def _compute_l10n_in_pf_employee_amount(self):

        # -----------------------------------------------------
        # AUTO SELECT PF TYPE
        #
        # Basic < 25,000
        #     -> calculate
        #
        # Basic >= 25,000
        #     -> restrict_25000
        #
        # Custom remains untouched.
        # -----------------------------------------------------

        for version in self:
            basic = version.l10n_in_basic_salary_amount or 0.0

            if version.l10n_in_pf_employee_type in (
                'calculate',
                'restrict_25000'
            ):
                version.l10n_in_pf_employee_type = (
                    'calculate'
                    if basic < 25000.0
                    else 'restrict_25000'
                )

        # Preserve Odoo's existing calculation
        super()._compute_l10n_in_pf_employee_amount()

        for version in self:

            basic = version.l10n_in_basic_salary_amount or 0.0

            # -------------------------------------------------
            # CUSTOM WAGE
            # -------------------------------------------------

            if version.l10n_in_pf_employee_type == 'custom':
                version.l10n_in_pf_employee_amount = (
                    basic *
                    (version.l10n_in_pf_employee_percentage or 0.0)
                )

            # -------------------------------------------------
            # ₹25,000 PF RESTRICTION
            # -------------------------------------------------

            if version.l10n_in_pf_employee_type == 'restrict_25000':

                # PF rate = 12%
                version.l10n_in_pf_employee_percentage = 0.12

                # PF wage is restricted to ₹25,000
                pf_wage = min(
                    basic,
                    25000.0
                )

                # Employee PF = PF wage × 12%
                version.l10n_in_pf_employee_amount = (
                    pf_wage * 0.12
                )

                # Display effective percentage against actual Basic
                #
                # Example:
                # Basic = 25,000
                # PF = 3,000
                # Effective percentage = 12%
                #
                # Basic = 30,000
                # PF = 3,000
                # Effective percentage = 10%
                if basic:
                    version.l10n_in_pf_employee_percentage = (
                        version.l10n_in_pf_employee_amount /
                        basic
                    )

    # =========================================================
    # PF EMPLOYER AMOUNT
    # =========================================================

    @api.depends(
        'l10n_in_basic_salary_amount',
        'l10n_in_pf_employer_type',
        'l10n_in_pf_employer_percentage',
        'wage',
        'hourly_wage'
    )
    def _compute_l10n_in_pf_employer_amount(self):

        # -----------------------------------------------------
        # AUTO SELECT PF TYPE
        #
        # Basic < 25,000
        #     -> calculate
        #
        # Basic >= 25,000
        #     -> restrict_25000
        #
        # Custom remains untouched.
        # -----------------------------------------------------

        for version in self:
            basic = version.l10n_in_basic_salary_amount or 0.0

            if version.l10n_in_pf_employer_type in (
                'calculate',
                'restrict_25000'
            ):
                version.l10n_in_pf_employer_type = (
                    'calculate'
                    if basic < 25000.0
                    else 'restrict_25000'
                )

        # Preserve Odoo's existing calculation
        super()._compute_l10n_in_pf_employer_amount()

        for version in self:

            basic = version.l10n_in_basic_salary_amount or 0.0

            # -------------------------------------------------
            # CUSTOM WAGE
            # -------------------------------------------------

            if version.l10n_in_pf_employer_type == 'custom':
                version.l10n_in_pf_employer_amount = (
                    basic *
                    (version.l10n_in_pf_employer_percentage or 0.0)
                )

            # -------------------------------------------------
            # ₹25,000 PF RESTRICTION
            # -------------------------------------------------

            if version.l10n_in_pf_employer_type == 'restrict_25000':

                # PF rate = 12%
                version.l10n_in_pf_employer_percentage = 0.12

                # PF wage restricted to ₹25,000
                pf_wage = min(
                    basic,
                    25000.0
                )

                # Employer PF = PF wage × 12%
                version.l10n_in_pf_employer_amount = (
                    pf_wage * 0.12
                )

                # Display effective percentage against actual Basic
                if basic:
                    version.l10n_in_pf_employer_percentage = (
                        version.l10n_in_pf_employer_amount /
                        basic
                    )

    # =========================================================
    # SPECIAL ALLOWANCE
    # =========================================================

    l10n_in_fixed_allowance = fields.Monetary(
        string='Special Allowance',
        tracking=True,
        compute="_compute_l10n_in_fixed_allowance",
        store=True,
        groups="hr_payroll.group_hr_payroll_user",
        readonly=False,
        help='The remaining variable amount is computed as the fixed allowance after all other allowances defined.\
        this will represents the portion of wages remaining after the total of all other allowances.'
    )

    # =========================================================
    # GRATUITY PERCENTAGE
    # =========================================================

    l10n_in_gratuity_percentage = fields.Float(
        string="Gratuity Percentage",
        compute="_compute_l10n_in_gratuity_percentage",
        store=True
    )

    # =========================================================
    # YEARS OF SERVICE
    # =========================================================

    years_of_service = fields.Float(
        string="Years of Service",
        compute="_compute_years_of_service",
        store=True
    )

    @api.depends('employee_id')
    def _compute_years_of_service(self):
        for rec in self:
            rec.years_of_service = (
                rec.employee_id.sudo().years_of_service or 0.0
            )

    # =========================================================
    # GRATUITY
    # =========================================================

    l10n_in_gratuity = fields.Monetary(
        string="Gratuity",
        compute="_compute_l10n_in_gratuity",
        store=True,
        readonly=False,
        groups="hr_payroll.group_hr_payroll_user"
    )

    @api.depends(
        'l10n_in_basic_salary_amount',
        'employee_id.years_of_service',
        'dearness_allowance'
    )
    def _compute_l10n_in_gratuity(self):
        for version in self:

            years = float(
                version.employee_id.sudo().years_of_service or 0.0
            )

            basic = (
                version.l10n_in_basic_salary_amount or 0.0
            )

            da = version.dearness_allowance or 0.0

            version.l10n_in_gratuity = (
                (basic + da) * 15 * years
            ) / 26

    # =========================================================
    # GRATUITY PERCENTAGE
    # =========================================================

    @api.depends('l10n_in_gratuity')
    def _compute_l10n_in_gratuity_percentage(self):
        for version in self:
            version.l10n_in_gratuity_percentage = 0.0

    # =========================================================
    # HRA CALCULATION BASED ON GROSS WAGE
    # =========================================================

    @api.depends(
        'wage',
        'l10n_in_hra_percentage'
    )
    def _compute_l10n_in_hra(self):

        self.env.remove_to_compute(
            self._fields['l10n_in_hra_percentage'],
            self
        )

        for version in self:

            hra_percentage = (
                version.l10n_in_hra_percentage or 0.0
            )

            # Convert 30 / 40 / 50
            # to 0.30 / 0.40 / 0.50

            if hra_percentage > 1.0:
                hra_percentage = hra_percentage / 100.0

            # Keep percentage between 0 and 1

            version.l10n_in_hra_percentage = min(
                max(hra_percentage, 0.0),
                1.0
            )

            # HRA = Gross Wage × HRA Percentage

            version.l10n_in_hra = (
                version.wage *
                version.l10n_in_hra_percentage
            )

    # =========================================================
    # HRA PERCENTAGE
    # =========================================================

    @api.depends(
        'l10n_in_hra',
        'wage'
    )
    def _compute_l10n_in_hra_percentage(self):

        for version in self:

            if not version.wage:
                version.l10n_in_hra_percentage = 0.0
                continue

            version.l10n_in_hra_percentage = (
                version.l10n_in_hra /
                version.wage
            )

            # Safety:
            # 0 <= percentage <= 1

            version.l10n_in_hra_percentage = min(
                max(
                    version.l10n_in_hra_percentage,
                    0.0
                ),
                1.0
            )

    # =========================================================
    # ENTERPRISE ALLOWANCE VALIDATION
    # =========================================================

    @api.constrains(
        'l10n_in_basic_salary_amount',
        'l10n_in_hra',
        'l10n_in_standard_allowance',
        'l10n_in_performance_bonus',
        'l10n_in_leave_travel_allowance',
        'wage',
        'hourly_wage'
    )
    def _check_l10n_in_total_allowance_below_wage(self):

        # Preserve existing behavior:
        # Skip enterprise validation
        return
