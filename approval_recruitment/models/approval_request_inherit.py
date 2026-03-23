from odoo import models, fields, api , _

class ApprovalRequestInherit(models.Model):
    _inherit = 'approval.request'
    _description = 'Approval Request'

    category_id = fields.Many2one('approval.category', string="Category", required=True)
    has_total_no_of_positions = fields.Selection(related="category_id.has_total_no_of_positions")
    has_job_position = fields.Selection(related="category_id.has_job_position")
    has_experience_min = fields.Selection(related="category_id.has_experience_min")
    has_experience_max = fields.Selection(related="category_id.has_experience_max")
    has_overall_budget_for_all_posting = fields.Selection(related="category_id.has_overall_budget_for_all_posting")
    has_budget_for_each_employee_position = fields.Selection(related="category_id.has_budget_for_each_employee_position")
    has_start_date = fields.Selection(related="category_id.has_start_date")
    has_end_date = fields.Selection(related="category_id.has_end_date")

    no_of_position = fields.Integer(string="No of Position")
    approval_job_position = fields.Char(string="Approval Job Position")
    approval_experience_minimum = fields.Integer(string="Experience Min")
    approval_experience_maximum = fields.Integer(string="Experience Max")
    approval_overall_budget_for_all_posting = fields.Integer(string="Approval Budget for All Posting")
    approval_budget_for_each_employee_position = fields.Integer(string="Approval Budget for Per Employee")
    approval_start_date = fields.Date(string="Approval Start Date")
    approval_end_date = fields.Date(string="Approval End Date")

    # hr_skill_type_id = fields.Many2one( comodel_name='hr.skill.type',string="HR Skill Types")
    # hr_skill_ids = fields.One2many( 'hr.skill','approval_request_id',string="HR Skills")
    # hr_skill_level_ids = fields.One2many( 'hr.skill.level','approval_request_id',string="HR Skill Levels")

    @api.depends('approver_ids.status', 'approver_ids.required')
    def _compute_request_status(self):
        super(ApprovalRequestInherit, self)._compute_request_status()
        for request in self:
            if request.request_status == 'approved' and request.category_id:

                # Safely get XML ID
                external_ids = request.category_id.get_external_id()
                category_xml_id = external_ids.get(request.category_id.id)

                # Check Category
                if category_xml_id == 'approval_category_data_man_power_requisition_inherit' or \
                        request.category_id.name == 'Man Power Requisition':
                    print("✅ Man Power Requisition category matched — proceeding to create HR Job")

                    # Check if job exists
                    existing_job = self.env['hr.job'].search(
                        [('name', '=', request.approval_job_position)],
                        limit=1
                    )
                    if existing_job:
                        print("⚠ Job already exists, skipping creation")
                        continue

                    # --------------------------------------
                    # CREATE NEW HR JOB
                    # --------------------------------------
                    job = self.env['hr.job'].create({
                        'name': request.approval_job_position,
                        'approval_experience_minimum': request.approval_experience_minimum,
                        'approval_experience_maximum': request.approval_experience_maximum,
                        'approval_overall_budget_for_all_posting': request.approval_overall_budget_for_all_posting,
                        'approval_budget_for_each_employee_position': request.approval_budget_for_each_employee_position,
                        'no_of_recruitment': request.no_of_position,
                    })

                    print(f"✅ HR Job created: {job.name} (Positions: {job.no_of_recruitment})")
                else:
                    print("⚠ No skill selected — skipping skill mapping")
