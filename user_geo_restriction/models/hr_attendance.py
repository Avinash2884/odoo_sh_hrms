from odoo import models, api, _, fields
from odoo.exceptions import UserError, ValidationError
from geopy.distance import geodesic
import logging
_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    geo_restriction_id = fields.Many2one(
        'geo.restriction',
        string="Check-in Location"
    )
    check_out_geo_restriction_id = fields.Many2one(
        'geo.restriction',
        string="Check-out Location"
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

    def _round_geo(self, value, digits=5):
        return round(value, digits) if value is not None else value

    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        Always calculate using ORIGINAL values (no rounding)
        """
        return geodesic((lat1, lon1), (lat2, lon2)).meters

    def _check_geo_restriction(self, vals):

        for attendance in self:

            _logger.info("🚀 ===== GEO CHECK START =====")
            _logger.info("👤 Employee: %s (ID: %s)",
                         attendance.employee_id.name,
                         attendance.employee_id.id)

            geo_locations = attendance.employee_id.geo_restriction_ids

            # =========================
            # COMMON FUNCTION
            # =========================
            def validate_geo(lat, lon, geo_field_name):

                if lat is None or lon is None:
                    _logger.error("❌ Missing location")
                    raise UserError(_("Location required."))

                # 🔹 Round only for logging/debug
                r_lat = self._round_geo(lat)
                r_lon = self._round_geo(lon)

                _logger.info("📍 RAW Lat: %s | Lon: %s", lat, lon)
                _logger.info("🎯 Rounded Lat: %s | Lon: %s", r_lat, r_lon)

                matched_geo = False

                for geo in geo_locations:

                    office_lat = geo.company_latitude
                    office_lon = geo.company_longitude

                    # 🔥 NO rounding for calculation
                    distance = self._calculate_distance(
                        office_lat, office_lon,
                        lat, lon
                    )

                    # 🔥 buffer added
                    allowed_radius = geo.allowed_distance + 150

                    _logger.info(
                        "📏 Office(%s,%s) → User(%s,%s) | Distance: %.2f m | Allowed: %s",
                        self._round_geo(office_lat),
                        self._round_geo(office_lon),
                        r_lat, r_lon,
                        distance,
                        allowed_radius
                    )

                    if distance <= allowed_radius:
                        setattr(attendance, geo_field_name, geo.id)
                        matched_geo = True
                        break

                return matched_geo

            # =========================
            # CHECK-IN
            # =========================
            if vals.get('check_in'):

                lat = vals.get('in_latitude') or attendance.in_latitude
                lon = vals.get('in_longitude') or attendance.in_longitude

                if not validate_geo(lat, lon, 'geo_restriction_id'):
                    raise UserError(_("Outside allowed location (Check-in)."))

            # =========================
            # CHECK-OUT
            # =========================
            if vals.get('check_out'):

                lat = vals.get('out_latitude') or attendance.out_latitude
                lon = vals.get('out_longitude') or attendance.out_longitude

                if not validate_geo(lat, lon, 'check_out_geo_restriction_id'):
                    raise UserError(_("You must check-out from an assigned location."))

            _logger.info("🏁 ===== GEO CHECK END =====\n")