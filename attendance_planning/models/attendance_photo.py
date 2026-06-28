# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import timedelta


class AttendancePhoto(models.Model):
    _name = 'attendance.photo'
    _description = 'Attendance Photo'
    _order = 'captured_at desc'

    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Attendance',
        required=True,
        ondelete='cascade',
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        related='attendance_id.employee_id',
        store=True,
    )
    photo = fields.Image(
        string='Photo',
        max_width=600,
        max_height=600,
        required=True,
    )
    punch_type = fields.Selection([
        ('checkin', 'Check-in'),
        ('checkout', 'Check-out'),
    ], string='Type', required=True)

    captured_at = fields.Datetime(
        string='Captured At',
        default=fields.Datetime.now,
        readonly=True,
    )
    deletion_date = fields.Date(
        string='Deletion Date',
        readonly=True,
        help='Photo is auto-deleted 60 days after capture',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'deletion_date' not in vals:
                vals['deletion_date'] = (
                    fields.Date.today() + timedelta(days=60)
                )
        return super().create(vals_list)

    @api.model
    def _auto_delete_old_photos(self):
        """Cron: Delete photo records older than 60 days"""
        today = fields.Date.today()
        expired = self.search([('deletion_date', '<=', today)])
        if expired:
            expired.sudo().unlink()