# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, time
import pytz  # Critical for the timezone fix!


class HrEdpRequest(models.Model):
    _name = 'hr.edp.request'
    _description = 'Extra Duty Plan (EDP) Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True,
                                  default=lambda self: self.env.user.employee_id)

    # EXACT MAPPING: Auto-fetches the specific manager and HR head for this employee
    manager_id = fields.Many2one('hr.employee', related='employee_id.parent_id', string='Reporting Manager', store=True)
    hr_head_id = fields.Many2one('hr.employee', related='employee_id.hr_head_id', string='HR Head', store=True)

    date = fields.Date(string='EDP Date', required=True)
    calendar_id = fields.Many2one('resource.calendar', string='Shift Template', required=True)

    # ---> CHANGED: Removed 'manager_approved' (Waiting for HR) intermediate state
    # Single approval flow: Draft -> Submitted -> Approved & Allocated
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Waiting for Manager'),
        ('approved', 'Approved & Allocated'),
        ('refused', 'Refused')
    ], string='Status', default='draft', tracking=True)

    # 👇 VISIBILITY CHECKERS added here 👇
    can_approve_manager = fields.Boolean(compute='_compute_can_approve')

    def _compute_can_approve(self):
        for req in self:
            current_employee = self.env.user.employee_id
            is_admin = self.env.user.has_group('base.group_erp_manager')

            # True ONLY if logged-in user is the assigned Manager (or an Admin)
            req.can_approve_manager = is_admin or (current_employee and current_employee == req.manager_id)

    @api.depends('employee_id', 'date')
    def _compute_name(self):
        for req in self:
            if req.employee_id and req.date:
                req.name = f"EDP: {req.employee_id.name} - {req.date}"
            else:
                req.name = "New EDP Request"

    # --- THE SECURE BUTTON ACTIONS ---
    def action_submit(self):
        for req in self:
            req.write({'state': 'submitted'})

            # Notify the exact mapped Manager
            if req.manager_id and req.manager_id.user_id:
                req.message_post(
                    body=f"Hello {req.manager_id.name}, an EDP request for {req.employee_id.name} on {req.date} is waiting for your approval.",
                    partner_ids=[req.manager_id.user_id.partner_id.id]
                )

    # ---> CHANGED: Manager approval now directly creates the planning slot
    # (this used to be in action_hr_approve — HR step removed entirely)
    def action_manager_approve(self):
        for req in self:
            # SECURITY: Only the assigned Manager can approve
            if self.env.user.employee_id != req.manager_id and not self.env.user.has_group('base.group_erp_manager'):
                raise UserError("Access Denied: Only the assigned Reporting Manager can approve this step!")

            # Timezone Fix for Planning App
            tz_name = req.employee_id.tz or self.env.user.tz or 'UTC'
            tz = pytz.timezone(tz_name)

            local_start = datetime.combine(req.date, time.min)
            local_end = datetime.combine(req.date, time.max)

            start_dt_utc = tz.localize(local_start).astimezone(pytz.utc).replace(tzinfo=None)
            end_dt_utc = tz.localize(local_end).astimezone(pytz.utc).replace(tzinfo=None)

            # Auto-Allocate the Shift
            self.env['planning.slot'].sudo().create({
                'employee_id': req.employee_id.id,
                'resource_id': req.employee_id.resource_id.id,
                'calendar_id': req.calendar_id.id,
                'start_datetime': start_dt_utc,
                'end_datetime': end_dt_utc,
                'state': 'published',
            })

            req.write({'state': 'approved'})

            # Notify Employee of Success
            if req.employee_id.user_id:
                req.message_post(
                    body=f"Congratulations! Your EDP request for {req.date} has been approved and allocated in your schedule.",
                    partner_ids=[req.employee_id.user_id.partner_id.id]
                )

    def action_refuse(self):
        for req in self:
            # SECURITY: Only Manager can refuse
            allowed_users = [req.manager_id.user_id.id] if req.manager_id.user_id else []
            if self.env.user.id not in allowed_users and not self.env.user.has_group('base.group_erp_manager'):
                raise UserError("Access Denied: You do not have permission to refuse this request.")

            req.write({'state': 'refused'})

            # Notify Employee of Rejection
            if req.employee_id.user_id:
                req.message_post(
                    body=f"Your EDP request for {req.date} has been refused.",
                    partner_ids=[req.employee_id.user_id.partner_id.id]
                )