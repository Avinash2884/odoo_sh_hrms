from copy import deepcopy
from datetime import datetime
from io import BytesIO

from odoo import http, _
from odoo.http import request

import xlsxwriter


class PayrollTDSSalaryRegister(http.Controller):

    @http.route(
        ['/export/salary-register/<int:wizard_id>'],
        type='http',
        auth='user'
    )
    def export_salary_register(self, wizard_id, **kwargs):
        pass