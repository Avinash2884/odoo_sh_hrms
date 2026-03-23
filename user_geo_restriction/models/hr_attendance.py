# from math import radians, sin, cos, sqrt, atan2
# from odoo import models, api, _
# from odoo.exceptions import UserError
#
#
# class HrAttendance(models.Model):
#     _inherit = 'hr.attendance'
#
#     @api.model
#     def create(self, vals):
#
#         print("===== ATTENDANCE CREATE START =====")
#
#         attendance = super().create(vals)
#
#         attendance._check_geo_restriction()
#
#         print("===== ATTENDANCE CREATE END =====")
#
#         return attendance
#
#     def write(self, vals):
#
#         print("===== ATTENDANCE WRITE START =====")
#
#         res = super().write(vals)
#
#         self._check_geo_restriction()
#
#         print("===== ATTENDANCE WRITE END =====")
#
#         return res
#
#     def _compute_distance(self, lat1, lon1, lat2, lon2):
#
#         print("Calculating distance...")
#
#         R = 6371.0  # Earth radius in KM
#
#         lat1, lon1, lat2, lon2 = map(
#             radians, [lat1, lon1, lat2, lon2]
#         )
#
#         dlon = lon2 - lon1
#         dlat = lat2 - lat1
#
#         a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
#         c = 2 * atan2(sqrt(a), sqrt(1 - a))
#
#         distance = R * c
#
#         print("Distance (KM):", distance)
#
#         return distance
#
#     def _check_geo_restriction(self):
#
#         print("------ GEO RESTRICTION CHECK START ------")
#
#         for attendance in self:
#
#             print("Employee:", attendance.employee_id.name)
#
#             geo_locations = self.env['geo.restriction'].search([
#                 ('employee_ids', 'in', attendance.employee_id.id)
#             ])
#
#             print("Geo Locations Found:", len(geo_locations))
#
#             if not geo_locations:
#                 print("No geo restriction configured")
#                 return
#
#             if not attendance.in_latitude or not attendance.in_longitude:
#                 print("Attendance location missing")
#                 raise UserError(_("Location access required."))
#
#             allowed = False
#
#             for geo in geo_locations:
#
#                 print("Company Latitude:", geo.company_latitude)
#                 print("Company Longitude:", geo.company_longitude)
#
#                 distance_km = self._compute_distance(
#                     geo.company_latitude,
#                     geo.company_longitude,
#                     attendance.in_latitude,
#                     attendance.in_longitude
#                 )
#
#                 distance_meters = distance_km * 1000
#
#                 print("Distance (Meters):", distance_meters)
#                 print("Allowed Distance:", geo.allowed_distance)
#
#                 if distance_meters <= geo.allowed_distance:
#
#                     print("Employee within allowed distance")
#
#                     allowed = True
#                     break
#
#             if not allowed:
#
#                 print("Employee outside allowed locations")
#
#                 raise UserError(
#                     _("You are outside all allowed work locations.")
#                 )
#
#         print("------ GEO RESTRICTION CHECK END ------")


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