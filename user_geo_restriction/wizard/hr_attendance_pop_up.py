from odoo import models, api, _, fields

class AttendancePopup(models.TransientModel):
    _name = 'attendance.popup'
    _description = 'Attendance Popup'

    message = fields.Char()