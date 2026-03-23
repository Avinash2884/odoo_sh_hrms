from odoo import models

class HrContractSalaryOffer(models.Model):
    _inherit = 'hr.contract.salary.offer'

    def write(self, vals):
        res = super().write(vals)

        if 'state' in vals:
            for record in self:
                if record.state == 'full_signed':
                    template = self.env.ref('approval_recruitment.mail_template_offer_acceptance')
                    template.send_mail(record.id, force_send=True)

        return res