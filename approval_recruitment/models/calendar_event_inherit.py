from odoo import models, fields

class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    reminder_sent_12h = fields.Boolean(default=False)
    reminder_sent_24h = fields.Boolean(default=False)

    def _cron_send_interview_reminder(self):
        print("hai")
        now = fields.Datetime.now()

        events = self.search([
            ('applicant_id', '!=', False),
            ('start', '!=', False),
        ])

        template = self.env.ref('approval_recruitment.calendar_template_meeting_interview_remainder')
        print("template")

        for event in events:
            diff_hours = (event.start - now).total_seconds() / 3600

            # 24 hours reminder
            if 23 <= diff_hours <= 24 and not event.reminder_sent_24h:
                template.send_mail(event.id, force_send=True)
                event.reminder_sent_24h = True
                print("Mail sent to 24")

            # 12 hours reminder
            if 11 <= diff_hours <= 12 and not event.reminder_sent_12h:
                template.send_mail(event.id, force_send=True)
                event.reminder_sent_12h = True
                print("Mail sent to 12")

    def action_send_interview_pending(self):
        template = self.env.ref('approval_recruitment.calendar_template_interview_outcome_pending')
        for rec in self:
            template.send_mail(rec.id, force_send=True)

    def action_send_interview_reschedule(self):
        template = self.env.ref('approval_recruitment.calendar_template_interview_reschedule_request')
        for rec in self:
            template.send_mail(rec.id, force_send=True)