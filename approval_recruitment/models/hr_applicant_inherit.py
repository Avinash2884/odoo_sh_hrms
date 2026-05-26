from datetime import date, timedelta
import uuid

from markupsafe import Markup

from odoo.exceptions import ValidationError, UserError
import logging
_logger = logging.getLogger(__name__)

from odoo import models, fields, api, _

class HrApplicantInherit(models.Model):
    _inherit = 'hr.applicant'
    _description = 'HR Applicant'

    mark = fields.Float(string="Overall Rating", compute="_compute_mark", store=True)
    evaluation_ids = fields.One2many("hr.applicant.evaluation", "applicant_id", string="Evaluations")
    is_suitable = fields.Selection([("yes", "Yes"), ("no", "No")], string="Suitability")
    application_status = fields.Selection(
        selection_add=[('hold', 'Hold')]
    )
    ls_date_of_joining = fields.Date(string="Date of Joining", copy=False, tracking=True)
    show_evaluation_page = fields.Boolean(
        compute='_compute_show_evaluation_page'
    )
    show_doj = fields.Boolean(
        compute="_compute_show_doj",
        store=False
    )
    is_hold = fields.Boolean(default=False)

    def _compute_show_evaluation_page(self):
        stage_1 = self.env.ref('hr_recruitment.stage_job0', raise_if_not_found=False)
        stage_2 = self.env.ref('hr_recruitment.stage_job1', raise_if_not_found=False)

        for rec in self:
            rec.show_evaluation_page = rec.stage_id in (stage_1, stage_2)

    @api.depends('stage_id')
    def _compute_show_doj(self):
        stage4 = self.env.ref('hr_recruitment.stage_job4', raise_if_not_found=False)
        stage5 = self.env.ref('hr_recruitment.stage_job5', raise_if_not_found=False)
        stage8 = self.env.ref('approval_recruitment.stage_job8', raise_if_not_found=False)

        allowed = [
            s.id for s in (stage4, stage5, stage8) if s
        ]

        for rec in self:
            rec.show_doj = rec.stage_id.id in allowed

    @api.model
    def _cron_move_not_shown_applicants(self):
        print("CRON STARTED: Move Not Joined Applicants")

        today = fields.Date.today()
        ten_days_ago = today - timedelta(days=10)
        print("Today Date:", today)
        print("Threshold Date (10 days ago):", ten_days_ago)

        # Get the "No Shown" stage
        not_shown_stage = self.env.ref(
            'approval_recruitment.stage_job8', raise_if_not_found=False
        )
        if not not_shown_stage:
            print("No Shown stage NOT FOUND")
            return

        # Search applicants that have a joining date, haven't joined, and not already in "No Shown"
        applicants = self.search([
            ('ls_date_of_joining', '!=', False),
            ('employee_id', '=', False),
        ])

        print("Total Applicants with joining date but not joined:", len(applicants))

        moved_count = 0
        for applicant in applicants:
            # Convert to date if it's datetime
            joining_date = applicant.ls_date_of_joining
            if isinstance(joining_date, str):
                joining_date = fields.Date.from_string(joining_date)

            if joining_date <= ten_days_ago:
                if applicant.stage_id != not_shown_stage:
                    print(f"➡ Moving Applicant {applicant.partner_name} ({joining_date}) to No Shown")
                    applicant.with_context(skip_stage_update=True).write({'stage_id': not_shown_stage.id})
                    moved_count += 1
                else:
                    print(f"ℹ Applicant {applicant.partner_name} already in No Shown stage")
            else:
                print(f"ℹ Applicant {applicant.partner_name} joining date {joining_date} not yet 10 days old")

        print(f"✅ CRON FINISHED. Total Moved: {moved_count}")

    @api.onchange('job_id')
    def _onchange_job_id_stage_domain(self):
        if self.job_id:
            return {
                'domain': {
                    'stage_id': [
                        ('job_ids', 'in', self.job_id.id)
                    ]
                }
            }
        else:
            return {
                'domain': {
                    'stage_id': [('id', '=', False)]
                }
            }

    @api.depends("evaluation_ids.education", "evaluation_ids.professional", "evaluation_ids.personality",
                 "evaluation_ids.communication", "evaluation_ids.knowledge", "evaluation_ids.experience")
    def _compute_mark(self):
        for rec in self:
            if rec.evaluation_ids:
                total = 0
                for ev in rec.evaluation_ids:
                    total += (ev.education + ev.professional + ev.personality +
                              ev.communication + ev.knowledge + ev.experience)
                rec.mark = total
            else:
                rec.mark = 0.0

    def write(self, vals):
        old_stage_map = {rec.id: rec.stage_id.id for rec in self}
        res = super().write(vals)
        stage_pre_offer = self.env.ref(
            'approval_recruitment.stage_job9',
            raise_if_not_found=False
        )
        template = self.env.ref(
            'approval_recruitment.mail_template_pre_offer_documents',
            raise_if_not_found=False
        )
        for rec in self:
            old_stage = old_stage_map.get(rec.id)
            if (
                    stage_pre_offer
                    and template
                    and rec.stage_id.id == stage_pre_offer.id
                    and old_stage != stage_pre_offer.id
            ):
                template.send_mail(rec.id, force_send=True)

        for rec in self:
            if rec.job_id:

                job_interviewers = set(rec.job_id.hr_interviewer_ids.ids)
                applicant_interviewers = set(rec.interviewer_ids.ids)

                # ADD new interviewers
                to_add = job_interviewers - applicant_interviewers

                # ➖ REMOVE deleted interviewers
                to_remove = applicant_interviewers - job_interviewers

                # REMOVE INTERVIEWERS
                if to_remove:
                    print("Removing interviewers from applicant:", to_remove)

                    rec.interviewer_ids = [(3, user_id) for user_id in to_remove]

                    # delete related evaluations too
                    self.env['hr.applicant.evaluation'].search([
                        ('applicant_id', '=', rec.id),
                        ('interviewer_id', 'in', list(to_remove))
                    ]).unlink()

                # ADD INTERVIEWERS

                if to_add:
                    print("Adding new interviewers:", to_add)

                    rec.interviewer_ids = [(4, user_id) for user_id in to_add]

                    for user_id in to_add:
                        self.env['hr.applicant.evaluation'].create({
                            'applicant_id': rec.id,
                            'interviewer_id': user_id,
                        })

        self._reorder_contract_proposal_stage()

        return res

    def _reorder_contract_proposal_stage(self):
        """Reorder applicants in Contract Proposal stage by highest mark first without recursion"""
        contract_stage = self.env.ref("hr_recruitment.stage_job4", raise_if_not_found=False)
        if not contract_stage:
            return

        # Use sudo() and update without triggering write() hooks
        applicants = self.env['hr.applicant'].sudo().search(
            [('stage_id', '=', contract_stage.id)], order="mark desc"
        )
        seq = 1
        for applicant in applicants:
            # direct SQL write to avoid triggering write() hooks
            self.env.cr.execute(
                "UPDATE hr_applicant SET sequence=%s WHERE id=%s",
                (seq, applicant.id)
            )
            seq += 1

    # ===== AUTO REGISTRATION NUMBER =====
    registration_no = fields.Char(
        string="Registration No",
        readonly=True,
        copy=False,
        default='New'
    )

    # ===== PERSONAL INFORMATION =====
    title = fields.Selection([
        ('mr', 'Mr.'),
        ('ms', 'Ms.'),
        ('mrs', 'Mrs.'),
        ('dr', 'Dr.')
    ], string="Title")

    first_name = fields.Char(string="First Name")
    last_name = fields.Char(string="Last Name")
    middle_name = fields.Char(string="Middle Name")
    father_name = fields.Char(string="Father's Name")
    mother_name = fields.Char(string="Mother's Name")
    date_of_birth = fields.Date(string="Date of Birth")

    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string="Gender")

    category = fields.Selection([
        ('general', 'General'),
        ('obc', 'OBC'),
        ('sc', 'SC'),
        ('st', 'ST')
    ], string="Category")

    # ===== CONTACT INFORMATION =====
    phone_with_std = fields.Char(string="Phone with STD Code")
    # mobile_no = fields.Char(string="Mobile Number")
    mailing_address = fields.Text(string="Mailing Address")
    permanent_address = fields.Text(string="Permanent Address")
    pincode = fields.Char(string="Pin Code")
    # email_id = fields.Char(string="Email ID")
    resume_file = fields.Binary(string="Resume")
    resume_filename = fields.Char(string="Resume Filename")

    applicant_street = fields.Char(string="Street")
    applicant_city = fields.Char(string="City")
    applicant_state = fields.Char(string="State")

    # ===== ADDITIONAL =====
    discipline_applied = fields.Char(string="Discipline Applied")
    declaration = fields.Boolean(string="Declaration Accepted")
    photograph = fields.Binary(string="Photograph")
    photograph_filename = fields.Char(string="Photograph Filename")

    # ===== ONE2MANY RELATIONS =====
    educational_qualification_ids = fields.One2many(
        'hr.applicant.education',
        'applicant_id',
        string='Educational Qualifications'
    )
    experience_ids = fields.One2many(
        'hr.applicant.experience',
        'applicant_id',
        string='Work Experience'
    )

    # ===== AUTO GENERATE REGISTRATION NUMBER =====
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:

            # EXISTING LOGIC (registration number)
            if not vals.get('registration_no') or vals.get('registration_no') == 'New':
                vals['registration_no'] = self.env['ir.sequence'].next_by_code(
                    'hr.applicant.registration'
                ) or 'New'

            # COPY INTERVIEWERS FROM JOB
            if vals.get('job_id'):
                job = self.env['hr.job'].browse(vals['job_id'])

                if job.hr_interviewer_ids:
                    vals['interviewer_ids'] = [(6, 0, job.hr_interviewer_ids.ids)]

        applicants = super().create(vals_list)

        # CREATE EVALUATION LINES
        for applicant in applicants:
            if applicant.interviewer_ids:
                applicant.evaluation_ids = [(5, 0, 0)]

                applicant.evaluation_ids = [
                    (0, 0, {
                        'interviewer_id': user.id
                    })
                    for user in applicant.interviewer_ids
                ]

        return applicants

    access_token = fields.Char(
        string='Security Token',
        copy=False,
        readonly=True,
        default=lambda self: str(uuid.uuid4())  # Automatically generates a secure random string
    )

    @api.constrains('access_token')
    def _check_access_token_unique(self):
        for record in self:
            if self.search([('access_token', '=', record.access_token), ('id', '!=', record.id)]):
                raise ValidationError(
                    'The security token must be completely unique for each applicant!'
                )

    def create_employee_from_applicant(self):

        # 1. Let Odoo create the basic employee record
        res = super(HrApplicantInherit, self).create_employee_from_applicant()
        employee_id = res.get('res_id')

        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)

            # --- TRANSLATE STATE TEXT TO DATABASE ID ---
            state_id = False
            if self.applicant_state:
                # Find the matching state in the database
                state_record = self.env['res.country.state'].search([
                    ('name', '=', self.applicant_state),
                    ('country_id.code', '=', 'IN')
                ], limit=1)
                if state_record:
                    state_id = state_record.id
            # -------------------------------------------

            # 2. MAPPING: Put the data in the exact, separated Employee boxes
            employee.write({
                'ls_employee_id': self.registration_no,
                'father_name': self.father_name,
                'mother_name': self.mother_name,
                'birthday': self.date_of_birth,
                'sex': self.gender,
                'ls_aadhar': getattr(self, 'aadhaar_no', False),
                'ls_pan': getattr(self, 'pan_no', False),
                'image_1920': self.photograph,

                'permanent_street': self.applicant_street,
                'permanent_city': self.applicant_city,
                'permanent_state_id': state_id,
                'permanent_zip': self.pincode,
            })

            # 3. Map the Education Table
            if self.educational_qualification_ids:
                edu_lines = []
                for line in self.educational_qualification_ids:
                    edu_lines.append((0, 0, {
                        'ls_degree': 'other',
                        'specialisation': line.exam_name,
                        'college_university_name': line.university,
                    }))
                if edu_lines:
                    employee.write({'education_ids': edu_lines})

        return res

    def action_hold_applicant(self):
        template = self.env.ref('approval_recruitment.mail_template_applicant_on_hold', raise_if_not_found=False)
        for rec in self:
            rec.is_hold = True
            if template:
                template.send_mail(rec.id, force_send=True)

    def action_unhold_applicant(self):
        for rec in self:
            rec.is_hold = False

    def action_position_filled(self):
        template = self.env.ref('approval_recruitment.mail_template_hr_recruitments_positions_filled', raise_if_not_found=False)
        for rec in self:
            if template:
                template.send_mail(rec.id, force_send=True)

    def action_send_pre_onboarding_mail(self):
        self.ensure_one()
        template = self.env.ref(
            'approval_recruitment.mail_template_pre_onboarding',
            raise_if_not_found=False
        )
        if not template:
            raise UserError("Pre-Onboarding mail template not found.")
        if not self.email_from:
            raise UserError("Candidate email (Email ID) is missing on this application.")
        if not self.access_token:
            raise UserError("Security Token is missing. Please save the record first.")

        template.send_mail(self.id, force_send=True, email_values={
            'email_to': self.email_from,
            'email_from': self.env.user.email,
        })

        self.message_post(
            body=Markup(f" Pre-Onboarding form link sent to <b>{self.email_from}</b> by {self.env.user.name}."),
            subtype_xmlid="mail.mt_note",
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Mail Sent!',
                'message': f'Pre-Onboarding form link sent to {self.email_from}.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_send_pre_offer_mail(self):
        self.ensure_one()
        template = self.env.ref(
            'approval_recruitment.mail_template_pre_offer',
            raise_if_not_found=False
        )
        if not template:
            raise UserError("Pre-Offer mail template not found.")
        if not self.email_from:
            raise UserError("Candidate email (Email ID) is missing on this application.")
        if not self.access_token:
            raise UserError("Security Token is missing. Please save the record first.")

        template.send_mail(self.id, force_send=True, email_values={
            'email_to': self.email_from,
            'email_from': (
                    self.job_id.hr_head.work_email
                    or self.job_id.hr_head.private_email
                    or self.env.user.email
            ),
        })

        self.message_post(
            body=Markup(f" Pre-Offer form link sent to <b>{self.email_from}</b> by {self.env.user.name}."),
            subtype_xmlid="mail.mt_note",
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Mail Sent!',
                'message': f'Pre-Offer form link sent to {self.email_from}.',
                'type': 'success',
                'sticky': False,
            }
        }


