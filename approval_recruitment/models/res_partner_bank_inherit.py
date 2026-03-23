from odoo import models, fields, api, _

class ResPartnerBankInherit(models.Model):
    _inherit = 'res.partner.bank'
    _description = 'Res Partner Bank Inherit'

    ls_ifsc_code = fields.Char(string="IFSC Code")
    ls_account_type_id = fields.Many2one('ls.account.type',string="Account Type")