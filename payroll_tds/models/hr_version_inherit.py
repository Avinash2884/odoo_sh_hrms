from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)
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

    # ---------------------------------------------------------
    # PF Help text change
    # ---------------------------------------------------------

    l10n_in_pf_employee_amount = fields.Monetary(
        compute="_compute_l10n_in_pf_employee_amount",
        store=True,
        readonly=False,
        tracking=True,
        groups="hr_payroll.group_hr_payroll_user",
        help="Employee contributes a percentage of the Basic salary + Special Allowance."
    )

    l10n_in_pf_employer_amount = fields.Monetary(
        string="Employer",
        compute="_compute_l10n_in_pf_employer_amount",
        store=True,
        readonly=False,
        tracking=True,
        groups="hr_payroll.group_hr_payroll_user",
        help="Employer contributes a percentage of the Basic salary + Special Allowance."
    )

    # ---------------------------------------------------------
    # Employee PF
    # ---------------------------------------------------------

    @api.depends(
        'l10n_in_basic_salary_amount',
        'l10n_in_fixed_allowance',
        'l10n_in_pf_employee_type',
        'l10n_in_pf_employee_percentage'
    )
    def _compute_l10n_in_pf_employee_amount(self):
        for version in self:

            pf_wage = (
                    (version.l10n_in_basic_salary_amount or 0.0)
                    + (version.l10n_in_fixed_allowance or 0.0)
            )

            if not pf_wage:
                version.l10n_in_pf_employee_amount = 0.0
                version.l10n_in_pf_employee_percentage = 0.0
                continue

            # -------------------------------------------------
            # PF Wage <= 15000
            # -------------------------------------------------
            if pf_wage <= 15000:

                version.l10n_in_pf_employee_type = 'fixed'

                # Default percentage = 12%
                if (
                        not version.l10n_in_pf_employee_percentage
                        or version.l10n_in_pf_employee_percentage > 0.12
                ):
                    version.l10n_in_pf_employee_percentage = 0.12

                version.l10n_in_pf_employee_amount = round(
                    pf_wage * version.l10n_in_pf_employee_percentage,
                    2
                )

            # -------------------------------------------------
            # PF Wage > 15000
            # -------------------------------------------------
            else:

                version.l10n_in_pf_employee_type = 'calculate'

                default_percentage = 1800.0 / pf_wage

                if (
                        not version.l10n_in_pf_employee_percentage
                        or abs(
                    version.l10n_in_pf_employee_percentage - 0.12
                ) < 0.000001
                ):
                    version.l10n_in_pf_employee_percentage = default_percentage
                    version.l10n_in_pf_employee_amount = 1800.0

                else:
                    version.l10n_in_pf_employee_amount = round(
                        pf_wage * version.l10n_in_pf_employee_percentage,
                        2
                    )

    @api.depends(
        'l10n_in_pf_employee_amount',
        'l10n_in_basic_salary_amount',
        'l10n_in_fixed_allowance'
    )
    def _compute_l10n_in_pf_employee_percentage(self):
        for version in self:

            pf_wage = (
                    (version.l10n_in_basic_salary_amount or 0.0)
                    + (version.l10n_in_fixed_allowance or 0.0)
            )

            if pf_wage:
                version.l10n_in_pf_employee_percentage = (
                        version.l10n_in_pf_employee_amount / pf_wage
                )
            else:
                version.l10n_in_pf_employee_percentage = 0.0
    # ---------------------------------------------------------
    # Employer PF
    # ---------------------------------------------------------

    @api.depends(
        'l10n_in_basic_salary_amount',
        'l10n_in_fixed_allowance',
        'l10n_in_pf_employer_type',
        'l10n_in_pf_employer_percentage'
    )
    def _compute_l10n_in_pf_employer_amount(self):
        for version in self:

            pf_wage = (
                    (version.l10n_in_basic_salary_amount or 0.0)
                    + (version.l10n_in_fixed_allowance or 0.0)
            )

            if not pf_wage:
                version.l10n_in_pf_employer_amount = 0.0
                version.l10n_in_pf_employer_percentage = 0.0
                continue

            # -------------------------------------------------
            # PF Wage <= 15000
            # -------------------------------------------------
            if pf_wage <= 15000:

                version.l10n_in_pf_employer_type = 'fixed'

                # Default Percentage = 12%
                if (
                        not version.l10n_in_pf_employer_percentage
                        or version.l10n_in_pf_employer_percentage > 0.12
                ):
                    version.l10n_in_pf_employer_percentage = 0.12

                version.l10n_in_pf_employer_amount = round(
                    pf_wage * version.l10n_in_pf_employer_percentage,
                    2
                )

            # -------------------------------------------------
            # PF Wage > 15000
            # -------------------------------------------------
            else:

                version.l10n_in_pf_employer_type = 'calculate'

                default_percentage = 1800.0 / pf_wage

                # First time -> Default ₹1800
                if (
                        not version.l10n_in_pf_employer_percentage
                        or abs(
                    version.l10n_in_pf_employer_percentage - 0.12
                ) < 0.000001
                ):
                    version.l10n_in_pf_employer_percentage = default_percentage
                    version.l10n_in_pf_employer_amount = 1800.0

                # User changed percentage
                else:
                    version.l10n_in_pf_employer_amount = round(
                        pf_wage * version.l10n_in_pf_employer_percentage,
                        2
                    )

    @api.depends(
        'l10n_in_pf_employer_amount',
        'l10n_in_basic_salary_amount',
        'l10n_in_fixed_allowance'
    )
    def _compute_l10n_in_pf_employer_percentage(self):
        for version in self:

            pf_wage = (
                    (version.l10n_in_basic_salary_amount or 0.0)
                    + (version.l10n_in_fixed_allowance or 0.0)
            )

            if pf_wage:
                version.l10n_in_pf_employer_percentage = (
                        version.l10n_in_pf_employer_amount / pf_wage
                )
            else:
                version.l10n_in_pf_employer_percentage = 0.0
    # <-- ADD HERE
    @api.onchange(
        'l10n_in_pf_employee_percentage',
        'l10n_in_pf_employer_percentage'
    )
    def _onchange_pf_percentage(self):
        for version in self:

            pf_wage = (
                    (version.l10n_in_basic_salary_amount or 0.0)
                    + (version.l10n_in_fixed_allowance or 0.0)
            )

            if version.l10n_in_pf_employee_type == 'calculate':
                version.l10n_in_pf_employee_amount = round(
                    pf_wage *
                    version.l10n_in_pf_employee_percentage,
                    2
                )

            if version.l10n_in_pf_employer_type == 'calculate':
                version.l10n_in_pf_employer_amount = round(
                    pf_wage *
                    version.l10n_in_pf_employer_percentage,
                    2
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
            rec.years_of_service = rec.employee_id.years_of_service or 0.0

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
            years = float(version.employee_id.years_of_service or 0.0)
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
        # Skip enterprise validation
        return