# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    edp_restrict_sunday = fields.Boolean(string="Restrict Sundays")
    edp_restrict_sat_1 = fields.Boolean(string="Restrict 1st Saturday")
    edp_restrict_sat_2 = fields.Boolean(string="Restrict 2nd Saturday")
    edp_restrict_sat_3 = fields.Boolean(string="Restrict 3rd Saturday")
    edp_restrict_sat_4 = fields.Boolean(string="Restrict 4th Saturday")
    edp_restrict_sat_5 = fields.Boolean(string="Restrict 5th Saturday")

    # field_name -> (ir.config_parameter key, default value if never saved before)
    _EDP_PARAM_MAP = {
        'edp_restrict_sunday': ('attendance.edp_restrict_sunday', True),
        'edp_restrict_sat_1': ('attendance.edp_restrict_sat_1', False),
        'edp_restrict_sat_2': ('attendance.edp_restrict_sat_2', True),
        'edp_restrict_sat_3': ('attendance.edp_restrict_sat_3', False),
        'edp_restrict_sat_4': ('attendance.edp_restrict_sat_4', True),
        'edp_restrict_sat_5': ('attendance.edp_restrict_sat_5', False),
    }

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        icp = self.env['ir.config_parameter'].sudo()
        for fname, (param_key, default_val) in self._EDP_PARAM_MAP.items():
            stored = icp.get_param(param_key)
            if stored is None:
                res[fname] = default_val
            else:
                res[fname] = str(stored).strip().lower() in ('true', '1', 't', 'yes', 'y')
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        icp = self.env['ir.config_parameter'].sudo()
        for fname, (param_key, _default_val) in self._EDP_PARAM_MAP.items():
            # Always store as an explicit string, never a raw Python bool,
            # so Odoo's set_param() never deletes the row on an unchecked (False) value.
            icp.set_param(param_key, str(bool(self[fname])))