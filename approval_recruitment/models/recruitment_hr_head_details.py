from odoo import models, fields, api , _

class RecruitmentHRHeadDetails(models.Model):
    _name = 'recruitment.hr.head.details'
    _description = 'HR Head Details'

    name = fields.Many2one(
        'res.users',
        string='Head Name',
        required=True
    )

    description = fields.Text(
        string='Description'
    )

    file = fields.Binary(
        string='Upload File'
    )

    file_name = fields.Char(
        string='File Name'
    )