from odoo import models, fields, api, _


class HrVersion(models.Model):
    _inherit = "hr.version"

    l10n_in_basic_salary_amount = fields.Monetary(
        string="Basic Salary",
        groups="base.group_user",
    )


    def _l10n_in_get_pf_selection(self):
        selection = super()._l10n_in_get_pf_selection()
        # CHANGE 1: old "Restrict contribution to 15,000" ('fixed') option remove
        selection = [s for s in selection if s[0] != 'fixed']
        selection.append(
            ('custom', _('Custom Wage'))
        )
        selection.append(
            ('restrict_25000', _('Restrict Contribution to ₹25,000.00 of PF Wage'))
        )
        return selection

    # CHANGE 2: default 'fixed' -> 'restrict_25000'
    l10n_in_pf_employee_type = fields.Selection(
        selection=_l10n_in_get_pf_selection,
        default='restrict_25000',
        groups="hr_payroll.group_hr_payroll_user"
    )

    l10n_in_pf_employer_type = fields.Selection(
        selection=_l10n_in_get_pf_selection,
        default='restrict_25000',
        groups="hr_payroll.group_hr_payroll_user"
    )

    dearness_allowance = fields.Monetary(
        string="Dearness Allowance",
        store=True,
        readonly=False,
        tracking=True,
        groups="hr_payroll.group_hr_payroll_user",
        help="Dearness Allowance (DA)"
    )

    conveyance_allowance = fields.Monetary(
        string="Conveyance Allowance",
        store=True,
        readonly=False,
        tracking=True,
        groups="hr_payroll.group_hr_payroll_user",
        help="Conveyance Allowance"
    )

    @api.depends(
        'l10n_in_basic_salary_amount',
        'l10n_in_pf_employee_type',
        'l10n_in_pf_employee_percentage',
        'wage',
        'hourly_wage'
    )
    def _compute_l10n_in_pf_employee_amount(self):

        # ADDED: basic < 25000 -> '12.0% of actual PF wages' ('calculate')
        #        basic >= 25000 -> 'Restrict Contribution to 25,000'
        # 'custom' selected manually is never overridden
        for version in self:
            if version.l10n_in_pf_employee_type in ('calculate', 'restrict_25000'):
                version.l10n_in_pf_employee_type = (
                    'calculate'
                    if (version.l10n_in_basic_salary_amount or 0.0) < 25000.0
                    else 'restrict_25000'
                )

        super()._compute_l10n_in_pf_employee_amount()

        for version in self:
            if version.l10n_in_pf_employee_type == 'custom':
                version.l10n_in_pf_employee_amount = (
                    version.l10n_in_basic_salary_amount *
                    version.l10n_in_pf_employee_percentage
                )

            if version.l10n_in_pf_employee_type == 'restrict_25000':
                version.l10n_in_pf_employee_percentage = 0.12

                # basic >= 25000 -> 3000 fixed, basic < 25000 -> 12% of actual basic
                version.l10n_in_pf_employee_amount = (
                        min(
                            version.l10n_in_basic_salary_amount or 0.0,
                            25000.0
                        ) * 0.12
                )

                # ADDED: show actual share of basic (30000 basic -> 3000 -> 10%)
                if version.l10n_in_basic_salary_amount:
                    version.l10n_in_pf_employee_percentage = (
                        version.l10n_in_pf_employee_amount /
                        version.l10n_in_basic_salary_amount
                    )

    @api.depends(
        'l10n_in_basic_salary_amount',
        'l10n_in_pf_employer_type',
        'l10n_in_pf_employer_percentage',
        'wage',
        'hourly_wage'
    )
    def _compute_l10n_in_pf_employer_amount(self):

        # ADDED: same auto switch for employer contribution type
        for version in self:
            if version.l10n_in_pf_employer_type in ('calculate', 'restrict_25000'):
                version.l10n_in_pf_employer_type = (
                    'calculate'
                    if (version.l10n_in_basic_salary_amount or 0.0) < 25000.0
                    else 'restrict_25000'
                )

        super()._compute_l10n_in_pf_employer_amount()

        for version in self:
            if version.l10n_in_pf_employer_type == 'custom':
                version.l10n_in_pf_employer_amount = (
                    version.l10n_in_basic_salary_amount *
                    version.l10n_in_pf_employer_percentage
                )

            if version.l10n_in_pf_employer_type == 'restrict_25000':
                version.l10n_in_pf_employer_percentage = 0.12

                # basic >= 25000 -> 3000 fixed, basic < 25000 -> 12% of actual basic
                version.l10n_in_pf_employer_amount = (
                        min(
                            version.l10n_in_basic_salary_amount or 0.0,
                            25000.0
                        ) * 0.12
                )

                # ADDED: show actual share of basic (30000 basic -> 3000 -> 10%)
                if version.l10n_in_basic_salary_amount:
                    version.l10n_in_pf_employer_percentage = (
                        version.l10n_in_pf_employer_amount /
                        version.l10n_in_basic_salary_amount
                    )

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

    l10n_in_gratuity_percentage = fields.Float(
        string="Gratuity Percentage",
        compute="_compute_l10n_in_gratuity_percentage",
        store=True
    )

    years_of_service = fields.Float(
        string="Years of Service",
        compute="_compute_years_of_service",
        store=True
    )

    @api.depends('employee_id')
    def _compute_years_of_service(self):
        for rec in self:
            rec.years_of_service = rec.employee_id.sudo().years_of_service or 0.0

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
            years = float(version.employee_id.sudo().years_of_service or 0.0)
            basic = version.l10n_in_basic_salary_amount or 0.0
            da = version.dearness_allowance or 0.0

            version.l10n_in_gratuity = ((basic + da) * 15 * years) / 26

    @api.depends('l10n_in_gratuity')
    def _compute_l10n_in_gratuity_percentage(self):
        for version in self:
            version.l10n_in_gratuity_percentage = 0.0

    @api.depends('wage', 'l10n_in_hra_percentage')
    def _compute_l10n_in_hra(self):
        self.env.remove_to_compute(
            self._fields['l10n_in_hra_percentage'],
            self
        )

        for version in self:
            hra_percentage = version.l10n_in_hra_percentage or 0.0

            if hra_percentage > 1.0:
                hra_percentage = hra_percentage / 100.0

            version.l10n_in_hra_percentage = min(
                max(hra_percentage, 0.0),
                1.0
            )

            version.l10n_in_hra = (
                version.wage *
                version.l10n_in_hra_percentage
            )

    @api.depends('l10n_in_hra', 'wage')
    def _compute_l10n_in_hra_percentage(self):
        for version in self:
            if not version.wage:
                version.l10n_in_hra_percentage = 0.0
                continue

            version.l10n_in_hra_percentage = (
                version.l10n_in_hra / version.wage
            )

            version.l10n_in_hra_percentage = min(
                max(version.l10n_in_hra_percentage, 0.0),
                1.0
            )

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
        return