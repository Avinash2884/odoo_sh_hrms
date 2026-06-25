import json
from odoo import http, fields
from odoo.http import request
from datetime import timedelta

class EmployeeAPI(http.Controller):

    API_TOKEN = "HRMS_SECRET_2026_XYZ"

    @http.route('/hrms/api/employees', type='http', auth='none', methods=['GET'], csrf=False)
    def get_employees(self, **kwargs):
        try:
            # 🔐 Token validation
            token = request.httprequest.headers.get('X-API-TOKEN')
            if token != self.API_TOKEN:
                return request.make_response(
                    json.dumps({
                        "status": "error",
                        "message": "Unauthorized"
                    }),
                    status=401,
                    headers=[('Content-Type', 'application/json')]
                )

            # ✅ Fetch employees
            employees = request.env['hr.employee'].sudo().search([])

            data = []

            for emp in employees:
                try:
                    # ✅ Account IDs (SAFE)
                    account_names = []

                    if 'account_office_name_ids' in emp._fields:
                        account_names = emp.account_office_name_ids.mapped('name')

                    doj = emp.joining_date_recruit.strftime('%Y-%m-%d') \
                        if 'joining_date_recruit' in emp._fields and emp.joining_date_recruit else ''

                    shift_name = ''
                    if 'shift_id' in emp._fields and emp.shift_id:
                        shift_name = emp.shift_id.name

                    attendance_status = 'Absent'

                    attendance = request.env['hr.attendance'].sudo().search([
                        ('employee_id', '=', emp.id),
                        ('check_in', '>=', fields.Date.today())
                    ], limit=1)

                    if attendance:
                        attendance_status = 'Present'

                    planned_from = ''
                    planned_to = ''
                    planned_duration = ''

                    slot = request.env['planning.slot'].sudo().search([
                        ('employee_id', '=', emp.id)
                    ], limit=1, order="start_datetime desc")

                    if slot:
                        user_tz = request.env.user.tz or 'Asia/Kolkata'

                        if slot.start_datetime:
                            start = fields.Datetime.context_timestamp(
                                request.env.user.with_context(tz=user_tz),
                                slot.start_datetime
                            )
                            planned_from = start.strftime('%Y-%m-%d %H:%M:%S')

                        if slot.end_datetime:
                            end = fields.Datetime.context_timestamp(
                                request.env.user.with_context(tz=user_tz),
                                slot.end_datetime
                            )
                            planned_to = end.strftime('%Y-%m-%d %H:%M:%S')

                        if slot.start_datetime and slot.end_datetime:
                            duration = slot.end_datetime - slot.start_datetime

                            total_seconds = int(duration.total_seconds())
                            hours = total_seconds // 3600
                            minutes = (total_seconds % 3600) // 60

                            planned_duration = f"{hours:02d}:{minutes:02d}"

                    data.append({
                        'employee_id': emp.id,
                        'name': emp.name or '',
                        'email': emp.work_email or '',
                        'designation': emp.job_id.name if emp.job_id else '',
                        'phone': emp.mobile_phone or '',
                        'doj': doj,
                        'account_names': account_names,
                        'shift': shift_name,
                        'attendance_status': attendance_status,
                        'planned_from': planned_from,
                        'planned_to': planned_to,
                        'planned_duration': planned_duration,
                    })

                except Exception as inner_error:
                    continue

            # ✅ Success response
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
            # ❌ Global error
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
                    "name": emp.name or '',
                    "email": emp.work_email or '',
                    "company_id": emp.company_id.id,
                    "company_name": emp.company_id.name,
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



