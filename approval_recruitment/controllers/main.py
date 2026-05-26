# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import base64
import logging

_logger = logging.getLogger(__name__)


class JobApplicationController(http.Controller):

    @http.route('/job/apply/save', type='http', auth='public', methods=['POST'], website=True, csrf=False)
    def submit_job_application(self, **kwargs):
        print("\n\n" + "=" * 60)
        print(" === JOB APPLICATION CONTROLLER TRIGGERED === ")
        print("=" * 60)

        def safe_int(value):
            try:
                return int(value) if value else False
            except ValueError:
                return False

        def safe_float(value):
            try:
                return float(value) if value else 0.0
            except ValueError:
                return 0.0

        try:
            first = (kwargs.get('first_name') or '').strip()
            last = (kwargs.get('last_name') or '').strip()
            full_name = '{} {}'.format(first, last).strip() or 'New Applicant'

            # --- THE MAGIC FIX: Combine Address Fields ---
            # Your model has 'mailing_address', not street/city/state.
            street = (kwargs.get('applicant_street') or '').strip()
            city = (kwargs.get('applicant_city') or '').strip()
            state = (kwargs.get('applicant_state') or '').strip()

            address_parts = [p for p in [street, city, state] if p]
            full_mailing_address = ", ".join(address_parts)
            # ---------------------------------------------

            vals = {
                'partner_name': full_name,
                'email_from': kwargs.get('email_from'),
                'partner_phone': kwargs.get('partner_phone'),

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
                'phone_with_std': kwargs.get('phone_with_std'),
                'pincode': kwargs.get('pincode'),

                # Assign the combined address here:
                'mailing_address': full_mailing_address,
                'applicant_street': kwargs.get('applicant_street'),
                'applicant_city': kwargs.get('applicant_city'),
                'applicant_state': kwargs.get('applicant_state'),

                'discipline_applied': kwargs.get('discipline_applied'),
                'declaration': True if kwargs.get('declaration') == 'on' else False,
                'linkedin_profile': kwargs.get('linkedin_profile'),
            }

            job_id = safe_int(kwargs.get('job_id'))
            dept_id = safe_int(kwargs.get('department_id'))
            if job_id: vals['job_id'] = job_id
            if dept_id: vals['department_id'] = dept_id

            print("\n 1. DICTIONARY COMPILED. ATTEMPTING TO SAVE THESE KEYS:")
            print(list(vals.keys()))

            photo = request.httprequest.files.get('photograph')
            if photo and photo.filename:
                vals['photograph'] = base64.b64encode(photo.read())
                vals['photograph_filename'] = photo.filename

            resume = request.httprequest.files.get('Resume')
            if resume and resume.filename:
                vals['resume_file'] = base64.b64encode(resume.read())
                vals['resume_filename'] = resume.filename

            print("\n⏳ 2. EXECUTING ORM CREATE()...")

            applicant = request.env['hr.applicant'].sudo().create(vals)

            print(f"✅ 3. SUCCESS! APPLICANT CREATED WITH ID: {applicant.id}")

            if vals.get('resume_file'):
                print("📎 4. Attaching Resume...")
                request.env['ir.attachment'].sudo().create({
                    'name': vals.get('resume_filename') or 'Resume',
                    'type': 'binary',
                    'datas': vals['resume_file'],
                    'res_model': 'hr.applicant',
                    'res_id': applicant.id,
                })

            print(" 5. Processing Education & Experience...")
            exams = request.httprequest.form.getlist('edu_exam_name[]')
            dates = request.httprequest.form.getlist('edu_passing_date[]')
            universities = request.httprequest.form.getlist('edu_university[]')
            marks = request.httprequest.form.getlist('edu_marks_percentage[]')
            subjects = request.httprequest.form.getlist('edu_main_subject[]')

            for i, exam in enumerate(exams):
                if exam.strip():
                    request.env['hr.applicant.education'].sudo().create({
                        'applicant_id': applicant.id,
                        'exam_name': exam.strip(),
                        'passing_date': dates[i] if i < len(dates) else '',
                        'university': universities[i] if i < len(universities) else '',
                        'marks_percentage': safe_float(marks[i]) if i < len(marks) else 0.0,
                        'main_subject': subjects[i] if i < len(subjects) else '',
                    })

            employers = request.httprequest.form.getlist('exp_employer_name[]')
            from_dates = request.httprequest.form.getlist('exp_from_date[]')
            to_dates = request.httprequest.form.getlist('exp_to_date[]')
            designations = request.httprequest.form.getlist('exp_designation[]')
            duties_list = request.httprequest.form.getlist('exp_duties[]')
            salaries = request.httprequest.form.getlist('exp_gross_salary[]')
            scales = request.httprequest.form.getlist('exp_pay_scale[]')

            for i, employer in enumerate(employers):
                if employer.strip():
                    request.env['hr.applicant.experience'].sudo().create({
                        'applicant_id': applicant.id,
                        'employer_name': employer.strip(),
                        'from_date': from_dates[i] if i < len(from_dates) else '',
                        'to_date': to_dates[i] if i < len(to_dates) else '',
                        'designation': designations[i] if i < len(designations) else '',
                        'duties': duties_list[i] if i < len(duties_list) else '',
                        'gross_salary': safe_float(salaries[i]) if i < len(salaries) else 0.0,
                        'pay_scale': scales[i] if i < len(scales) else '',
                    })

            print("🎉 6. ALL SAVED. REDIRECTING TO THANK YOU PAGE. ===\n\n")
            return "SUCCESS"

        except Exception as e:
            print("\n" + "❌" * 20)
            print("FATAL DATABASE CRASH DETECTED!")
            print("Exact Error:", str(e))
            print("❌" * 20 + "\n")

            error_msg = f"""
            <div style="padding: 40px; font-family: sans-serif;">
                <h1 style="color: #d9534f;">Odoo Save Failed!</h1>
                <p style="font-size: 18px;">The database rejected the save because of this exact error:</p>
                <div style="background: #f8d7da; color: #721c24; padding: 20px; border: 1px solid #f5c6cb; border-radius: 5px; font-size: 20px; font-weight: bold;">
                    {str(e)}
                </div>
            </div>
            """
            return error_msg


