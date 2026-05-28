from odoo import models, fields, api, _


class HrVersion(models.Model):
    _inherit = "hr.version"


    def _l10n_in_get_pf_selection(self):
        selection = super()._l10n_in_get_pf_selection()
        selection.append(
            ('custom', _('Custom Wage'))
        )
        return selection

    l10n_in_pf_employee_type = fields.Selection(
        selection=_l10n_in_get_pf_selection,
        default='fixed',
        groups="hr_payroll.group_hr_payroll_user"
    )

    l10n_in_pf_employer_type = fields.Selection(
        selection=_l10n_in_get_pf_selection,
        default='fixed',
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


    @api.depends('l10n_in_basic_salary_amount',
                 'l10n_in_pf_employee_type',
                 'l10n_in_pf_employee_percentage',
                 'wage', 'hourly_wage')
    def _compute_l10n_in_pf_employee_amount(self):

        super()._compute_l10n_in_pf_employee_amount()

        for version in self:
            if version.l10n_in_pf_employee_type == 'custom':
                version.l10n_in_pf_employee_amount = (
                        version.l10n_in_basic_salary_amount *
                        version.l10n_in_pf_employee_percentage
                )

    @api.depends('l10n_in_basic_salary_amount',
                 'l10n_in_pf_employer_type',
                 'l10n_in_pf_employer_percentage',
                 'wage', 'hourly_wage')

    def _compute_l10n_in_pf_employer_amount(self):

        super()._compute_l10n_in_pf_employer_amount()

        for version in self:
            if version.l10n_in_pf_employer_type == 'custom':
                version.l10n_in_pf_employer_amount = (
                        version.l10n_in_basic_salary_amount *
                        version.l10n_in_pf_employer_percentage
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
        related='employee_id.years_of_service',
        store=True
    )

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
            years = float(version.employee_id.years_of_servic or 0.0)
            basic = version.l10n_in_basic_salary_amount or 0.0
            da = version.dearness_allowance or 0.0

            # 🔥 No condition → always calculate
            version.l10n_in_gratuity = ((basic + da) * 15 * years) / 26

    @api.depends('l10n_in_gratuity')
    def _compute_l10n_in_gratuity_percentage(self):
        for version in self:
            # 🔥 Always safe value
            version.l10n_in_gratuity_percentage = 0.0

    # ---------------------------------------
    # HRA Calculation Based On Gross Wage
    # ---------------------------------------

    @api.depends('wage', 'l10n_in_hra_percentage')
    def _compute_l10n_in_hra(self):

        # Remove old compute queue
        self.env.remove_to_compute(
            self._fields['l10n_in_hra_percentage'],
            self
        )

        for version in self:
            # HRA = Gross Wage × HRA %
            version.l10n_in_hra = (
                    version.wage *
                    version.l10n_in_hra_percentage
            )

