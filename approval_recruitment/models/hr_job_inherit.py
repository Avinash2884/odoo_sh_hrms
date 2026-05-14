from odoo import models, fields

class HrJobInherit(models.Model):
    _inherit = 'hr.job'
    _description = 'HR Job'

    approval_experience_minimum = fields.Integer(string="Experience Min")
    approval_experience_maximum = fields.Integer(string="Experience Max")
    approval_overall_budget_for_all_posting = fields.Integer(string="Budget for All Posting")
    approval_budget_for_each_employee_position = fields.Integer(string="Budget for Per Employee")
    hr_head = fields.Many2one('hr.employee',string="HR head")
    hr_interviewer_ids = fields.Many2many(
        'res.users',
        'hr_job_interviewer_rel',
        'category_id',
        'user_id',
        string="Recruitment Interviewers",
        help="Set Interviewers for All Candidates",
    )

    def action_send_job_email(self):
        self.ensure_one()

        partner = False
        email = self.user_id.partner_id.email  # recruiter email

        if email:
            partner = self.env['res.partner'].search([
                ('email', '=', email)
            ], limit=1)

            if not partner:
                partner = self.env['res.partner'].create({
                    'name': self.user_id.name,
                    'email': email,
                })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Send Email',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model': 'hr.job',
                'default_res_ids': self.ids,
                'default_composition_mode': 'comment',
                'default_partner_ids': [(6, 0, [partner.id])] if partner else [],
                'default_email_to': email,
            }
        }