from odoo import models, fields, api

class LsPublicHoliday(models.Model):
    _name = 'ls.public.holiday'
    _description = 'Ls Public Holiday'

    name = fields.Char(string='Name',tracking=True)
    date = fields.Date(string='Date', required=True)
    state_holiday_id = fields.Many2one(
        'ls.state.public.holiday',
        string='State Holiday',
        ondelete='cascade',
        required=True
    )