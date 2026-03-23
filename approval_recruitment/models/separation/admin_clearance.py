from odoo import models, fields, api, _

class AdminClearance(models.Model):
    _name = 'admin.clearance'
    _description = 'Admin Clearance'

    name = fields.Many2one('item.name',string="Item Name",required=True)
    issued = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ], string="Issued")
    returned = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ], string="Returned")
    dues_cleared = fields.Selection([
        ('cleared', 'Cleared'),
        ('pending', 'Pending'),
        ('na', 'N/A'),
    ], string="Dues Cleared")
    remarks = fields.Text(string="Remarks")

    admin_state = fields.Selection([
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('resubmitted', 'Resubmitted'),
    ], tracking=True)


    initiate_separation_id = fields.Many2one('initiate.separation', string="Initiate Separation")