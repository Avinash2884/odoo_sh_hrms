from odoo import api, models
from datetime import date, timedelta, datetime
import calendar as cal_module
import pytz

INDIA_TZ = pytz.timezone('Asia/Kolkata')


def _to_ist(utc_naive_dt):
    if not utc_naive_dt:
        return None
    return pytz.utc.localize(utc_naive_dt).astimezone(INDIA_TZ)


def _ist_date(utc_naive_dt):
    aware = _to_ist(utc_naive_dt)
    return aware.date() if aware else None


def _ist_hhmm(utc_naive_dt):
    aware = _to_ist(utc_naive_dt)
    return aware.strftime('%H:%M') if aware else ''


class AttendanceMatrixReport(models.AbstractModel):
    """
    Attendance Sheet grid — one cell per (employee, day).

    Badge logic
    ────────────────────────────────────────────────────────────────
    ROTATIONAL employee:
      planning.slot with calendar_id exists (real shift):
        • No check-in yet          → shift name  e.g. "G1"  (planned)
        • Checked in, no checkout  → "P"                     (in-progress)
        • Checked out              → "A"  (+ "OT" if approved OT > 0)
      planning.slot with no calendar_id → week-off (WO)
      No planning slot at all          → empty cell

    REGULAR employee:
      Any hr.attendance that day → "A"  (+ "OT")
      No attendance              → week-off if config says so, else empty

    EDP badge:  approved hr.edp.request AND check_out exists that day.
    """
    _name = 'attendance.matrix.report'
    _description = 'Attendance Sheet (A / OT / EDP grid)'

    # ── Regular week-off (config params) ─────────────────────────────────────
    def _get_regular_weekoff_config(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param

        def is_active(key):
            return str(get_param(key, 'False')).strip().lower() in (
                'true', '1', 't', 'yes', 'y')

        restrict_sunday = is_active('attendance.edp_restrict_sunday')
        restricted_sats = {n for n in range(1, 6)
                           if is_active(f'attendance.edp_restrict_sat_{n}')}
        return restrict_sunday, restricted_sats

    def _regular_weekoff_days_for_month(self, year, month,
                                        restrict_sunday, restricted_sats):
        days_in_month = cal_module.monthrange(year, month)[1]
        weekoffs = set()
        for day_num in range(1, days_in_month + 1):
            d = date(year, month, day_num)
            weekday = d.weekday()
            if weekday == 6 and restrict_sunday:
                weekoffs.add(str(d))
            elif weekday == 5:
                week_of_month = (d.day - 1) // 7 + 1
                if week_of_month in restricted_sats:
                    weekoffs.add(str(d))
        return weekoffs

    # ── Rotational week-off (planning slots with no calendar) ────────────────
    def _rotational_weekoff_days_for_employee(self, emp_id, year, month):
        first_day = date(year, month, 1)
        last_day = date(year, month, cal_module.monthrange(year, month)[1])
        slots = self.env['planning.slot'].sudo().search([
            ('employee_id', '=', emp_id),
            ('shift_date', '>=', first_day),
            ('shift_date', '<=', last_day),
            ('calendar_id', '=', False),
        ])
        return {str(s.shift_date) for s in slots if s.shift_date}

    # ── Rotational real shifts (with calendar_id) ─────────────────────────────
    def _rotational_shift_slots_for_employee(self, emp_id, year, month):
        """Returns { 'YYYY-MM-DD': shift_name } for real (non-WO) planning slots."""
        first_day = date(year, month, 1)
        last_day = date(year, month, cal_module.monthrange(year, month)[1])
        slots = self.env['planning.slot'].sudo().search([
            ('employee_id', '=', emp_id),
            ('shift_date', '>=', first_day),
            ('shift_date', '<=', last_day),
            ('calendar_id', '!=', False),
        ])
        result = {}
        for s in slots:
            if s.shift_date:
                result[str(s.shift_date)] = s.calendar_id.name or 'SHIFT'
        return result

    # ── Main grid builder ─────────────────────────────────────────────────────
    @api.model
    def get_matrix_data(self, year, month, employee_ids=None, department_id=None):
        Employee = self.env['hr.employee']
        domain = []
        if employee_ids:
            domain.append(('id', 'in', employee_ids))
        if department_id:
            domain.append(('department_id', '=', department_id))
        employees = Employee.search(domain, order='name')

        days_in_month = cal_module.monthrange(year, month)[1]
        first_day = date(year, month, 1)
        last_day = date(year, month, days_in_month)
        day_list = [str(first_day + timedelta(days=i)) for i in range(days_in_month)]
        day_set = set(day_list)

        if not employees:
            return {
                'employees': [],
                'days': day_list,
                'matrix': {},
                'weekoff_days_by_emp': {},
            }

        emp_ids = employees.ids

        # Regular week-off config (once for all regular employees)
        restrict_sunday, restricted_sats = self._get_regular_weekoff_config()
        regular_weekoffs = self._regular_weekoff_days_for_month(
            year, month, restrict_sunday, restricted_sats)

        # Per-employee data
        weekoff_days_by_emp = {}
        shift_slots_by_emp = {}   # rotational only: day_key → shift_name

        for emp in employees:
            if emp.shift_type == 'rotational':
                weekoff_days_by_emp[emp.id] = \
                    self._rotational_weekoff_days_for_employee(emp.id, year, month)
                shift_slots_by_emp[emp.id] = \
                    self._rotational_shift_slots_for_employee(emp.id, year, month)
            else:
                weekoff_days_by_emp[emp.id] = set(regular_weekoffs)
                shift_slots_by_emp[emp.id] = {}

        # Attendance records — widen UTC window ±1 day for IST safety
        utc_window_start = datetime(year, month, 1) - timedelta(days=1)
        utc_window_end = datetime(year, month, days_in_month) + timedelta(days=2)

        attendances = self.env['hr.attendance'].search([
            ('employee_id', 'in', emp_ids),
            ('check_in', '>=', utc_window_start),
            ('check_in', '<', utc_window_end),
        ])

        # Approved EDP requests
        edp_requests = self.env['hr.edp.request'].search([
            ('employee_id', 'in', emp_ids),
            ('date', '>=', first_day),
            ('date', '<=', last_day),
            ('state', '=', 'approved'),
        ])

        # att_lookup: (emp_id, IST-date-str) → [hr.attendance, …]
        att_lookup = {}
        for att in attendances:
            if not att.check_in:
                continue
            ist_day = _ist_date(att.check_in)
            if not ist_day:
                continue
            day_key = str(ist_day)
            if day_key not in day_set:
                continue
            att_lookup.setdefault((att.employee_id.id, day_key), []).append(att)

        # edp_lookup: (emp_id, date-str) → hr.edp.request
        edp_lookup = {}
        for edp in edp_requests:
            edp_lookup[(edp.employee_id.id, str(edp.date))] = edp

        # Build matrix
        matrix = {}
        for emp in employees:
            emp_row = {}
            is_rotational = (emp.shift_type == 'rotational')
            emp_shifts = shift_slots_by_emp.get(emp.id, {})

            for day_key in day_list:
                codes = []
                detail = {}

                day_atts = att_lookup.get((emp.id, day_key), [])
                has_checkin  = bool(day_atts)
                has_checkout = any(a.check_out for a in day_atts)

                if is_rotational:
                    shift_name = emp_shifts.get(day_key)  # None if no slot

                    if shift_name:
                        if not has_checkin:
                            # Shift assigned, employee not arrived yet
                            codes.append(shift_name)
                            detail['shift_name'] = shift_name
                            detail['shift_status'] = 'planned'
                        elif has_checkin and not has_checkout:
                            # Currently working
                            codes.append('P')
                            detail['shift_name'] = shift_name
                            detail['shift_status'] = 'in_progress'
                        else:
                            # Shift completed
                            codes.append('A')
                            detail['shift_name'] = shift_name
                            detail['shift_status'] = 'done'
                else:
                    # Regular employee
                    if has_checkin:
                        codes.append('A')

                # OT — only when checked out, both shift types
                if has_checkout:
                    total_ot = sum(a.approved_extra_hours or 0.0 for a in day_atts)
                    if total_ot > 0:
                        codes.append('OT')

                # Punch details for popup
                if day_atts:
                    punches = []
                    total_worked = 0.0
                    total_ot = 0.0
                    for a in day_atts:
                        approved_ot = a.approved_extra_hours or 0.0
                        worked = a.worked_hours_custom or 0.0
                        punches.append({
                            'check_in':  _ist_hhmm(a.check_in),
                            'check_out': _ist_hhmm(a.check_out) if a.check_out else '-',
                            'worked_hours': round(worked, 2),
                            'extra_hours': round(a.extra_hours or 0.0, 2),
                            'approved_extra_hours': round(approved_ot, 2),
                            'late_checkout_state': a.late_checkout_state,
                        })
                        total_worked += worked
                        total_ot += approved_ot

                    detail['punches'] = punches
                    detail['total_worked_hours'] = round(total_worked, 2)
                    detail['total_ot_hours'] = round(total_ot, 2)
                    detail['total_payable_hours'] = round(total_worked + total_ot, 2)

                # EDP — only after checkout
                edp = edp_lookup.get((emp.id, day_key))
                if edp and has_checkout:
                    codes.append('EDP')
                    detail['edp'] = {
                        'shift_template': edp.calendar_id.name if edp.calendar_id else '',
                        'state': edp.state,
                    }

                emp_row[day_key] = {'codes': codes, 'detail': detail}

            matrix[emp.id] = emp_row

        return {
            'employees': [
                {'id': e.id, 'name': e.name, 'shift_type': e.shift_type or 'regular'}
                for e in employees
            ],
            'days': day_list,
            'matrix': matrix,
            'weekoff_days_by_emp': {
                str(emp_id): list(wo_set)
                for emp_id, wo_set in weekoff_days_by_emp.items()
            },
        }