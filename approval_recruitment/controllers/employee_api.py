import json
from odoo import http
from odoo.http import request

class EmployeeAPI(http.Controller):

    API_TOKEN = "HRMS_SECRET_2026_XYZ"

    @http.route('/hrms/api/employees', type='http', auth='none', methods=['GET'], csrf=False)
    def get_employees(self, **kwargs):
        try:
            token = request.httprequest.headers.get('X-API-TOKEN')
            if token != self.API_TOKEN:
                return request.make_response(
                    json.dumps({"status": "error", "message": "Unauthorized"}),
                    status=401,
                    headers=[('Content-Type', 'application/json')]
                )

            employees = request.env['hr.employee'].sudo().search([])
            data = []

            for emp in employees:
                try:
                    # ✅ GET ACCOUNT IDS INSTEAD OF NAMES
                    account_ids = []
                    if 'account_office_name_ids' in emp._fields:
                        try:
                            account_ids = emp.account_office_name_ids.ids
                        except Exception:
                            account_ids = []

                    doj = ''
                    if 'joining_date_recruit' in emp._fields and emp.joining_date_recruit:
                        doj = str(emp.joining_date_recruit)

                    data.append({
                        'name': emp.name or '',
                        'email': emp.work_email or '',
                        'designation': emp.job_title or '',
                        'phone': emp.mobile_phone or '',
                        'doj': doj,
                        'account_ids': account_ids  # 🔥 UPDATED
                    })

                except Exception:
                    continue

            return request.make_response(
                json.dumps({
                    "status": "success",
                    "count": len(data),
                    "data": data
                }),
                status=200,
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            return request.make_response(
                json.dumps({
                    "status": "error",
                    "message": str(e)
                }),
                status=500,
                headers=[('Content-Type', 'application/json')]
            )

    @http.route('/hrms/api/employees/name', type='http', auth='none', methods=['GET'], csrf=False)
    def employee_dropdown(self, **kwargs):
        try:
            # 🔐 Token validation
            token = request.httprequest.headers.get('X-API-TOKEN')
            if token != self.API_TOKEN:
                return request.make_response(
                    json.dumps({"status": "error", "message": "Unauthorized"}),
                    status=401,
                    headers=[('Content-Type', 'application/json')]
                )

            # 📌 Fetch employees
            employees = request.env['hr.employee'].sudo().search([])

            data = []
            for emp in employees:
                data.append({
                    "id": emp.id,
                    "name": emp.name or ''
                })

            return request.make_response(
                json.dumps({
                    "status": "success",
                    "count": len(data),
                    "data": data
                }),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            return request.make_response(
                json.dumps({
                    "status": "error",
                    "message": "Internal Server Error"
                }),
            )
