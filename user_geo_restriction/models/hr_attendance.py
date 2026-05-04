from odoo import models, api, _, fields
from odoo.exceptions import UserError
from geopy.distance import geodesic


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    geo_restriction_id = fields.Many2one(
        'geo.restriction',
        string="Check-in Location"
    )

    @api.model
    def create(self, vals_list):

        records = super().create(vals_list)

        # ensure list
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        for rec, vals in zip(records, vals_list):
            rec._check_geo_restriction(vals)

        return records

    def write(self, vals):
        res = super().write(vals)
        self._check_geo_restriction(vals)
        return res

    def _check_geo_restriction(self, vals):

        for attendance in self:

            geo_locations = self.env['geo.restriction'].search([
                ('employee_ids', 'in', attendance.employee_id.id)
            ])

            if not geo_locations:
                return

            # -------------------------
            # ✅ CHECK-IN
            # -------------------------
            if vals.get('check_in'):

                lat = attendance.in_latitude
                lon = attendance.in_longitude

                if not lat or not lon:
                    raise UserError(_("Location required for check-in."))

                for geo in geo_locations:
                    distance = geodesic(
                        (geo.company_latitude, geo.company_longitude),
                        (lat, lon)
                    ).meters

                    if distance <= geo.allowed_distance:
                        # 🔥 முக்கியம்: matched geo save
                        attendance.geo_restriction_id = geo.id
                        break
                else:
                    raise UserError(_("Outside allowed location (Check-in)."))

            # -------------------------
            # ✅ CHECK-OUT
            # -------------------------
            if vals.get('check_out'):

                lat = attendance.out_latitude
                lon = attendance.out_longitude

                if not lat or not lon:
                    raise UserError(_("Location required for check-out."))

                if not attendance.geo_restriction_id:
                    raise UserError(_("Check-in location not found."))

                geo = attendance.geo_restriction_id

                distance = geodesic(
                    (geo.company_latitude, geo.company_longitude),
                    (lat, lon)
                ).meters

                # 🔥 same location check
                if distance > geo.allowed_distance:
                    raise UserError(_(
                        "You must check-out from the same location as check-in."
                    ))

    def _attendance_action_change(self, geo_ip_response=None):

        res = super()._attendance_action_change(geo_ip_response)

        attendance = self.env['hr.attendance'].search([
            ('employee_id', '=', self.id)
        ], order="id desc", limit=1)

        if attendance:
            if attendance.check_out:
                message = "✅ Check-out successful"
            else:
                message = "✅ Check-in successful"

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'attendance.popup',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_message': message
                }
            }

        return res