
from odoo import models, fields, api, _

class ResCompanyInherit(models.Model):
    _inherit = 'res.company'
    _description = 'Res Company'

    state_id = fields.Many2one('res.country.state',string='State')
