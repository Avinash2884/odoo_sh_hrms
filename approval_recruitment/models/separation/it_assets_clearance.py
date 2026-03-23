from odoo import models, fields, api, _

class ItAssetsClearance(models.Model):
    _name = 'it.assets.clearance'
    _description = 'It Assets Clearance'

    name = fields.Many2one('device.type',string="Device type",required=True,ondelete="restrict")
    specification = fields.Char(string="Specification/ID")
    issued = fields.Selection([
        ('yes','Yes'),
        ('no','No'),
    ],string="Issued")
    returned = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ], string="Returned")
    condition = fields.Selection([
        ('good', 'Good'),
        ('damaged', 'Damaged'),
    ], string="Condition")
    dues_cleared = fields.Selection([
        ('cleared', 'Cleared'),
        ('pending', 'Pending'),
        ('missing', 'Missing'),
        ('na', 'N/A'),
    ], string="Dues Cleared")
    asset_value_cost = fields.Integer(string="Asset Value Cost")
    remarks = fields.Text(string="Remarks")

    it_assets_state = fields.Selection([
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('resubmitted', 'Resubmitted'),
    ], tracking=True)

    initiate_separation_id = fields.Many2one('initiate.separation',string="Initiate Separation")