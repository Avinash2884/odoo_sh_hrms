# -*- coding: utf-8 -*-
from odoo import models, fields, api

# ==========================================
# 1. THE ADMIN / CORE EMPLOYEE MODEL
# ==========================================
class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # contract_date_start = fields.Date(related='contract_id.date_start', groups="base.group_user")
    # contract_date_end = fields.Date(related='contract_id.date_end', groups="base.group_user")

    shift_type = fields.Selection([
        ('regular', 'Regular Shift (Fixed Weekends)'),
        ('rotational', 'Rotational Shift (Dynamic Week-Offs)')
    ], string="Shift Type", default='regular', tracking=True)

    bypass_geo_restriction = fields.Boolean(
        string="Allow Check-in Anywhere",
        default=False,
        tracking=True,
        help="If enabled, this employee can Check In / Check Out from any "
             "location — the office geo-fence restriction will be skipped "
             "for them. Use this for field staff, sales reps, or remote "
             "employees who don't work from a fixed office location."
    )

    face_descriptor = fields.Text(string="Face Recognition Data", copy=False, groups="hr.group_hr_user")
    has_registered_face = fields.Boolean(compute='_compute_has_registered_face')
    is_current_user = fields.Boolean(compute='_compute_is_current_user')

    pending_attendance_photo = fields.Text(string="Pending Photo")
    pending_geo_zone_id = fields.Integer(string="Pending Geo Zone")
    pending_photo_timestamp = fields.Datetime(string="Pending Photo Time")

    last_photo_attach_status = fields.Boolean(string="Last Photo Attach Succeeded", default=True)
    last_photo_attach_note = fields.Char(string="Last Photo Attach Note")

    # version_ids = fields.One2many(groups="base.group_user")
    # The field is on its own line
    version_id = fields.Many2one('hr.version', required=True, ondelete='cascade', groups="base.group_user")

    # The decorator and function are on their own lines below it
    @api.model
    def stage_attendance_data(self, photo_base64, geo_zone_id=False):
        """Step 1: Stages the photo and exact time right before the punch."""
        employee = self.env.user.employee_id
        if employee:
            employee.sudo().write({
                'pending_attendance_photo': photo_base64,
                'pending_geo_zone_id': geo_zone_id or False,
                'pending_photo_timestamp': fields.Datetime.now(),
            })
        return True

    def _attendance_action_change(self, geo_information=None):
        """Step 2: Native punch + Atomic photo attach + UI status update."""
        res = super(HrEmployee, self)._attendance_action_change(geo_information=geo_information)

        for emp in self:
            if emp.pending_attendance_photo and emp.pending_photo_timestamp:
                time_diff = fields.Datetime.now() - emp.pending_photo_timestamp

                if time_diff.total_seconds() < 60:
                    att = emp.sudo().last_attendance_id

                    if att:
                        punch_type = 'checkin' if emp.attendance_state == 'checked_in' else 'checkout'

                        self.env['attendance.photo'].sudo().create({
                            'attendance_id': att.id,
                            'photo': emp.pending_attendance_photo,
                            'punch_type': punch_type,
                        })

                        if emp.pending_geo_zone_id:
                            if punch_type == 'checkin':
                                att.sudo().write({'geo_restriction_id': emp.pending_geo_zone_id})
                            elif punch_type == 'checkout':
                                att.sudo().write({'check_out_geo_restriction_id': emp.pending_geo_zone_id})

                        # Success: Overwrite status
                        emp.sudo().write({
                            'last_photo_attach_status': True,
                            'last_photo_attach_note': False,
                        })
                    else:
                        # Failed: No record
                        emp.sudo().write({
                            'last_photo_attach_status': False,
                            'last_photo_attach_note': 'No attendance record found to attach photo to.',
                        })
                else:
                    # Failed: Expired
                    emp.sudo().write({
                        'last_photo_attach_status': False,
                        'last_photo_attach_note': f'Staged photo expired ({int(time_diff.total_seconds())}s old) before attach.',
                    })

                # Always wipe staging fields clean
                emp.sudo().write({
                    'pending_attendance_photo': False,
                    'pending_geo_zone_id': False,
                    'pending_photo_timestamp': False,
                })

        return res

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
# 2. THE PUBLIC EMPLOYEE MODEL
# ==========================================
class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    version_id = fields.Many2one(
        'hr.version',
        string="Version ID Bypass",
        readonly=True,
        store=False,
        compute='_compute_dummy_version'
    )

    pending_attendance_photo = fields.Text(string="Pending Photo", compute='_compute_public_attendance_fields')
    pending_attendance_photo = fields.Text(string="Pending Photo", compute='_compute_public_attendance_fields')
    pending_geo_zone_id = fields.Integer(string="Pending Geo Zone", compute='_compute_public_attendance_fields')
    pending_photo_timestamp = fields.Datetime(string="Pending Photo Time", compute='_compute_public_attendance_fields')

    last_photo_attach_status = fields.Boolean(string="Last Photo Attach Succeeded",
                                              compute='_compute_public_attendance_fields')
    last_photo_attach_note = fields.Char(string="Last Photo Attach Note", compute='_compute_public_attendance_fields')

    def _compute_public_attendance_fields(self):
        """Safely fetches the actual data from the core employee model"""
        for emp in self:
            real_emp = self.env['hr.employee'].sudo().search([('id', '=', emp.id)], limit=1)
            if real_emp:
                emp.pending_attendance_photo = real_emp.pending_attendance_photo
                emp.pending_geo_zone_id = real_emp.pending_geo_zone_id
                emp.pending_photo_timestamp = real_emp.pending_photo_timestamp
                emp.last_photo_attach_status = real_emp.last_photo_attach_status
                emp.last_photo_attach_note = real_emp.last_photo_attach_note
            else:
                emp.pending_attendance_photo = False
                emp.pending_geo_zone_id = False
                emp.pending_photo_timestamp = False
                emp.last_photo_attach_status = False
                emp.last_photo_attach_note = False


    def _compute_dummy_version(self):
        for rec in self:
            rec.version_ids = False

    has_registered_face = fields.Boolean(compute='_compute_has_registered_face')
    is_current_user = fields.Boolean(compute='_compute_is_current_user')

    shift_type = fields.Selection([
        ('regular', 'Regular Shift (Fixed Weekends)'),
        ('rotational', 'Rotational Shift (Dynamic Week-Offs)')
    ], string="Shift Type", default='regular')

    bypass_geo_restriction = fields.Boolean(compute='_compute_bypass_geo_restriction')

    def _compute_bypass_geo_restriction(self):
        for emp in self:
            real_emp = self.env['hr.employee'].sudo().search([('id', '=', emp.id)], limit=1)
            emp.bypass_geo_restriction = bool(real_emp.bypass_geo_restriction) if real_emp else False


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


