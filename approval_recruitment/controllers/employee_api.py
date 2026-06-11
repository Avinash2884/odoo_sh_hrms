import json
from odoo import http
from odoo.http import request

class EmployeeAPI(http.Controller):

    API_TOKEN = "HRMS_SECRET_2026_XYZ"

    @http.route('/hrms/api/employees', type='http', auth='none', methods=['GET'], csrf=False)
    def get_employees(self, **kwargs):

        token = request.httprequest.headers.get('X-API-TOKEN')

        if token != self.API_TOKEN:
            return request.make_response(
                json.dumps({"error": "Unauthorized"}),
                status=401,
                headers=[('Content-Type', 'application/json')]
            )

        # 🔥 ONLY mapped employees
        employees = request.env['hr.employee'].sudo().search([
            ('account_office_name_id', '!=', False)
        ])

        data = []

        for emp in employees:
            data.append({
                'name': emp.name or '',
                'email': emp.work_email or '',
                'designation': emp.job_title or '',
                'phone': emp.mobile_phone or '',
                'doj': str(emp.joining_date_recruit or ''),
                'account_name': emp.account_office_name_id.name or''
            })

        return request.make_response(
            json.dumps({
                "status": "success",
                "count": len(data),
                "data": data
            }),
            headers=[('Content-Type', 'application/json')]
        )