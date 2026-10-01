from odoo import models, fields


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    report_footer_address_2 = fields.Html(
        string='Footer Address 2',
        related='company_id.report_footer_address_2',
        readonly=False,
    )

    report_footer_address_3 = fields.Html(
        string='Footer Address 3',
        related='company_id.report_footer_address_3',
        readonly=False,
    )