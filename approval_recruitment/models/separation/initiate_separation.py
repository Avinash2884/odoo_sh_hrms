
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class InitiateSeparation(models.Model):
    _name = 'initiate.separation'
    _description = 'Initiate Separation'
    _inherit = ['mail.thread']
    _rec_name = 'employee_id'
    _order = "create_date desc"

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1),
        check_company=True,
        index=True,
        tracking=True,
    )
    ls_employee_id = fields.Char(string="Employee ID", related='employee_id.ls_employee_id',tracking=True)
    ls_designation_id = fields.Many2one('designation', 'Designation',related='employee_id.ls_designation_id', tracking=True)
    department_id = fields.Many2one('hr.department', 'Department',related='employee_id.department_id',tracking=True)
    reporting_manager_id = fields.Many2one('hr.employee', 'Reporting Manager',related='employee_id.parent_id',tracking=True)
    hr_id = fields.Many2one('hr.employee', 'HR',related='employee_id.hr_id',tracking=True)
    hr_head_id = fields.Many2one('hr.employee', 'HR Head',related='employee_id.hr_head_id',tracking=True)
    it_asset_head_id = fields.Many2one('hr.employee', 'IT Asset Head',related='employee_id.it_asset_head_id',tracking=True)
    admin_head_id = fields.Many2one('hr.employee', 'Admin Head',related='employee_id.admin_head_id',tracking=True)
    payroll_head_id = fields.Many2one('hr.employee', 'Payroll Head',related='employee_id.payroll_head_id',tracking=True)
    joining_date_recruit = fields.Date(string="Date of Joining", copy=False,related='employee_id.joining_date_recruit', tracking=True)
    last_working_date = fields.Date(string="Last Working Date", copy=False, tracking=True,default=lambda self: fields.Date.today() + timedelta(days=30))
    reason_for_resignation = fields.Char(string="Reason For Resignation", copy=False, tracking=True)
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
    ], required=True,tracking=True)
    detailed_reason = fields.Text(string="Detailed Reason", tracking=True)
    acknowledgement = fields.Boolean(tracking=True)
    action_performed_manager = fields.Char(string="Action Performed By Manager",tracking=True)
    action_by_manager = fields.Char(string="Action by Manager",tracking=True)
    action_performed_hr = fields.Char(string="Action Performed By HR",tracking=True)
    action_by_hr = fields.Char(string="Action by HR",tracking=True)
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        tracking = True
    )
    key_responsibility = fields.Html(string='Key Responsibility')
    take_description = fields.Html(string='Task Description')
    handing_over_to = fields.Many2one('hr.employee',string='Handover to',tracking=True)
    role = fields.Char(string='Role', related='handing_over_to.ls_role_id.name', store=True, tracking=True)
    status_of_tasks = fields.Selection([
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ], string='Status of Tasks',tracking=True)
    knowledge_transfer = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ], string='Knowledge Transfer',tracking=True)
    dues_cleared = fields.Selection([
        ('pending', 'Pending'),
        ('cleared', 'Cleared'),
    ], string='Dues Cleared',tracking=True)
    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        string="Attachments",
        tracking = True
    )
    remarks = fields.Text(string="Remarks", tracking=True)
    approver_name = fields.Many2one('res.users',string='Approver Name', tracking=True)
    approval_date = fields.Date(string="Approval Date",tracking=True)
    approver_remark = fields.Char(string="Approver Remarks",tracking=True)

    it_assets_clearance_ids = fields.One2many('it.assets.clearance','initiate_separation_id',string="IT Asset Clearance",tracking=True)
    admin_clearance_ids = fields.One2many('admin.clearance','initiate_separation_id',string="Admin Clearance",tracking=True)
    payroll_clearance_ids = fields.One2many('payroll.clearance','initiate_separation_id',string="Payroll Clearance",tracking=True)
    exit_interview_line_ids = fields.One2many('exit.interview.line','initiate_separation_id',string="Exit Interview",tracking=True)

    # IT Assets Clearance
    it_assets_clearance_dues_cleared_status = fields.Selection([
        ('cleared', 'Cleared'),
        ('pending', 'Pending'),
    ], string='IT Asset Dues Cleared Status',tracking=True)
    it_assets_clearance_remarks = fields.Text(string="Clerance Remarks", tracking=True)
    it_assets_clearance_approver_name = fields.Many2one('hr.employee', string='IT Asset Approver Name', tracking=True)
    it_assets_clearance_approval_date = fields.Date(string="IT Asset Approval Date", tracking=True)

    # Admin Clearance
    admin_clearance_dues_cleared_status = fields.Selection([
        ('cleared', 'Cleared'),
        ('pending', 'Pending'),
    ], string='Admin Clearance Dues Cleared Status', tracking=True)
    admin_clearance_remarks = fields.Text(string="Admin Clearance Remarks", tracking=True)
    admin_clearance_approver_name = fields.Many2one('hr.employee', string='Admin Clearance Approver Name', tracking=True)
    admin_clearance_approval_date = fields.Date(string="Admin Clearance Approval Date", tracking=True)

    # Payroll Clearance
    payroll_clearance_dues_cleared_status = fields.Selection([
        ('cleared', 'Cleared'),
        ('pending', 'Pending'),
    ], string='Payroll Dues Cleared Status', tracking=True)
    payroll_clearance_remarks = fields.Text(string="Payroll Clearance Remarks", tracking=True)
    payroll_clearance_approver_names = fields.Char( string='Payroll Approver Name', tracking=True)
    payroll_clearance_approval_date = fields.Date(string="Payroll Approval Date", tracking=True)

    exit_acknowledgement = fields.Boolean(tracking=True)
    state = fields.Selection([
        ('submitted', 'Submitted'),
        ('handing_over_responsibility', 'Handing Over Responsibility'),
        ('clearance', 'Clearance'),
        ('exit', 'Exit'),
        ('revoked', 'Revoked'),
    ], string="State", tracking=True)
    internal_state = fields.Selection([
        ('submitted', 'Submitted'),
        ('manager_approved', 'Manager Approved'),
        ('manager_rejected', 'Manager Rejected'),
        ('hr_approved', 'HR Approved'),
        ('hr_rejected', 'HR Rejected'),
        ('handing_approved', 'Handing Approved'),
        ('handing_rejected', 'Handing Rejected'),
        ('clearance_approved', 'Clearance Approved'),
        ('clearance_rejected', 'Clearance Rejected'),
        ('exit_approved', 'Exit Approved'),
        ('exit_rejected', 'Exit Rejected'),
        ('revoked', 'Revoked'),
    ],tracking=True)
    key_state = fields.Selection([
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('resubmitted', 'Resubmitted'),
    ],tracking=True)
    it_assets_state = fields.Selection([
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('resubmitted', 'Resubmitted'),
    ],tracking=True)
    admin_state = fields.Selection([
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('resubmitted', 'Resubmitted'),
    ],tracking=True)
    payroll_state = fields.Selection([
        ('proceed', 'Proceed'),
    ],tracking=True)
    exit_state = fields.Selection([
        ('submitted', 'submitted'),
    ],tracking=True)
    can_show_payroll = fields.Boolean(
        compute="_compute_payroll_visibility",
        store=False
    )
    acknowledgement_editable = fields.Boolean(
        string="Employee Editable Acknowledge",
        compute="_compute_acknowledgement_editable"
    )
    is_request_owner = fields.Boolean(compute="_compute_is_request_owner")
    is_only_manager = fields.Boolean(compute="_compute_is_only_manager")
    is_only_hr_head = fields.Boolean(compute="_compute_is_only_hr_head")
    is_only_it_assets_head = fields.Boolean(compute="_compute_is_only_it_assets_head")
    is_only_admin_head = fields.Boolean(compute="_compute_is_only_admin_head")
    is_only_payroll_head = fields.Boolean(compute="_compute_is_only_payroll_head")

    def _compute_is_request_owner(self):
        for rec in self:
            rec.is_request_owner = rec.create_uid == self.env.user

    def _compute_is_only_manager(self):
        for rec in self:
            user = self.env.user

            rec.is_only_manager = (
                    user.has_group('approval_recruitment.group_separation_reporting_manager')
                    and not user.has_group('approval_recruitment.group_separation_hr')
                    and rec.reporting_manager_id.user_id == user
                    and rec.create_uid != user
            )

    def _compute_is_only_hr_head(self):
        for rec in self:
            user = self.env.user

            rec.is_only_hr_head = (
                    user.has_group('approval_recruitment.group_separation_hr_head')
                    and not user.has_group('approval_recruitment.group_separation_it_assets_clearance_head')
                    and rec.hr_head_id.user_id == user
                    and rec.create_uid != user
            )

    def _compute_is_only_it_assets_head(self):
        for rec in self:
            user = self.env.user

            rec.is_only_it_assets_head = (
                    user.has_group('approval_recruitment.group_separation_it_assets_clearance_head')
                    and rec.it_asset_head_id
                    and rec.it_asset_head_id.user_id == user
                    and rec.create_uid != user
            )

    def _compute_is_only_admin_head(self):
        for rec in self:
            user = self.env.user

            rec.is_only_admin_head = (
                    user.has_group('approval_recruitment.group_separation_admin_clearance_head')
                    and rec.admin_head_id
                    and rec.admin_head_id.user_id == user
                    and rec.create_uid != user
            )

    def _compute_is_only_payroll_head(self):
        for rec in self:
            user = self.env.user

            rec.is_only_payroll_head = (
                    user.has_group('approval_recruitment.group_separation_payroll_clearance_head')
                    and rec.payroll_clearance_approver_ids  # or payroll_head_id if you have
                    and user.id in rec.payroll_clearance_approver_ids.mapped('user_id').ids
                    and rec.create_uid != user
            )

    def _compute_acknowledgement_editable(self):
        for rec in self:
            # Only the employee themselves can edit
            rec.acknowledgement_editable = (rec.employee_id.user_id == self.env.user)

    is_hr_head = fields.Boolean(compute="_compute_is_hr_head")

    def _compute_is_hr_head(self):
        for rec in self:
            rec.is_hr_head = self.env.user.has_group('approval_recruitment.group_separation_hr_head')

    def get_record_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/web#id={self.id}&model={self._name}&view_type=form"

    @api.depends('it_assets_state', 'admin_state')
    def _compute_payroll_visibility(self):
        for rec in self:
            if rec.it_assets_state == 'approved' and rec.admin_state == 'approved':
                rec.can_show_payroll = True
            else:
                rec.can_show_payroll = False

    def action_submit(self):
        for record in self:
            if not record.acknowledgement:
                raise ValidationError(
                    _("You must acknowledge the resignation before submitting!")
                )

            record._send_resignation_mail()

            record.state = 'submitted'
            record.internal_state = 'submitted'

    def action_manager_approve(self):
        for record in self:
            record.action_by_manager = self.env.user.name
            record.action_performed_manager = "Approved"
            record.internal_state = 'manager_approved'
            record._send_manager_approval_mail()

    def action_manager_reject(self):
        for record in self:
            record.action_by_manager = self.env.user.name
            record.action_performed_manager = "Rejected"
            record.internal_state = 'manager_rejected'
            record._send_manager_reject_mail()

    def action_hr_approve(self):
        for record in self:
            record.action_by_hr = self.env.user.name
            record.action_performed_hr = "Approved"
            record.internal_state = 'hr_approved'
            record._send_hr_approval_mail()

    def action_hr_reject(self):
        for record in self:
            record.action_by_hr = self.env.user.name
            record.action_performed_hr = "Rejected"
            record.internal_state = 'hr_rejected'
            record._send_hr_reject_mail()

    def action_handover_submit(self):
        for record in self:
            record.key_state = 'submitted'
            record._send_handover_submit_mail()

    def action_handover_approve(self):
        for record in self:
            record.approver_name = self.env.user.id
            record.approval_date = fields.Date.today()
            record.key_state = 'approved'
            record.state = 'handing_over_responsibility'
            record._send_handover_approved_mail()

    def action_handover_reject(self):
        for record in self:
            record.key_state = 'resubmitted'
            record._send_handover_resubmit_mail()

    def action_it_assets_submit(self):
        for record in self:
            record.it_assets_clearance_ids.it_assets_state = 'submitted'
            record.it_assets_state = 'submitted'
            record._send_it_asset_head_submit_mail()

    def action_it_assets_approve(self):
        for record in self:
            employee = self.env['hr.employee'].search([
                ('user_id', '=', self.env.user.id)
            ], limit=1)
            record.it_assets_clearance_ids.it_assets_state = 'approved'
            record.it_assets_clearance_approver_name = employee.id
            record.it_assets_clearance_approval_date = fields.Date.today()
            record.it_assets_state = 'approved'
            record._send_it_asset_head_approve_mail()

    def action_it_assets_resubmitted(self):
        for record in self:
            record.it_assets_clearance_ids.it_assets_state = 'resubmitted'
            record.it_assets_state = 'resubmitted'
            record._send_it_asset_head_resubmit_mail()

    def action_admin_submit(self):
        for record in self:
            record.admin_clearance_ids.admin_state = 'submitted'
            record.admin_state = 'submitted'
            record._send_admin_head_submit_mail()

    def action_admin_approve(self):
        for record in self:
            employee = self.env['hr.employee'].search([
                ('user_id', '=', self.env.user.id)
            ], limit=1)

            record.admin_clearance_ids.admin_state = 'approved'
            record.admin_clearance_approver_name = employee.id
            record.admin_clearance_approval_date = fields.Date.today()
            record.admin_state = 'approved'

            record._send_admin_head_approve_mail()

    def action_admin_resubmitted(self):
        for record in self:
            record.admin_clearance_ids.admin_state = 'resubmitted'
            record.admin_state = 'resubmitted'
            record._send_admin_head_resubmit_mail()

    def action_proceed(self):
        for record in self:
            record.payroll_clearance_approver_names = self.env.user.name
            record.payroll_clearance_approval_date = fields.Date.today()
            record.payroll_clearance_ids.payroll_state = 'proceed'
            record.payroll_state = 'proceed'
            record.state = 'clearance'
            record._send_payroll_proceed_mail()

    def action_exit_submit(self):
        for record in self:
            record.exit_state = 'submitted'
            record.state = 'exit'
            record._send_exit_submit_mail()

    @api.model
    def create(self, vals):
        record = super(InitiateSeparation, self).create(vals)

        # Exit Interview Questions
        questions = self.env['exit.interview.question'].search([], order='sequence')
        question_lines = []

        for q in questions:
            question_lines.append((0, 0, {
                'question_id': q.id,
                'initiate_separation_id': record.id
            }))

        record.exit_interview_line_ids = question_lines

        # IT Asset Devices
        devices = self.env['device.type'].search([])
        device_lines = []

        for device in devices:
            device_lines.append((0, 0, {
                'name': device.id,
                'initiate_separation_id': record.id
            }))

        record.it_assets_clearance_ids = device_lines

        # Admin Asset Devices
        items = self.env['item.name'].search([])
        admin_lines = []

        for item in items:
            admin_lines.append((0, 0, {
                'name': item.id,
                'initiate_separation_id': record.id
            }))

        record.admin_clearance_ids = admin_lines

        # Payroll Asset Devices
        components = self.env['payroll.component'].search([])
        payroll_lines = []
        for comp in components:
            payroll_lines.append((0, 0, {
                'name': comp.id,
                'initiate_separation_id': record.id
            }))
        record.payroll_clearance_ids = payroll_lines

        return record

    # Mails
    def _send_resignation_mail(self):
        self.ensure_one()

        if not self.reporting_manager_id or not self.reporting_manager_id.work_email:
            raise ValidationError(
                _("Reporting Manager does not have a work email configured.")
            )

        template = self.env.ref(
            'approval_recruitment.mail_template_resignation_initiation',
            raise_if_not_found=False
        )

        if template:
            email_values = {
                'email_to': self.reporting_manager_id.work_email,
            }

            template.sudo().send_mail(self.id, force_send=True, email_values=email_values)

        print("Mail sent successfully")

    def _send_manager_approval_mail(self):
        """Send manager approval notification to HR & HR Head"""
        self.ensure_one()

        if not (self.hr_id and self.hr_head_id):
            raise ValidationError(_("HR or HR Head is not configured."))

        template = self.env.ref(
            'approval_recruitment.mail_template_manager_approval',
            raise_if_not_found=False
        )

        if template:
            email_values = {
                'email_to': f"{self.hr_id.work_email}",
                'email_cc': f"{self.hr_head_id.work_email}"
            }
            template.sudo().send_mail(self.id, force_send=True, email_values=email_values)

    def _send_manager_reject_mail(self):
        """Send manager rejection notification to HR & HR Head"""
        self.ensure_one()

        if not (self.hr_id and self.hr_head_id):
            raise ValidationError(_("HR or HR Head is not configured."))

        template = self.env.ref(
            'approval_recruitment.mail_template_manager_reject',
            raise_if_not_found=False
        )

        if template:
            email_values = {
                'email_to': f"{self.hr_id.work_email}",
                'email_cc': f"{self.hr_head_id.work_email}"
            }
            template.sudo().send_mail(self.id, force_send=True, email_values=email_values)

    def _send_hr_approval_mail(self):
        """Send HR approval mail to Employee"""
        self.ensure_one()

        if not self.employee_id.work_email:
            raise ValidationError(_("Employee does not have a work email configured."))

        template = self.env.ref(
            'approval_recruitment.mail_template_hr_approval',
            raise_if_not_found=False
        )

        if template:
            email_values = {
                'email_to': self.employee_id.work_email
            }

            template.sudo().send_mail(self.id, force_send=True, email_values=email_values)

    def _send_hr_reject_mail(self):
        """Send HR rejection mail to Employee"""
        self.ensure_one()

        if not self.employee_id.work_email:
            raise ValidationError(_("Employee does not have a work email configured."))

        template = self.env.ref(
            'approval_recruitment.mail_template_hr_reject',
            raise_if_not_found=False
        )

        if template:
            email_values = {
                'email_to': self.employee_id.work_email
            }

            template.sudo().send_mail(self.id, force_send=True, email_values=email_values)

    def _send_handover_submit_mail(self):
        self.ensure_one()

        template = self.env.ref(
            'approval_recruitment.mail_template_handover_submit',
            raise_if_not_found=False
        )

        if template:
            email_values = {
                'email_to': self.reporting_manager_id.work_email
            }

            template.sudo().send_mail(self.id, force_send=True, email_values=email_values)

    def _send_handover_approved_mail(self):
        self.ensure_one()

        template = self.env.ref(
            'approval_recruitment.mail_template_handover_approved',
            raise_if_not_found=False
        )

        if template:
            email_values = {
                'email_to': self.employee_id.work_email
            }

            template.sudo().send_mail(self.id, force_send=True, email_values=email_values)

    def _send_handover_resubmit_mail(self):
        self.ensure_one()

        template = self.env.ref(
            'approval_recruitment.mail_template_handover_resubmit',
            raise_if_not_found=False
        )

        if template:
            email_values = {
                'email_to': self.employee_id.work_email
            }

            template.sudo().send_mail(self.id, force_send=True, email_values=email_values)

    def _send_it_asset_head_submit_mail(self):
        self.ensure_one()

        template = self.env.ref(
            'approval_recruitment.mail_template_it_assets_submit',
            raise_if_not_found=False
        )

        if template:
            email_values = {
                'email_to': self.it_asset_head_id.work_email
            }

            template.sudo().send_mail(self.id, force_send=True, email_values=email_values)

    def _send_it_asset_head_approve_mail(self):
        self.ensure_one()

        template = self.env.ref(
            'approval_recruitment.mail_template_it_assets_approved',
            raise_if_not_found=False
        )

        if template:
            email_values = {
                'email_to': self.employee_id.work_email
            }

            template.sudo().send_mail(self.id, force_send=True, email_values=email_values)

    def _send_it_asset_head_resubmit_mail(self):
        self.ensure_one()

        template = self.env.ref(
            'approval_recruitment.mail_template_it_assets_resubmit',
            raise_if_not_found=False
        )

        if template:
            email_values = {
                'email_to': self.employee_id.work_email
            }

            template.sudo().send_mail(self.id, force_send=True, email_values=email_values)


    def _send_admin_head_submit_mail(self):
        self.ensure_one()

        template = self.env.ref(
            'approval_recruitment.mail_template_admin_clearance_submit',
            raise_if_not_found=False
        )

        if template:
            email_values = {
                'email_to': self.admin_head_id.work_email
            }

            template.sudo().send_mail(self.id, force_send=True, email_values=email_values)

    def _send_admin_head_approve_mail(self):
        self.ensure_one()

        template = self.env.ref(
            'approval_recruitment.mail_template_payroll_start',
            raise_if_not_found=False
        )

        if template:
            email_values = {
                'email_to': self.payroll_head_id.work_email
            }

            template.sudo().send_mail(self.id, force_send=True, email_values=email_values)

    def _send_admin_head_resubmit_mail(self):
        self.ensure_one()

        template = self.env.ref(
            'approval_recruitment.mail_template_admin_clearance_resubmit',
            raise_if_not_found=False
        )

        if template:
            email_values = {
                'email_to': self.employee_id.work_email
            }

            template.sudo().send_mail(self.id, force_send=True, email_values=email_values)

    def _send_payroll_proceed_mail(self):
        self.ensure_one()

        template = self.env.ref(
            'approval_recruitment.mail_template_payroll_proceed',
            raise_if_not_found=False
        )

        if template:
            email_values = {
                'email_to': self.employee_id.work_email
            }

            template.sudo().send_mail(self.id, force_send=True, email_values=email_values)

    def _send_exit_submit_mail(self):
        self.ensure_one()

        template = self.env.ref(
            'approval_recruitment.mail_template_exit_interview_submitted',
            raise_if_not_found=False
        )

        if template:
            email_values = {
                'email_to': f"{self.hr_id.work_email}",
                'email_cc': f"{self.hr_head_id.work_email}"
            }
            template.sudo().send_mail(self.id, force_send=True, email_values=email_values)

    def action_revoke(self):
        for record in self:
            record.state = 'revoked'
            record.internal_state = 'revoked'