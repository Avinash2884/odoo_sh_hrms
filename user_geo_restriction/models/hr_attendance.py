from odoo import models, api, _, fields
from odoo.exceptions import UserError
from geopy.distance import geodesic
import logging

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    geo_restriction_id = fields.Many2one('geo.restriction', string="Check-in Location")
    check_out_geo_restriction_id = fields.Many2one('geo.restriction', string="Check-out Location")

    def _check_geo_restriction(self, vals):

        for attendance in self:

            _logger.info("🚀 ===== GEO CHECK START =====")
            _logger.info("👤 Employee: %s (ID: %s)", attendance.employee_id.name, attendance.employee_id.id)

            geo_locations = attendance.employee_id.geo_restriction_ids

            # -------------------------
            # CHECK-IN
            # -------------------------
            if vals.get('check_in'):

                lat = vals.get('in_latitude') or attendance.in_latitude
                lon = vals.get('in_longitude') or attendance.in_longitude

                _logger.info("📍 RAW Check-in Lat: %s", lat)
                _logger.info("📍 RAW Check-in Lon: %s", lon)

                if lat is None or lon is None:
                    _logger.error("❌ Missing check-in location")
                    raise UserError(_("Location required for check-in."))

                # ✅ Normalize
                lat = round(lat, 5)
                lon = round(lon, 5)

                _logger.info("🎯 Rounded Lat: %s", lat)
                _logger.info("🎯 Rounded Lon: %s", lon)

                matched_geo = False

                for geo in geo_locations:

                    office_lat = round(geo.company_latitude, 5)
                    office_lon = round(geo.company_longitude, 5)

                    _logger.info("🏢 Geo ID: %s", geo.id)
                    _logger.info("🏢 Office Lat: %s", office_lat)
                    _logger.info("🏢 Office Lon: %s", office_lon)

                    distance = geodesic(
                        (office_lat, office_lon),
                        (lat, lon)
                    ).meters

                    allowed_radius = geo.allowed_distance + 100

                    _logger.info("📏 Calculated Distance: %.2f meters", distance)
                    _logger.info("🎯 Allowed Radius (with buffer): %s meters", allowed_radius)

                    if distance <= allowed_radius:
                        _logger.info("✅ MATCH FOUND (Check-in) → Geo ID: %s", geo.id)
                        attendance.geo_restriction_id = geo.id
                        matched_geo = True
                        break
                    else:
                        _logger.warning("⚠️ Not matched with Geo ID: %s", geo.id)

                if not matched_geo:
                    _logger.error("❌ FINAL RESULT: Outside allowed location (Check-in)")
                    raise UserError(_("Outside allowed location (Check-in)."))

            # -------------------------
            # CHECK-OUT
            # -------------------------
            if vals.get('check_out'):

                lat = vals.get('out_latitude') or attendance.out_latitude
                lon = vals.get('out_longitude') or attendance.out_longitude

                _logger.info("📍 RAW Check-out Lat: %s", lat)
                _logger.info("📍 RAW Check-out Lon: %s", lon)

                if lat is None or lon is None:
                    _logger.error("❌ Missing check-out location")
                    raise UserError(_("Location required for check-out."))

                # ✅ Normalize
                lat = round(lat, 5)
                lon = round(lon, 5)

                _logger.info("🎯 Rounded Lat: %s", lat)
                _logger.info("🎯 Rounded Lon: %s", lon)

                matched_geo = False

                for geo in geo_locations:

                    office_lat = round(geo.company_latitude, 5)
                    office_lon = round(geo.company_longitude, 5)

                    _logger.info("🏢 Geo ID: %s", geo.id)
                    _logger.info("🏢 Office Lat: %s", office_lat)
                    _logger.info("🏢 Office Lon: %s", office_lon)

                    distance = geodesic(
                        (office_lat, office_lon),
                        (lat, lon)
                    ).meters

                    allowed_radius = geo.allowed_distance + 100

                    _logger.info("📏 Calculated Distance: %.2f meters", distance)
                    _logger.info("🎯 Allowed Radius (with buffer): %s meters", allowed_radius)

                    if distance <= allowed_radius:
                        _logger.info("✅ MATCH FOUND (Check-out) → Geo ID: %s", geo.id)
                        attendance.check_out_geo_restriction_id = geo.id
                        matched_geo = True
                        break
                    else:
                        _logger.warning("⚠️ Not matched with Geo ID: %s", geo.id)

                if not matched_geo:
                    _logger.error("❌ FINAL RESULT: Outside allowed location (Check-out)")
                    raise UserError(_("You must check-out from an assigned location."))

            _logger.info("🏁 ===== GEO CHECK END =====\n")