from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    regularization = fields.Boolean(string="Regularization",
                                    help="Regularized attendance")

