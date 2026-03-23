from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import datetime

class WeekendWorkApproval(models.Model):
    _name = 'weekend.work.approval'
    _description = 'Weekend Work Approval Request'
    _rec_name = 'employee_id'

    # Auto-populated Employee (based on logged-in user)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee Name',
        required=True,
        default=lambda self: self.env.user.employee_id,
        readonly=True
    )

    # Dropdown for Saturday / Sunday
    working_day = fields.Selection(
        [
            ('saturday', 'Saturday'),
            ('sunday', 'Sunday'),
        ],
        string='Working Day',
        required=True
    )

    # Date field — user can only select weekend (validated)
    work_date = fields.Date(
        string='Date',
        required=True
    )

    # Reason for working on weekend
    reason = fields.Text(
        string='Reason for Weekend Work',
        required=True
    )

    # Optional: status tracking (for manager approval later)
    state = fields.Selection(
        [
            ('draft', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected')
        ],
        string='Status',
    )

    # ---------- VALIDATION ----------
    @api.constrains('work_date')
    def _check_weekend_date(self):
        for record in self:
            if record.work_date:
                weekday = record.work_date.weekday()  # Monday=0, Sunday=6
                if weekday not in [5, 6]:  # 5=Saturday, 6=Sunday
                    raise ValidationError(_("You can only select a Saturday or Sunday date."))

    # ---------- ACTION BUTTONS (optional, for future) ----------

    def _send_email(self, subject, body, recipients):
        """Utility method to send email notifications."""
        mail_values = {
            'subject': subject,
            'body_html': body,
            'email_to': ','.join(recipients),
            'author_id': self.env.user.partner_id.id,
        }
        mail = self.env['mail.mail'].create(mail_values)
        mail.send()


    def action_submit(self):
        """When employee submits → notify manager."""
        for rec in self:
            rec.state = 'draft'
            manager = rec.employee_id.parent_id  # Manager (if set in HR)
            if manager and manager.work_email:
                subject = _("Weekend Work Request Submitted by %s") % rec.employee_id.name
                body = _(
                    "<p>Dear %s,</p>"
                    "<p>%s has submitted a weekend work request for <b>%s</b> (%s).</p>"
                    "<p><b>Reason:</b> %s</p>"
                    "<p>Please review and approve or reject the request.</p>"
                ) % (manager.name, rec.employee_id.name, rec.work_date, rec.working_day.title(), rec.reason)
                self._send_email(subject, body, [manager.work_email])

    def action_approve(self):
        """When manager approves → notify employee."""
        for rec in self:
            rec.state = 'approved'
            employee = rec.employee_id
            if employee and employee.work_email:
                subject = _("Weekend Work Request Approved")
                body = _(
                    "<p>Dear %s,</p>"
                    "<p>Your weekend work request for <b>%s</b> (%s) has been <b>approved</b> by your manager.</p>"
                ) % (employee.name, rec.work_date, rec.working_day.title())
                self._send_email(subject, body, [employee.work_email])

    def action_reject(self):
        """When manager rejects → notify employee."""
        for rec in self:
            rec.state = 'rejected'
            employee = rec.employee_id
            if employee and employee.work_email:
                subject = _("Weekend Work Request Rejected")
                body = _(
                    "<p>Dear %s,</p>"
                    "<p>Your weekend work request for <b>%s</b> (%s) has been <b>rejected</b> by your manager.</p>"
                ) % (employee.name, rec.work_date, rec.working_day.title())
                self._send_email(subject, body, [employee.work_email])