from odoo import models, api, _
from odoo.exceptions import UserError
from geopy.distance import geodesic


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    @api.model
    def create(self, vals):

        print("===== ATTENDANCE CREATE START =====")

        attendance = super().create(vals)

        attendance._check_geo_restriction()

        print("===== ATTENDANCE CREATE END =====")

        return attendance

    def _check_geo_restriction(self):
        print("------ GEO RESTRICTION CHECK START ------")

        for attendance in self:
            print("Employee:", attendance.employee_id.name)

            geo_locations = self.env['geo.restriction'].search([
                ('employee_ids', 'in', attendance.employee_id.id)
            ])

            print("Geo Locations Found:", len(geo_locations))
            if not geo_locations:
                print("No geo restriction configured")
                return

            # Check check-in
            if attendance.in_latitude and attendance.in_longitude:
                lat, lon = attendance.in_latitude, attendance.in_longitude
                action_type = "Check-in"
            # Check check-out
            elif attendance.out_latitude and attendance.out_longitude:
                lat, lon = attendance.out_latitude, attendance.out_longitude
                action_type = "Check-out"
            else:
                print("Employee location missing")
                raise UserError(_("Location access required."))

            print(f"{action_type} Latitude:", lat)
            print(f"{action_type} Longitude:", lon)

            for geo in geo_locations:
                print("Company Latitude:", geo.company_latitude)
                print("Company Longitude:", geo.company_longitude)

                distance = geodesic(
                    (geo.company_latitude, geo.company_longitude),
                    (lat, lon)
                ).meters

                print("Distance (Meters):", distance)
                print("Allowed Distance:", geo.allowed_distance)

                if distance <= geo.allowed_distance:
                    print("Employee inside allowed radius")
                    break
            else:
                # If no geo matched
                print("Employee outside allowed radius")
                raise UserError(_("You are outside allowed work location."))

        print("------ GEO RESTRICTION CHECK END ------")