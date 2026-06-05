# -*- coding: utf-8 -*-
from odoo import models, fields, api

# ==========================================
# 1. THE ADMIN / CORE EMPLOYEE MODEL
# ==========================================
class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    face_descriptor = fields.Text(string="Face Recognition Data", copy=False, groups="hr.group_hr_user")
    has_registered_face = fields.Boolean(compute='_compute_has_registered_face')
    is_current_user = fields.Boolean(compute='_compute_is_current_user')

    def _compute_has_registered_face(self):
        for emp in self:
            emp.has_registered_face = bool(emp.sudo().face_descriptor)

    def _compute_is_current_user(self):
        for emp in self:
            emp.is_current_user = (emp.user_id.id == self.env.uid)

    def action_open_face_registration(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'attendance_face_register',
            'name': 'Register Face: %s' % self.name,
            'context': {'default_employee_id': self.id},
        }

    def action_delete_face(self):
        for employee in self:
            employee.face_descriptor = False

    @api.model
    def get_my_face_descriptor(self):
        employee = self.sudo().search([('user_id', '=', self.env.uid)], limit=1)
        if employee and employee.face_descriptor:
            return employee.face_descriptor
        return False

    @api.model
    def ai_attendance_manual(self, employee_id):
        employee = self.sudo().browse(employee_id)
        open_attendance = self.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_out', '=', False)
        ], limit=1)

        if open_attendance:
            open_attendance.write({'check_out': fields.Datetime.now()})
        else:
            self.env['hr.attendance'].sudo().create({
                'employee_id': employee.id,
                'check_in': fields.Datetime.now()
            })
        return True

    @api.model
    def sudo_save_face_by_id(self, employee_id, descriptor_string):
        """Allows Admins to save anyone's face, but restricts normal employees to their own face"""
        employee = self.sudo().browse(employee_id)

        if employee.exists():
            # Security Check 1: Is the person clicking the button an HR Admin?
            is_admin = self.env.user.has_group('hr.group_hr_user')

            # Security Check 2: Is the person clicking the button saving their own profile?
            is_own_profile = (employee.user_id.id == self.env.uid)

            if is_admin or is_own_profile:
                employee.face_descriptor = descriptor_string
                employee.sudo().message_post(
                    body=" <b>Face ID Registered:</b> Biometric data was successfully captured and secured.",
                    author_id=self.env.user.partner_id.id,
                    subtype_xmlid="mail.mt_note"
                )
                return True

        return False

# ==========================================
# 2. THE PUBLIC EMPLOYEE MODEL (FOR WFH / MRUDHULA)
# ==========================================
class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    has_registered_face = fields.Boolean(compute='_compute_has_registered_face')
    is_current_user = fields.Boolean(compute='_compute_is_current_user')

    def _compute_has_registered_face(self):
        for emp in self:
            # Sudo peeks at the REAL secure employee record to see if they have a face saved
            real_emp = self.env['hr.employee'].sudo().search([('id', '=', emp.id)], limit=1)
            emp.has_registered_face = bool(real_emp.face_descriptor) if real_emp else False

    def _compute_is_current_user(self):
        for emp in self:
            emp.is_current_user = (emp.user_id.id == self.env.uid)

    def action_open_face_registration(self):
        """Opens the camera directly from the public profile"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'attendance_face_register',
            'name': 'Register My Face',
            'context': {'default_employee_id': self.id},
        }