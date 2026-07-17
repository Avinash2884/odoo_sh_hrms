from odoo import models, fields, api

class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    cc_partner_ids = fields.Many2many(
        'res.partner',
        'mail_compose_message_cc_rel',
        'wizard_id',
        'partner_id',
        string="Cc"
    )

    # ✅ Auto populate HR Head in CC
    @api.model
    def default_get(self, fields_list):
        print("\n===== DEFAULT_GET CALLED =====")

        res = super().default_get(fields_list)

        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')

        print("Active Model:", active_model)
        print("Active ID:", active_id)

        applicant = False

        # ✅ HANDLE BOTH MODELS
        if active_model == 'hr.applicant' and active_id:
            applicant = self.env['hr.applicant'].browse(active_id)
            print("From Applicant screen")

        elif active_model == 'hr.contract.salary.offer' and active_id:
            offer = self.env['hr.contract.salary.offer'].browse(active_id)
            print("From Offer screen:", offer)

            applicant = offer.applicant_id   # 🔥 IMPORTANT
            print("Applicant from offer:", applicant)

        else:
            print("❌ Unsupported model")

        # ✅ COMMON LOGIC
        if applicant and applicant.job_id and applicant.job_id.hr_head:
            hr_head = applicant.job_id.hr_head

            print("HR HEAD:", hr_head)

            partner = False

            if hr_head.user_id and hr_head.user_id.partner_id:
                partner = hr_head.user_id.partner_id
                print("Partner from user:", partner)

            elif hasattr(hr_head, 'work_contact_id') and hr_head.work_contact_id:
                partner = hr_head.work_contact_id
                print("Partner from work_contact:", partner)

            else:
                print("⚠️ No partner found")

            if partner and partner.email:
                res['cc_partner_ids'] = [(6, 0, [partner.id])]
                print("✅ CC SET:", partner.name)
            else:
                print("❌ Partner missing email")

        else:
            print("❌ Applicant / Job / HR Head missing")

        print("===== DEFAULT_GET END =====\n")

        return res

    # ✅ Inject CC into outgoing mail
    def action_send_mail(self):
        print("\n===== SEND MAIL CALLED =====")

        res = super().action_send_mail()

        if self.cc_partner_ids:
            emails = self.cc_partner_ids.mapped('email')
            emails = [e for e in emails if e]

            if emails:
                mails = self.env['mail.mail'].search(
                    [('author_id', '=', self.env.user.partner_id.id)],
                    order='id desc',
                    limit=10
                )

                for mail in mails:
                    existing_cc = mail.email_cc or ''
                    new_cc = ','.join(emails)

                    mail.email_cc = (
                        existing_cc + ',' + new_cc if existing_cc else new_cc
                    )

                    print("✅ Updated Mail CC:", mail.email_cc)

        print("===== SEND MAIL END =====\n")

        return res