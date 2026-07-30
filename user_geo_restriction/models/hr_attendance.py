import math
import logging
from odoo import models, api, _, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    geo_restriction_id = fields.Many2one('geo.restriction', string="Check-in Location")
    check_out_geo_restriction_id = fields.Many2one('geo.restriction', string="Check-out Location")

    in_accuracy = fields.Float(string="Check-in GPS Accuracy (m)")
    out_accuracy = fields.Float(string="Check-out GPS Accuracy (m)")

    MAX_ALLOWED_ACCURACY = 100  # meters, tune based on testing

    @api.model
    def create(self, vals_list):
        records = super().create(vals_list)
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        for rec, vals in zip(records, vals_list):
            rec._check_geo_restriction(vals)
        return records

    def write(self, vals):
        res = super().write(vals)
        self._check_geo_restriction(vals)
        return res

    def _round_geo(self, value, digits=5):
        return round(value, digits) if value is not None else value

    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        Haversine formula - pure Python, no external library needed.
        Returns distance in meters.
        """
        R = 6371000
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def _check_geo_restriction(self, vals):

        for attendance in self:

            _logger.info("🚀 ===== GEO CHECK START =====")
            _logger.info("👤 Employee: %s (ID: %s)",
                         attendance.employee_id.name, attendance.employee_id.id)

            geo_locations = attendance.employee_id.geo_restriction_ids

            def validate_geo(lat, lon, geo_field_name, accuracy=None):

                if lat is None or lon is None:
                    _logger.error("❌ Missing location")
                    raise UserError(_("Location required."))

                # 🔥 NEW: Accuracy check BEFORE distance check
                if accuracy is not None and accuracy > self.MAX_ALLOWED_ACCURACY:
                    _logger.warning("⚠️ Poor GPS accuracy: %.2f m", accuracy)
                    raise UserError(_(
                        "Your device's location accuracy is too low (%.0f m). "
                        "Please move to an open area, enable Precise Location, and try again."
                    ) % accuracy)

                r_lat = self._round_geo(lat)
                r_lon = self._round_geo(lon)

                _logger.info("📍 RAW Lat: %s | Lon: %s | Accuracy: %s", lat, lon, accuracy)

                matched_geo = False

                for geo in geo_locations:
                    office_lat = geo.company_latitude
                    office_lon = geo.company_longitude

                    distance = self._calculate_distance(office_lat, office_lon, lat, lon)
                    allowed_radius = geo.allowed_distance + max(150, geo.allowed_distance * 0.1)

                    _logger.info(
                        "📏 Office(%s,%s) → User(%s,%s) | Distance: %.2f m | Allowed: %s",
                        self._round_geo(office_lat), self._round_geo(office_lon),
                        r_lat, r_lon, distance, allowed_radius
                    )

                    if distance <= allowed_radius:
                        setattr(attendance, geo_field_name, geo.id)
                        matched_geo = True
                        break

                return matched_geo

            if vals.get('check_in'):
                lat = vals.get('in_latitude') or attendance.in_latitude
                lon = vals.get('in_longitude') or attendance.in_longitude
                accuracy = vals.get('in_accuracy') or attendance.in_accuracy

                if not validate_geo(lat, lon, 'geo_restriction_id', accuracy):
                    raise UserError(_("Outside allowed location (Check-in)."))

            if vals.get('check_out'):
                lat = vals.get('out_latitude') or attendance.out_latitude
                lon = vals.get('out_longitude') or attendance.out_longitude
                accuracy = vals.get('out_accuracy') or attendance.out_accuracy

                if not validate_geo(lat, lon, 'check_out_geo_restriction_id', accuracy):
                    raise UserError(_("You must check-out from an assigned location."))

            _logger.info("🏁 ===== GEO CHECK END =====\n")