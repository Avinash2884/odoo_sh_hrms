from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import ValidationError


class CompanyPolicy(models.Model):
    _name = 'company.policy'
    _description = 'Company Policy'
    _inherit = ['mail.thread']

    name = fields.Char(string='Policy Name', required=True)
    active = fields.Boolean(default=True)

    # ✅ LINK (IMPORTANT)
    employee_policy_id = fields.Many2one('employee.policy')

    # ---------------- REVISION FIELDS ----------------

    revision_1_file_name = fields.Char(tracking=True)
    revision_1_file = fields.Binary()
    revision_1_date = fields.Datetime(readonly=True)
    revision_1_published = fields.Boolean(default=False)

    revision_2_file_name = fields.Char(tracking=True)
    revision_2_file = fields.Binary()
    revision_2_date = fields.Datetime(readonly=True)
    revision_2_published = fields.Boolean(default=False)

    revision_3_file_name = fields.Char(tracking=True)
    revision_3_file = fields.Binary()
    revision_3_date = fields.Datetime(readonly=True)
    revision_3_published = fields.Boolean(default=False)

    revision_4_file_name = fields.Char(tracking=True)
    revision_4_file = fields.Binary()
    revision_4_date = fields.Datetime(readonly=True)
    revision_4_published = fields.Boolean(default=False)

    revision_5_file_name = fields.Char(tracking=True)
    revision_5_file = fields.Binary()
    revision_5_date = fields.Datetime(readonly=True)
    revision_5_published = fields.Boolean(default=False)

    # ---------------- STATE ----------------

    state = fields.Selection([
        ('revision_1_publish', 'Rev 1'),
        ('revision_2_publish', 'Rev 2'),
        ('revision_3_publish', 'Rev 3'),
        ('revision_4_publish', 'Rev 4'),
        ('revision_5_publish', 'Rev 5'),
    ], tracking=True)

    warning_message = fields.Html(compute="_compute_warning")

    acknowledged_user_ids = fields.Many2many(
        'res.users',
        string="Acknowledged Users",
        tracking=True
    )

    acknowledged_log = fields.Text("Acknowledgement Log")

    @api.depends('state')
    def _compute_warning(self):
        for rec in self:
            rec.warning_message = """
                <div style="padding:10px;background:#fff3cd;border:1px solid #ffeeba;">
                    ⚠ Upload correct document before publishing.
                </div>
            """

    # ---------------- COMMON LOGIC ----------------

    def _publish_latest_revision(self, vals):
        now = datetime.now()
        publishing_index = None

        for i in reversed(range(1, 6)):
            if vals.get(f'revision_{i}_file'):
                publishing_index = i
                break

        if publishing_index:
            for j in range(1, 6):
                vals[f'revision_{j}_published'] = False

            vals[f'revision_{publishing_index}_published'] = True
            vals[f'revision_{publishing_index}_date'] = now

    # ---------------- CREATE ----------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._publish_latest_revision(vals)
        return super().create(vals_list)

    # ---------------- WRITE ----------------

    def write(self, vals):

        for rec in self:
            for i in range(1, 6):

                if vals.get(f'revision_{i}_published'):

                    if not (vals.get(f'revision_{i}_file') or rec[f'revision_{i}_file']):
                        raise ValidationError(f"Upload file before publishing Rev {i}")

                    for j in range(i + 1, 6):
                        if rec[f'revision_{j}_published']:
                            raise ValidationError(
                                f"Rev {j} already published. Cannot publish Rev {i}"
                            )

        res = super().write(vals)

        # ✅ ARCHIVE SYNC
        if 'active' in vals:
            for rec in self:
                if rec.employee_policy_id:
                    rec.employee_policy_id.active = vals['active']

        return res

    # ---------------- PUBLISH ----------------

    def action_publish(self, index=None):
        for rec in self:

            # 🔥 take specific revision OR latest fallback
            if index:
                file_data = rec[f'revision_{index}_file']
                file_name = rec[f'revision_{index}_file_name']
            else:
                file_data = False
                file_name = False

                for i in reversed(range(1, 6)):
                    if rec[f'revision_{i}_file']:
                        file_data = rec[f'revision_{i}_file']
                        file_name = rec[f'revision_{i}_file_name']
                        break

            # ✅ UPDATE
            if rec.employee_policy_id:
                rec.employee_policy_id.write({
                    'name': rec.name,
                    'document': file_data,
                    'file_name': file_name,
                })

            # 🆕 CREATE
            else:
                rec.employee_policy_id = self.env['employee.policy'].create({
                    'name': rec.name,
                    'document': file_data,
                    'file_name': file_name,
                })

            rec.acknowledged_user_ids = [(5, 0, 0)]
            rec.acknowledged_log = False

    # ---------------- BUTTONS ----------------

    def action_revision_1_publish(self):
        self._check_file_before_publish(self, 1)
        self.action_publish()
        self.revision_1_date = datetime.now()
        self.state = 'revision_1_publish'

    def action_revision_2_publish(self):
        self._check_file_before_publish(self, 2)
        self.action_publish()
        self.revision_2_date = datetime.now()
        self.state = 'revision_2_publish'

    def action_revision_3_publish(self):
        self._check_file_before_publish(self, 3)
        self.action_publish()
        self.revision_3_date = datetime.now()
        self.state = 'revision_3_publish'

    def action_revision_4_publish(self):
        self._check_file_before_publish(self, 4)
        self.action_publish()
        self.revision_4_date = datetime.now()
        self.state = 'revision_4_publish'

    def action_revision_5_publish(self):
        self._check_file_before_publish(self, 5)
        self.action_publish()
        self.revision_5_date = datetime.now()
        self.state = 'revision_5_publish'

    def _check_file_before_publish(self, rec, index):
        file_field = f'revision_{index}_file'

        if not rec[file_field]:
            raise ValidationError(
                f"Upload file before publishing Revision {index}"
            )

    # ---------------- PREVIEW ----------------

    def action_preview_revision(self):
        self.ensure_one()

        rev = int(self.env.context.get('revision_no'))

        file_data = self[f'revision_{rev}_file']
        file_name = self[f'revision_{rev}_file_name'] or f"Rev_{rev}.pdf"

        if not file_data:
            raise ValidationError("No file uploaded")

        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': file_data,
            'mimetype': 'application/pdf',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=false',
            'target': 'self',
        }

