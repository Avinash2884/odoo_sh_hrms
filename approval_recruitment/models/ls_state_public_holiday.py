from odoo import models, fields, api

class LsStatePublicHoliday(models.Model):
    _name = 'ls.state.public.holiday'
    _description = 'Ls State Public Holiday'
    _rec_name = 'state_id'

    state_id = fields.Many2one('res.country.state', string='State')
    holiday_line_ids = fields.One2many(
        'ls.public.holiday',
        'state_holiday_id',
        string='Public Holidays'
    )