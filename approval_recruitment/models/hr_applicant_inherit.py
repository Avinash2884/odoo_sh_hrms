from datetime import date, timedelta

from odoo.exceptions import ValidationError

from odoo import models, fields, api , _

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

    @api.onchange('interviewer_ids')
    def _onchange_interviewer_ids(self):

        if not self.interviewer_ids:
            self.evaluation_ids = [(5, 0, 0)]
            return

        commands = [(5, 0, 0)]  # clear all lines

        for user in self.interviewer_ids:
            commands.append((0, 0, {
                'interviewer_id': user.id
            }))

        self.evaluation_ids = commands
        artists = ['interviewer_ids1', 'interviewer_ids2', 'interviewer_ids3']
        print(artists(1))

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
        print("🔔 CRON STARTED: Move Not Joined Applicants")

        today = fields.Date.today()
        ten_days_ago = today - timedelta(days=10)
        print("📅 Today Date:", today)
        print("⏳ Threshold Date (10 days ago):", ten_days_ago)

        # Get the "No Shown" stage
        not_shown_stage = self.env.ref(
            'approval_recruitment.stage_job8', raise_if_not_found=False
        )
        if not not_shown_stage:
            print("❌ No Shown stage NOT FOUND")
            return

        # Search applicants that have a joining date, haven't joined, and not already in "No Shown"
        applicants = self.search([
            ('ls_date_of_joining', '!=', False),
            ('employee_id', '=', False),
        ])

        print("👥 Total Applicants with joining date but not joined:", len(applicants))

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
        self._reorder_contract_proposal_stage()

        if 'stage_id' in vals:
            stage_offer_release = self.env.ref('hr_recruitment.stage_job4', raise_if_not_found=False)
            stage_offer_accepted = self.env.ref('hr_recruitment.stage_job5', raise_if_not_found=False)

            for rec in self:
                old_stage = old_stage_map.get(rec.id)

                # ---------------------------
                # 1️⃣ Send Offer Release Mail to Candidate
                # ---------------------------
                if stage_offer_release and old_stage != stage_offer_release.id and rec.stage_id.id == stage_offer_release.id:
                    template = self.env.ref(
                        'approval_recruitment.mail_template_offer_release')
                    template.sudo().send_mail(rec.id, force_send=True)

                # ---------------------------
                # 2️⃣ Send Offer Accepted Mail to Recruiter/HR (Optional)
                # ---------------------------
                if stage_offer_accepted and old_stage != stage_offer_accepted.id and rec.stage_id.id == stage_offer_accepted.id:
                    # Example: send via another template if needed
                    template = self.env.ref(
                        'approval_recruitment.mail_template_offer_accepted')
                    template.sudo().send_mail(rec.id, force_send=True)

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
            if not vals.get('registration_no') or \
                    vals.get('registration_no') == 'New':
                vals['registration_no'] = self.env[
                                              'ir.sequence'
                                          ].next_by_code(
                    'hr.applicant.registration'
                ) or 'New'
        return super().create(vals_list)