# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import io
import xlsxwriter
from datetime import datetime


class AttendanceMatrixController(http.Controller):

    @http.route('/attendance_matrix/export_excel', type='http', auth='user')
    def export_excel(self, year, month, shift_filter='all', search_text='', **kwargs):
        year = int(year)
        month = int(month)

        # 1. Fetch the exact same data the UI uses (Zero logic changes!)
        data = request.env['attendance.matrix.report'].get_matrix_data(year, month)

        # 2. Apply the UI filters so the Excel matches what they see on screen
        employees = data.get('employees', [])
        if shift_filter != 'all':
            employees = [e for e in employees if e.get('shift_type', 'regular') == shift_filter]

        if search_text:
            q = search_text.lower()
            employees = [e for e in employees if
                         q in str(e.get('name', '')).lower() or q in str(e.get('department_id', '')).lower()]

        days = data.get('days', [])
        matrix = data.get('matrix', {})
        consolidation = data.get('consolidation', {})
        all_leave_codes = data.get('all_leave_codes', [])

        # 3. Create the Excel File in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Attendance Matrix')

        # Formats
        head_format = workbook.add_format(
            {'bold': True, 'bg_color': '#f3f4f6', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        cell_format = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        emp_format = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter'})

        # 4. Write Headers
        headers = ['Emp ID', 'Employee Name', 'Department']
        for d in days:
            day_num = d.split('-')[2]
            headers.append(day_num)  # e.g., 01, 02, 03

        headers.extend(
            ['Calendar Days', 'Working Days', 'Days Worked', 'EDP Days', 'Non-Payable OT', 'Payable OT (Hrs)',
             'OT Days', 'PH Worked'])
        headers.extend(all_leave_codes)

        for col_num, header in enumerate(headers):
            sheet.write(0, col_num, header, head_format)

        # 5. Write Data Rows
        row = 1
        for emp in employees:
            emp_id = emp['id']
            sheet.write(row, 0, emp.get('ls_employee_id', ''), emp_format)
            sheet.write(row, 1, emp.get('name', ''), emp_format)
            sheet.write(row, 2, emp.get('department_id', ''), emp_format)

            col = 3
            # Write Daily Codes
            for d in days:
                cell_data = matrix.get(emp_id, {}).get(d, {})
                codes = cell_data.get('codes', [])
                # Clean up codes for Excel (e.g., remove :DRAFT or LV:)
                display_codes = [c.replace(':DRAFT', '').replace('LV:', '').replace('SH:', '') for c in codes]
                sheet.write(row, col, ', '.join(display_codes), cell_format)
                col += 1

            # Write Consolidation Data
            cons = consolidation.get(emp_id, {})
            sheet.write(row, col, cons.get('calendar_days', 0), cell_format)
            sheet.write(row, col + 1, cons.get('working_days', 0), cell_format)
            sheet.write(row, col + 2, cons.get('effective_present', 0), cell_format)
            sheet.write(row, col + 3, cons.get('edp_days', 0), cell_format)
            sheet.write(row, col + 4, cons.get('ot_hours_less_fmt', '0:00'), cell_format)
            sheet.write(row, col + 5, cons.get('ot_hours_fmt', '0:00'), cell_format)
            sheet.write(row, col + 6, cons.get('ot_days', 0), cell_format)
            sheet.write(row, col + 7, cons.get('ph_worked', 0), cell_format)

            col += 8

            # Write Leave Details
            leave_counts = cons.get('leave_counts_full', {})
            for lc in all_leave_codes:
                val = leave_counts.get(lc, 0)
                sheet.write(row, col, val if val else 0, cell_format)
                col += 1

            row += 1

        workbook.close()
        output.seek(0)

        # 6. Return the file as a download
        file_name = f"Attendance_Matrix_{year}_{month:02d}.xlsx"
        return request.make_response(
            output.getvalue(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={file_name}')
            ]
        )