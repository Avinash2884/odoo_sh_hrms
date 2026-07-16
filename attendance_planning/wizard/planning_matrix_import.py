# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
import base64
import io
from datetime import datetime
import logging

try:
    import openpyxl
except ImportError:
    openpyxl = None

_logger = logging.getLogger(__name__)


class PlanningMatrixImport(models.TransientModel):
    _name = 'planning.matrix.import'
    _description = 'Import Planning Matrix'

    upload_file = fields.Binary(string='Upload Excel Roster', required=True)
    file_name = fields.Char(string='File Name')

    def action_import_matrix(self):
        if not openpyxl:
            raise UserError("The 'openpyxl' Python library is missing.")
        if not self.upload_file:
            raise UserError("Please upload a file.")

        # 1. Read the Excel File
        file_data = base64.b64decode(self.upload_file)
        data = io.BytesIO(file_data)
        try:
            wb = openpyxl.load_workbook(data, data_only=True)
            sheet = wb.active
        except Exception as e:
            raise UserError(f"Could not read the Excel file. Make sure it is a valid .xlsx file. Error: {str(e)}")

        # 2. Map the Dates from the Header Row (Row 1)
        # Assuming Dates start at Column D (Index 3) based on your HR screenshot
        headers = list(sheet.iter_rows(min_row=1, max_row=1, values_only=True))[0]
        date_map = {}

        for col_idx in range(3, len(headers)):
            val = headers[col_idx]
            if not val:
                continue

            if isinstance(val, datetime):
                date_map[col_idx] = val.date()
            else:
                try:
                    date_map[col_idx] = datetime.strptime(str(val).strip(), '%m/%d/%Y').date()
                except ValueError:
                    continue

        if not date_map:
            raise UserError("Could not find any valid dates in the header row. Please format headers as MM/DD/YYYY.")

        # 3. Read Roster Rows and trigger our custom create() method!
        slots_to_create = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            emp_code = row[0]  # Column A: Employee ID
            if not emp_code:
                continue

            emp_code = str(emp_code).strip()

            for col_idx, target_date in date_map.items():
                shift_code = row[col_idx]


                # Create Week Off slot for empty cells or "WO"
                if not shift_code or str(shift_code).strip().upper() in ['WO', 'OFF', '']:
                    slots_to_create.append({
                        'import_employee_id': emp_code,
                        'import_date': target_date,
                        'is_week_off': True,  # Mark as week off
                    })
                    continue

                shift_code = str(shift_code).strip()

                # Find the Shift Template in Odoo
                calendar = self.env['resource.calendar'].search([('name', '=', shift_code)], limit=1)
                if not calendar:
                    raise UserError(
                        f"HALTED: Shift Template '{shift_code}' does not exist in Odoo. Please create it first.")

                # Push directly into the custom logic we built earlier
                slots_to_create.append({
                    'import_employee_id': emp_code,
                    'calendar_id': calendar.id,
                    'import_date': target_date,
                })

        if not slots_to_create:
            raise UserError("No valid shifts found to import.")

        # Create all the records safely
        self.env['planning.slot'].create(slots_to_create)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Successfully imported {len(slots_to_create)} shifts!',
                'type': 'success',
                'sticky': False,
            }
        }