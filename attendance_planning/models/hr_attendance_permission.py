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
        tracking=True # Added tracking so changes show in chatter
    )
    date = fields.Date(
        string="Date", required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    reason = fields.Text(string="Reason", required=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string="Status", default='draft', tracking=True)

    occasions_used = fields.Integer(
        string="Occasions Used This Month",
        compute="_compute_occasions_used",
        store=False,
    )

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

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_cancel(self):
        for rec in self:
            # We remove the UserError check so Approved can be Cancelled
            rec.state = 'cancelled'

    def action_reset_draft(self):
        # Allow moving back to draft from any state
        self.write({'state': 'draft'})

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
        return records