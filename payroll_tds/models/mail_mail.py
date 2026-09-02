from odoo import models, api


class MailMail(models.Model):
    _inherit = 'mail.mail'

    @api.model_create_multi
    def create(self, vals_list):

        filtered_vals_list = []

        for vals in vals_list:

            # Block all outgoing emails related to Payslips
            if vals.get('model') == 'hr.payslip':
                continue

            filtered_vals_list.append(vals)

        # If all emails are Payslip emails, do not create them
        if not filtered_vals_list:
            return self.browse()

        return super().create(filtered_vals_list)