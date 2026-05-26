from odoo import models, fields, api, _

class DeviceType(models.Model):
    _name = 'device.type'
    _description = 'Device Type'
    _copy = True

    name = fields.Char(string="Device Name",required=True)
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )