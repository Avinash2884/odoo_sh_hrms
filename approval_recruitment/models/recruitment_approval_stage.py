from odoo import models, fields, api, _
from odoo.exceptions import UserError

class RecruitmentApprovalStage(models.Model):
    _name = 'recruitment.approval.stage'
    _description = 'Recruitment Approval Stage'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'job_position_id'

    name = fields.Char(string="Recruitment Approval Name", tracking=True)
    job_position_id = fields.Many2one('hr.job', string="Recruitment Job Position", tracking=True,required=True)
    user_id = fields.Many2one(
        'res.users',
        string="User",
        related='job_position_id.user_id',
        store=True,
        readonly=True
    )

    approval_applicant_ids = fields.Many2many(
        'hr.applicant',
        string="Approval Stage Applicants",
        compute='_compute_approval_applicant_ids',
        store=True
    )

    job_position_budget = fields.Integer(
        string="Job Position Budget",
        related='job_position_id.approval_overall_budget_for_all_posting',
        store=True
    )

    @api.depends('job_position_id')
    def _compute_approval_applicant_ids(self):
        approval_stage = self.env['hr.recruitment.stage'].search([('name', '=', 'Approval')], limit=1)
        for record in self:
            if record.job_position_id and approval_stage:
                applicants = self.env['hr.applicant'].search([
                    ('job_id', '=', record.job_position_id.id),
                    ('stage_id', '=', approval_stage.id)
                ])
                record.approval_applicant_ids = [(6, 0, applicants.ids)]
            else:
                record.approval_applicant_ids = [(5, 0, 0)]

    def action_send_approval_mail(self):
        for record in self:
            if not record.user_id or not record.user_id.email:
                raise UserError(_("Responsible user or their email is missing."))

            applicants = record.approval_applicant_ids
            if not applicants:
                raise UserError(_("No applicants found in the 'Approval' stage for this position."))

            applicant_names = ', '.join(applicants.mapped('partner_name'))
            subject = _("Recruitment Approval Update - %s") % record.job_position_id.name

            # 🧩 include budget details
            budget_text = _("Total Budget for this Postings: ₹%s") % (record.job_position_budget or 0)

            body = _(
                "Dear %s,<br/><br/>"
                "The following applicants are currently in the 'Approval' stage for the job position <b>%s</b>:<br/>"
                "<b>%s</b><br/><br/>"
                "%s<br/><br/>"
                "Regards,<br/>Odoo Recruitment System"
            ) % (record.user_id.name, record.job_position_id.name, applicant_names, budget_text)

            mail_values = {
                'subject': subject,
                'body_html': body,
                'email_to': record.user_id.email,
                'email_from': self.env.user.email or 'noreply@example.com',
            }

            self.env['mail.mail'].create(mail_values).send()

            record.message_post(
                body=_("Approval email sent to %s (Budget: ₹%s)") % (record.user_id.email, record.job_position_budget)
            )