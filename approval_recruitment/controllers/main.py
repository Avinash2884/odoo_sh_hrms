# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import base64
import logging

_logger = logging.getLogger(__name__)


class JobApplicationController(http.Controller):

    @http.route('/job/apply/save', type='http', auth='public', methods=['POST'], website=True, csrf=False)
    def submit_job_application(self, **kwargs):
        _logger.info("=== JOB APPLICATION SUBMISSION STARTED ===")

        def safe_int(value):
            try: return int(value) if value else False
            except ValueError: return False

        def safe_float(value):
            try: return float(value) if value else 0.0
            except ValueError: return 0.0

        try:
            # 1. GENERATE NAME
            first = kwargs.get('first_name', '').strip()
            last = kwargs.get('last_name', '').strip()
            full_name = f"{first} {last}".strip() or "New Applicant"

            vals = {
                # --- CORE ODOO FIELDS (Now using Defaults) ---
                'partner_name': full_name,
                'email_from': kwargs.get('email_from'),
                'partner_phone': kwargs.get('partner_phone'),

                # IDs
                'job_id': safe_int(kwargs.get('job_id')),
                'department_id': safe_int(kwargs.get('department_id')),

                # CUSTOM PERSONAL INFO
                'registration_no': kwargs.get('registration_no'),
                'title': kwargs.get('title'),
                'first_name': kwargs.get('first_name'),
                'middle_name': kwargs.get('middle_name'),
                'last_name': kwargs.get('last_name'),
                'father_name': kwargs.get('father_name'),
                'mother_name': kwargs.get('mother_name'),
                'date_of_birth': kwargs.get('date_of_birth') or False,
                'gender': kwargs.get('gender'),
                'category': kwargs.get('category'),

                # CONTACT
                'phone_with_std': kwargs.get('phone_with_std'),
                'mailing_address': kwargs.get('mailing_address'),
                'pincode': kwargs.get('pincode'),

                # OTHER
                'discipline_applied': kwargs.get('discipline_applied'),
                'declaration': True if kwargs.get('declaration') == 'on' else False,
                'linkedin_profile': kwargs.get('linkedin_profile'),
            }

            # 2. HANDLE PHOTO
            file = request.httprequest.files.get('photograph')
            if file and file.filename:
                vals['photograph'] = base64.b64encode(file.read())
                vals['photograph_filename'] = file.filename

            # 3. HANDLE RESUME
            resume = request.httprequest.files.get('Resume')
            if resume and resume.filename:
                vals['resume_file'] = base64.b64encode(resume.read())
                vals['resume_filename'] = resume.filename

            # 4. CREATE APPLICANT
            applicant = request.env['hr.applicant'].sudo().create(vals)
            _logger.info("Applicant Created: ID %s", applicant.id)

            # 5. HANDLE EDUCATION
            exams = request.httprequest.form.getlist('edu_exam_name[]')
            dates = request.httprequest.form.getlist('edu_passing_date[]')
            universities = request.httprequest.form.getlist('edu_university[]')
            marks = request.httprequest.form.getlist('edu_marks_percentage[]')
            subjects = request.httprequest.form.getlist('edu_main_subject[]')

            for i in range(len(exams)):
                if exams[i].strip():
                    request.env['hr.applicant.education'].sudo().create({
                        'applicant_id': applicant.id,
                        'exam_name': exams[i],
                        'passing_date': dates[i] if i < len(dates) else '',
                        'university': universities[i] if i < len(universities) else '',
                        'marks_percentage': safe_float(marks[i]) if i < len(marks) else 0.0,
                        'main_subject': subjects[i] if i < len(subjects) else '',
                    })

            # 6. HANDLE EXPERIENCE
            employers = request.httprequest.form.getlist('exp_employer_name[]')
            from_dates = request.httprequest.form.getlist('exp_from_date[]')
            to_dates = request.httprequest.form.getlist('exp_to_date[]')
            designations = request.httprequest.form.getlist('exp_designation[]')
            duties = request.httprequest.form.getlist('exp_duties[]')
            salaries = request.httprequest.form.getlist('exp_gross_salary[]')
            scales = request.httprequest.form.getlist('exp_pay_scale[]')

            for i in range(len(employers)):
                if employers[i].strip():
                    request.env['hr.applicant.experience'].sudo().create({
                        'applicant_id': applicant.id,
                        'employer_name': employers[i],
                        'from_date': from_dates[i] if i < len(from_dates) else '',
                        'to_date': to_dates[i] if i < len(to_dates) else '',
                        'designation': designations[i] if i < len(designations) else '',
                        'duties': duties[i] if i < len(duties) else '',
                        'gross_salary': safe_float(salaries[i]) if i < len(salaries) else 0.0,
                        'pay_scale': scales[i] if i < len(scales) else '',
                    })

            return request.redirect('/contactus-thank-you')

        except Exception as e:
            _logger.exception("CRITICAL ERROR: %s", e)
            return request.redirect('/jobs?error=internal_error')


class PreOnboardingController(http.Controller):

    @http.route('/job/pre_onboarding', type='http', auth='user', website=True)
    def pre_onboarding_form(self, **kwargs):
        user = request.env.user
        # Find the applicant linked to this portal user
        applicant = request.env['hr.applicant'].sudo().search([
            ('partner_id', '=', user.partner_id.id)
        ], limit=1)

        if not applicant:
            return request.redirect('/my/home')

        # The 'applicant' object contains all the details they submitted earlier
        return request.render('website_job_custom.pre_onboarding_template', {
            'applicant': applicant
        })

    @http.route('/job/onboarding/save', type='http', auth='user', methods=['POST'], website=True, csrf=False)
    def save_onboarding_docs(self, **kwargs):
        user = request.env.user
        applicant = request.env['hr.applicant'].sudo().search([
            ('partner_id', '=', user.partner_id.id)
        ], limit=1)

        if not applicant:
            return request.redirect('/my/home')

        # 1. HANDLE TEXT FIELDS (Identity & Bank)
        text_fields = [
            'aadhaar_no', 'pan_no', 'bank_name',
            'bank_acc_no', 'bank_ifsc', 'bank_branch'
        ]

        vals = {}
        for field in text_fields:
            if kwargs.get(field):
                vals[field] = kwargs.get(field)

        # 2. HANDLE FILE FIELDS
        file_fields = [
            'onboarding_photo', 'aadhaar_card', 'pan_card', 'bank_doc',
            'marksheet_10', 'marksheet_12', 'diploma_cert', 'ug_degree', 'pg_degree',
            'payslips', 'salary_revision_letter', 'relieving_letter', 'exp_appointment_letter'
        ]

        for field in file_fields:
            file = request.httprequest.files.get(field)
            if file and file.filename:
                vals[field] = base64.b64encode(file.read())

        if vals:
            applicant.sudo().write(vals)

        return request.redirect('/contactus-thank-you')

