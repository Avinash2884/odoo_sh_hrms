from odoo import models, api, _, fields
from odoo.exceptions import UserError, ValidationError
from geopy.distance import geodesic


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
            print("Employee Name:", attendance.employee_id.name)
            print("Employee ID:", attendance.employee_id.id)

            # ✅ Skip if no check-in / check-out (demo safe)
            if not attendance.check_in and not attendance.check_out:
                continue

            # ✅ Skip if no GPS data (demo safe)
            if not attendance.in_latitude and not attendance.out_latitude:
                continue

            geo_locations = attendance.employee_id.geo_restriction_ids

            if not geo_locations:
                print("ERROR: No geo locations configured!")
                raise ValidationError(_("No office locations configured for this employee."))

            # -------------------------
            # CHECK-IN
            # -------------------------
            if vals.get('check_in'):

                lat = attendance.in_latitude
                lon = attendance.in_longitude
                print("\n--- CHECK-IN ---")
                print("Check-in Latitude:", lat)
                print("Check-in Longitude:", lon)

                if not lat or not lon:
                    print("ERROR: Missing check-in location")
                    raise UserError(_("Location required for check-in."))

                matched_geo = False

                for geo in geo_locations:
                    print("\nChecking Geo Location ID:", geo.id)
                    print("Office Latitude:", geo.company_latitude)
                    print("Office Longitude:", geo.company_longitude)
                    print("Allowed Radius (meters):", geo.allowed_distance)
                    distance = geodesic(
                        (geo.company_latitude, geo.company_longitude),
                        (lat, lon)
                    ).meters

                    print("Calculated Distance (meters):", distance)

                    if distance <= geo.allowed_distance:
                        attendance.geo_restriction_id = geo.id
                        matched_geo = True
                        break

                if not matched_geo:
                    print("❌ Outside allowed location (Check-in)")
                    raise UserError(_("Outside allowed location (Check-in)."))

            # -------------------------
            # CHECK-OUT
            # -------------------------
            if vals.get('check_out'):

                lat = attendance.out_latitude
                lon = attendance.out_longitude

                print("\n--- CHECK-OUT ---")
                print("Check-out Latitude:", lat)
                print("Check-out Longitude:", lon)

                if not lat or not lon:
                    print("ERROR: Missing check-out location")
                    raise UserError(_("Location required for check-out."))

                matched_geo = False

                for geo in geo_locations:
                    print("\nChecking Geo Location ID:", geo.id)
                    print("Office Latitude:", geo.company_latitude)
                    print("Office Longitude:", geo.company_longitude)
                    print("Allowed Radius (meters):", geo.allowed_distance)
                    distance = geodesic(
                        (geo.company_latitude, geo.company_longitude),
                        (lat, lon)
                    ).meters

                    print("Calculated Distance (meters):", distance)

                    if distance <= geo.allowed_distance:
                        print("✅ MATCHED (Check-out) with Geo ID:", geo.id)
                        attendance.check_out_geo_restriction_id = geo.id
                        matched_geo = True
                        break

                if not matched_geo:
                    print("❌ Outside allowed location (Check-out)")
                    raise UserError(_("You must check-out from an assigned location."))