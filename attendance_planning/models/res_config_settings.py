# -*- coding: utf-8 -*-
from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Notice we use config_parameter instead of related='company_id...'
    # This stores the settings safely without altering the database schema!
    edp_restrict_sunday = fields.Boolean(string="Restrict Sundays", config_parameter='attendance.edp_restrict_sunday', default=True)
    edp_restrict_sat_1 = fields.Boolean(string="Restrict 1st Saturday", config_parameter='attendance.edp_restrict_sat_1', default=False)
    edp_restrict_sat_2 = fields.Boolean(string="Restrict 2nd Saturday", config_parameter='attendance.edp_restrict_sat_2', default=True)
    edp_restrict_sat_3 = fields.Boolean(string="Restrict 3rd Saturday", config_parameter='attendance.edp_restrict_sat_3', default=False)
    edp_restrict_sat_4 = fields.Boolean(string="Restrict 4th Saturday", config_parameter='attendance.edp_restrict_sat_4', default=True)
    edp_restrict_sat_5 = fields.Boolean(string="Restrict 5th Saturday", config_parameter='attendance.edp_restrict_sat_5', default=False)