class PreOnboardingController(http.Controller):

    # =======================================================
    # 1. NEW: Route to load the Pre-Offer page
    # =======================================================
    @http.route('/job/pre_offer/<string:token>', type='http', auth='public', website=True)
    def pre_offer_form(self, token, **kwargs):
        if not token:
            return request.redirect('/')

        applicant = request.env['hr.applicant'].sudo().search([
            ('access_token', '=', token)
        ], limit=1)

        if not applicant:
            _logger.warning("Invalid pre-offer token: %s", token)
            return request.redirect('/')

        return request.render('approval_recruitment.pre_offer_template', {
            'applicant': applicant,
            'token': token,
        })

    # =======================================================
    # 2. EXISTING: Route to load the Pre-Onboarding page
    # =======================================================
    @http.route('/job/pre_onboarding/<string:token>', type='http', auth='public', website=True)
    def pre_onboarding_form(self, token, **kwargs):
        if not token:
            return request.redirect('/')

        applicant = request.env['hr.applicant'].sudo().search([
            ('access_token', '=', token)
        ], limit=1)

        if not applicant:
            _logger.warning("Invalid pre-onboarding token: %s", token)
            return request.redirect('/')

        return request.render('approval_recruitment.pre_onboarding_template', {
            'applicant': applicant,
            'token': token,
        })

    # =======================================================
    # 3. UPGRADED: Universal Save (Saves data from BOTH forms)
    # =======================================================
    @http.route('/job/onboarding/save', type='http', auth='public', methods=['POST'], website=True, csrf=False)
    def save_onboarding_docs(self, **kwargs):
        _logger.info("=== UNIVERSAL DOCUMENT SAVE STARTED ===")

        token = kwargs.get('access_token')
        if not token:
            return request.redirect('/')

        applicant = request.env['hr.applicant'].sudo().search([
            ('access_token', '=', token)
        ], limit=1)

        if not applicant:
            _logger.error("No applicant for token: %s", token)
            return request.redirect('/')

        vals = {}
        try:
            # Added the new Pre-Offer dropdowns to this list
            text_fields = [
                'aadhaar_no', 'pan_no', 'bank_name', 'bank_acc_no',
                'bank_ifsc', 'bank_branch', 'joining_category',
                'highest_edu_level', 'highest_edu_detail', 'income_proof_type'
            ]

            for field in text_fields:
                if kwargs.get(field):
                    vals[field] = kwargs[field]

            file_fields = [
                'onboarding_photo', 'aadhaar_card', 'pan_card', 'bank_doc',
                'marksheet_10', 'marksheet_12', 'diploma_cert', 'ug_degree', 'pg_degree',
                'payslips', 'salary_revision_letter', 'relieving_letter', 'exp_appointment_letter',
                'income_bank_statement'
            ]

            for field in file_fields:
                for f in request.httprequest.files.getlist(field):
                    if f and f.filename:
                        data = base64.b64encode(f.read())
                        if field not in vals:
                            vals[field] = data
                            if field == 'onboarding_photo':
                                vals['photograph'] = data

                        # Save attachments for HR
                        request.env['ir.attachment'].sudo().create({
                            'name': '{} - {}'.format(field.replace('_', ' ').title(), f.filename),
                            'type': 'binary',
                            'datas': data,
                            'res_model': 'hr.applicant',
                            'res_id': applicant.id,
                            'public': False,
                        })

            if vals:
                applicant.sudo().write(vals)
                _logger.info("Documents saved for applicant id=%s", applicant.id)

            return request.redirect('/contactus-thank-you')

        except Exception as e:
            _logger.exception("DOCUMENT SAVE ERROR: %s", e)
            return request.redirect('/contactus-thank-you')
