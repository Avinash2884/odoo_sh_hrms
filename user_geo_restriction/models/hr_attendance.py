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

    def _round_geo(self, value):
        return round(value, 4) if value is not None else value

    def _check_geo_restriction(self, vals):

        for attendance in self:

            _logger.info("🚀 ===== GEO CHECK START =====")
            _logger.info("👤 Employee: %s (ID: %s)", attendance.employee_id.name, attendance.employee_id.id)

            geo_locations = attendance.employee_id.geo_restriction_ids

            # -------------------------
            # CHECK-IN
            # -------------------------
            if vals.get('check_in'):

                # ✅ FIRST assign
                lat = vals.get('in_latitude') or attendance.in_latitude
                lon = vals.get('in_longitude') or attendance.in_longitude

                _logger.info("📍 RAW Check-in Lat: %s", lat)
                _logger.info("📍 RAW Check-in Lon: %s", lon)

                if lat is None or lon is None:
                    _logger.error("❌ Missing check-in location")
                    raise UserError(_("Location required for check-in."))

                # ✅ THEN round
                lat = self._round_geo(lat)
                lon = self._round_geo(lon)

                _logger.info("🎯 Rounded Lat: %s", lat)
                _logger.info("🎯 Rounded Lon: %s", lon)

                matched_geo = False

                for geo in geo_locations:

                    office_lat = self._round_geo(geo.company_latitude)
                    office_lon = self._round_geo(geo.company_longitude)
                    _logger.info("🎯 Office Lat: %s", office_lat)
                    _logger.info("🎯 Office Lon: %s", office_lon)

                    distance = geodesic(
                        (office_lat, office_lon),
                        (lat, lon)
                    ).meters

                    allowed_radius = geo.allowed_distance + 100

                    _logger.info("📏 Distance: %.2f | Allowed: %s", distance, allowed_radius)

                    if distance <= allowed_radius:
                        attendance.geo_restriction_id = geo.id
                        matched_geo = True
                        break

                if not matched_geo:
                    raise UserError(_("Outside allowed location (Check-in)."))

            # -------------------------
            # CHECK-OUT
            # -------------------------
            if vals.get('check_out'):

                # ✅ FIRST assign
                lat = vals.get('out_latitude') or attendance.out_latitude
                lon = vals.get('out_longitude') or attendance.out_longitude

                _logger.info("📍 RAW Check-out Lat: %s", lat)
                _logger.info("📍 RAW Check-out Lon: %s", lon)

                if lat is None or lon is None:
                    _logger.error("❌ Missing check-out location")
                    raise UserError(_("Location required for check-out."))

                # ✅ THEN round
                lat = self._round_geo(lat)
                lon = self._round_geo(lon)

                _logger.info("🎯 Rounded Lat: %s", lat)
                _logger.info("🎯 Rounded Lon: %s", lon)

                matched_geo = False

                for geo in geo_locations:

                    office_lat = self._round_geo(geo.company_latitude)
                    office_lon = self._round_geo(geo.company_longitude)
                    _logger.info("🎯 Office Lat: %s", office_lat)
                    _logger.info("🎯 Office Lon: %s", office_lon)

                    distance = geodesic(
                        (office_lat, office_lon),
                        (lat, lon)
                    ).meters

                    allowed_radius = geo.allowed_distance + 100

                    _logger.info("📏 Distance: %.2f | Allowed: %s", distance, allowed_radius)

                    if distance <= allowed_radius:
                        attendance.check_out_geo_restriction_id = geo.id
                        matched_geo = True
                        break

                if not matched_geo:
                    raise UserError(_("You must check-out from an assigned location."))

            _logger.info("🏁 ===== GEO CHECK END =====\n")