from odoo import models, fields, api , _
from odoo.exceptions import ValidationError


class HrApplicantEvaluation(models.Model):
    _name = "hr.applicant.evaluation"
    _description = "Applicant Evaluation"

    applicant_id = fields.Many2one("hr.applicant", string="Applicant", required=True, ondelete="cascade")
    interviewer_id = fields.Many2one("res.users", string="Interviewer")
    education = fields.Float(string="Educational Background")
    professional = fields.Float(string="Professional Ability")
    personality = fields.Float(string="Personality")
    communication = fields.Float(string="Communication")
    knowledge = fields.Float(string="General Knowledge")
    experience = fields.Float(string="Work Experience")
    total_score = fields.Float(string="Overall Rating", compute="_compute_total", store=True)
    suitability = fields.Selection([("yes", "Yes"), ("no", "No")], string="Suitability")
    notes = fields.Text(string="Remarks")

    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("completed", "Completed"),
        ],
        string="Status",
    )

    @api.depends("education", "professional", "personality", "communication", "knowledge", "experience")
    def _compute_total(self):
        for rec in self:
            rec.total_score = rec.education + rec.professional + rec.personality + rec.communication + rec.knowledge + rec.experience

    @api.constrains("education", "professional", "personality", "communication", "knowledge", "experience")
    def _check_max_value(self):
        for rec in self:
            for field in ["education", "professional", "personality", "communication", "knowledge", "experience"]:
                value = getattr(rec, field)
                if value > 10:
                    raise ValidationError(f"{field.replace('_', ' ').title()} cannot be more than 10.")

    # @api.model
    # def create(self, vals):
    #     rec = super().create(vals)
    #     rec.applicant_id._update_stage_based_on_mark()  # only for mark → stage_job3
    #     return rec

    def write(self, vals):
        for rec in self:

            # Prevent editing completed evaluations
            if rec.status == "completed":
                editable_fields = {
                    "education",
                    "professional",
                    "personality",
                    "communication",
                    "knowledge",
                    "experience",
                    "notes",
                    "interviewer_id",
                    "suitability",
                }

                if editable_fields.intersection(vals.keys()):
                    raise ValidationError(
                        _("Completed evaluation cannot be modified.")
                    )

        res = super().write(vals)

        # # Update applicant stage after changes
        # for rec in self:
        #     if rec.applicant_id:
        #         rec.applicant_id._update_stage_based_on_mark()

        return res