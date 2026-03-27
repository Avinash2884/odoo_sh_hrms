from odoo import models, fields, api
from datetime import datetime


class CompanyPolicy(models.Model):
    _name = 'company.policy'
    _description = 'Company Policy'
    _inherit = ['mail.thread']

    name = fields.Char(string='Policy Name', required=True)

    revision_1_file_name = fields.Char("Revision 1 File Name", tracking=True)
    revision_1_file = fields.Binary(string='Revision 1')
    revision_1_date = fields.Datetime(string='Revision 1 Date', readonly=True)
    revision_1_published = fields.Boolean(string='Revision 1 Published', default=False)

    revision_2_file_name = fields.Char("Revision 2 File Name", tracking=True)
    revision_2_file = fields.Binary(string='Revision 2')
    revision_2_date = fields.Datetime(string='Revision 2 Date', readonly=True)
    revision_2_published = fields.Boolean(string='Revision 2 Published', default=False)

    revision_3_file_name = fields.Char("Revision 3 File Name", tracking=True)
    revision_3_file = fields.Binary(string='Revision 3')
    revision_3_date = fields.Datetime(string='Revision 3 Date', readonly=True)
    revision_3_published = fields.Boolean(string='Revision 3 Published', default=False)

    revision_4_file_name = fields.Char("Revision 4 File Name", tracking=True)
    revision_4_file = fields.Binary(string='Revision 4')
    revision_4_date = fields.Datetime(string='Revision 4 Date', readonly=True)
    revision_4_published = fields.Boolean(string='Revision 4 Published', default=False)

    revision_5_file_name = fields.Char("Revision 5 File Name", tracking=True)
    revision_5_file = fields.Binary(string='Revision 5')
    revision_5_date = fields.Datetime(string='Revision 5 Date', readonly=True)
    revision_5_published = fields.Boolean(string='Revision 5 Published', default=False)

    state = fields.Selection([
        ('submit', 'Submit'),
        ('publish', 'Publish'),
    ], string='Status', tracking=True)

    # ---------------------------------------------------------
    # Helper
    # ---------------------------------------------------------

    def _publish_latest_revision(self, vals):
        now = datetime.now()

        for i in reversed(range(1, 6)):
            file_field = f'revision_{i}_file'

            if vals.get(file_field):
                vals[f'revision_{i}_published'] = True
                vals[f'revision_{i}_date'] = now

                for j in range(1, i):
                    vals[f'revision_{j}_published'] = False

                break

    # ---------------------------------------------------------
    # CREATE (Odoo 19 Fix)
    # ---------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._publish_latest_revision(vals)
        return super().create(vals_list)

    # ---------------------------------------------------------
    # WRITE
    # ---------------------------------------------------------

    def write(self, vals):
        self._publish_latest_revision(vals)
        return super().write(vals)

    # ---------------------------------------------------------
    # BUTTONS
    # ---------------------------------------------------------

    def action_submit(self):
        self.state = 'submit'

    def action_publish(self):
        self.state = 'publish'

        for rec in self:

            file_data = False
            file_name = False

            for i in reversed(range(1, 6)):
                if rec[f'revision_{i}_published']:
                    file_data = rec[f'revision_{i}_file']
                    file_name = rec[f'revision_{i}_file_name']
                    break

            if file_data:

                existing_policy = self.env['employee.policy'].search([
                    ('name', '=', rec.name)
                ], limit=1)

                if existing_policy:
                    existing_policy.write({
                        'document': file_data,
                        'file_name': file_name
                    })
                else:
                    self.env['employee.policy'].create({
                        'name': rec.name,
                        'document': file_data,
                        'file_name': file_name
                    })