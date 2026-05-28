from odoo import models, fields, api

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
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")

    file_data = fields.Binary(string="Upload File")
    file_name = fields.Char(string="File Name")
    hr_head_name = fields.Many2one('res.users', string="Head Name")
    hr_description = fields.Char(string="Description")

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

    @api.model
    def cron_unpublish_expired_jobs(self):
        today = fields.Date.context_today(self)

        print("CRON START")
        print("Today:", today)

        expired_jobs = self.search([
            ('end_date', '!=', False),
            ('end_date', '<=', today),
            ('website_published', '=', True)
        ])

        print("Found:", len(expired_jobs))
        print("Jobs:", expired_jobs.mapped('name'))

        if expired_jobs:
            expired_jobs.write({'website_published': False})
            print("Unpublished:", expired_jobs.mapped('name'))
        else:
            print("No jobs matched")

        print("END")