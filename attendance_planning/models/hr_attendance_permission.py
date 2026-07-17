# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import timedelta
from odoo.exceptions import UserError


class HrAttendancePermission(models.Model):
    _name = "hr.attendance.permission"
    _description = "Employee Permission Request"
    #  IMPORTANT: You must inherit these for Chatter to work!
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "employee_id"
    _order = "date desc"

    employee_id = fields.Many2one(
        'hr.employee', string="Employee", required=True,
        default=lambda self: self.env.user.employee_id,
        tracking=True  # Added tracking so changes show in chatter
    )
    date = fields.Date(
        string="Date", required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    reason = fields.Text(string="Reason", required=True, tracking=True)

    # 1. UPDATE THE STATE FIELD
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string="Status", default='draft', tracking=True)

    # 2. ADD THE SUBMIT ACTION (This replaces the 'create' method!)
    def action_submit(self):
        for rec in self:
            rec.state = 'submitted'
            manager = rec.employee_id.parent_id
            if manager and manager.user_id:
                # Post to chatter and notify manager
                rec.message_post(
                    body=f"New Permission Request submitted by {rec.employee_id.name} for {rec.date}. Please review.",
                    partner_ids=[manager.user_id.partner_id.id],
                    subtype_xmlid="mail.mt_comment"
                )

                # TRIGGER EMAIL TO MANAGER
                template = self.env.ref('attendance_planning.email_template_permission_manager',
                                        raise_if_not_found=False)
                if template:
                    template.send_mail(rec.id, force_send=True)

    occasions_used = fields.Integer(
        string="Occasions Used This Month",
        compute="_compute_occasions_used",
        store=False,
    )

    # Hidden field to control the buttons
    can_approve_manager = fields.Boolean(
        string="Can Approve Manager",
        compute="_compute_can_approve_manager"
    )

    @api.depends('employee_id.parent_id', 'employee_id.parent_id.user_id')
    def _compute_can_approve_manager(self):
        for record in self:
            is_manager = False

            # MAPPING: If the employee has a Reporting Manager (parent_id),
            # and that manager's login account (user_id) is the current user.
            if record.employee_id.parent_id and record.employee_id.parent_id.user_id == self.env.user:
                is_manager = True

            # Always allow the top Admins/HR to bypass and approve if needed
            if self.env.user.has_group('hr.group_hr_manager') or self.env.user.has_group('base.group_system'):
                is_manager = True

            record.can_approve_manager = is_manager


    @api.depends('employee_id', 'date', 'state')
    def _compute_occasions_used(self):
        for rec in self:
            if not rec.employee_id or not rec.date:
                rec.occasions_used = 0
                continue
            month_start = rec.date.replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1)
            rec.occasions_used = self.search_count([
                ('employee_id', '=', rec.employee_id.id),
                ('date', '>=', month_start),
                ('date', '<', month_end),
                ('state', '=', 'approved'),
            ])

    def action_approve(self):
        for rec in self:
            month_start = rec.date.replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1)
            count = self.search_count([
                ('employee_id', '=', rec.employee_id.id),
                ('date', '>=', month_start),
                ('date', '<', month_end),
                ('state', '=', 'approved'),
                ('id', '!=', rec.id),
            ])
            if count >= 4:
                raise UserError(
                    f"Limit Reached! {rec.employee_id.name} has already used "
                    f"4 permissions this month. Cannot approve more."
                )
            rec.state = 'approved'


            template = self.env.ref('attendance_planning.email_template_permission_employee', raise_if_not_found=False)
            if template:
                template.send_mail(rec.id, force_send=True)

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'

            # TRIGGER EMAIL TO EMPLOYEE
            template = self.env.ref('attendance_planning.email_template_permission_employee', raise_if_not_found=False)
            if template:
                template.send_mail(rec.id, force_send=True)

    def action_cancel(self):
        for rec in self:
            # We remove the UserError check so Approved can be Cancelled
            rec.state = 'cancelled'

    def action_reset_draft(self):
        # Allow moving back to draft from any state
        self.write({'state': 'draft'})

    def write(self, vals):
        res = super(HrAttendancePermission, self).write(vals)

        # WAKE UP THE ATTENDANCE MATH WHEN APPROVED/REJECTED
        if 'state' in vals:
            for rec in self:
                from datetime import datetime, time
                # Create a 24-hour search window for the date of the permission
                day_start = datetime.combine(rec.date, time.min)
                day_end = datetime.combine(rec.date, time.max)

                # Find the employee's attendance record for this exact day
                attendances = self.env['hr.attendance'].search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('check_in', '>=', day_start),
                    ('check_in', '<=', day_end)
                ])

                # Force the Attendance record to recalculate everything!
                if attendances:
                    attendances._compute_worked()
                    attendances._compute_half_day()
                    attendances._compute_total()

        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super(HrAttendancePermission, self).create(vals_list)
        for rec in records:
            manager = rec.employee_id.parent_id
            if manager and manager.user_id:
                # Post to chatter and notify manager
                rec.message_post(
                    body=f"New Permission Request submitted by {rec.employee_id.name} for {rec.date}. Please review.",
                    partner_ids=[manager.user_id.partner_id.id],
                    subtype_xmlid="mail.mt_comment"
                )

                # TRIGGER EMAIL TO MANAGER
                template = self.env.ref('attendance_planning.email_template_permission_manager',
                                        raise_if_not_found=False)
                if template:
                    template.send_mail(rec.id, force_send=True)

        return records
