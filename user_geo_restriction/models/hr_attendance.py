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

    def _check_geo_restriction(self, vals):

        for attendance in self:
            _logger.info("🚀 GEO CHECK STARTED for Attendance ID: %s", attendance.id)
            _logger.info("Employee Name: %s", attendance.employee_id.name)
            _logger.info("Employee ID: %s", attendance.employee_id.id)

            # ✅ Skip if no check-in / check-out (demo safe)
            if not attendance.check_in and not attendance.check_out:
                continue

            # ✅ Skip if no GPS data (demo safe)
            if not attendance.in_latitude and not attendance.out_latitude:
                continue

            geo_locations = attendance.employee_id.geo_restriction_ids

            # if not geo_locations:
            #     print("ERROR: No geo locations configured!")
            #     raise ValidationError(_("No office locations configured for this employee."))

            # -------------------------
            # CHECK-IN
            # -------------------------
            if vals.get('check_in'):

                lat = vals.get('in_latitude') or attendance.in_latitude
                lon = vals.get('in_longitude') or attendance.in_longitude
                _logger.info("---- CHECK-IN START ----")
                _logger.info("Check-in Latitude: %s", lat)
                _logger.info("Check-in Longitude: %s", lon)

                if lat is None or lon is None:
                    _logger.error("Missing check-in location")
                    raise UserError(_("Location required for check-in."))

                matched_geo = False

                for geo in geo_locations:
                    _logger.info("Checking Geo ID: %s", geo.id)
                    _logger.info("Office Lat: %s, Lon: %s", geo.company_latitude, geo.company_longitude)
                    _logger.info("Allowed Radius: %s meters", geo.allowed_distance)
                    distance = geodesic(
                        (geo.company_latitude, geo.company_longitude),
                        (lat, lon)
                    ).meters

                    _logger.info("Calculated Distance: %s meters", distance)

                    allowed_radius = geo.allowed_distance + 50

                    if distance <= geo.allowed_distance:
                        _logger.info("✅ MATCHED CHECK-IN with Geo ID: %s", geo.id)
                        attendance.geo_restriction_id = geo.id
                        matched_geo = True
                        break

                if not matched_geo:
                    _logger.error("❌ Outside allowed location (Check-in)")
                    raise UserError(_("Outside allowed location (Check-in)."))

            # -------------------------
            # CHECK-OUT
            # -------------------------
            if vals.get('check_out'):

                lat = vals.get('out_latitude') or attendance.out_latitude
                lon = vals.get('out_longitude') or attendance.out_longitude

                _logger.info("---- CHECK-OUT START ----")
                _logger.info("Check-out Latitude: %s", lat)
                _logger.info("Check-out Longitude: %s", lon)

                if lat is None or lon is None:
                    _logger.error("Missing check-out location")
                    raise UserError(_("Location required for check-out."))

                matched_geo = False

                for geo in geo_locations:
                    _logger.info("Checking Geo ID: %s", geo.id)
                    _logger.info("Office Lat: %s, Lon: %s", geo.company_latitude, geo.company_longitude)
                    _logger.info("Allowed Radius: %s meters", geo.allowed_distance)
                    distance = geodesic(
                        (geo.company_latitude, geo.company_longitude),
                        (lat, lon)
                    ).meters

                    _logger.info("Calculated Distance: %s meters", distance)

                    allowed_radius = geo.allowed_distance + 50

                    if distance <= geo.allowed_distance:
                        _logger.info("✅ MATCHED CHECK-OUT with Geo ID: %s", geo.id)
                        attendance.check_out_geo_restriction_id = geo.id
                        matched_geo = True
                        break

                if not matched_geo:
                    _logger.error("❌ Outside allowed location (Check-out)")
                    raise UserError(_("You must check-out from an assigned location."))