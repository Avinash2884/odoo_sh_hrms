from odoo import api, models
from datetime import date, timedelta, datetime
import calendar as cal_module
import pytz

INDIA_TZ = pytz.timezone('Asia/Kolkata')


def _to_ist(utc_naive_dt):
    """Convert naive UTC datetime → IST aware datetime."""
    if not utc_naive_dt:
        return None
    return pytz.utc.localize(utc_naive_dt).astimezone(INDIA_TZ)


def _ist_date(utc_naive_dt):
    """Return the IST calendar date for a naive UTC datetime."""
    aware = _to_ist(utc_naive_dt)
    return aware.date() if aware else None


def _ist_hhmm(utc_naive_dt):
    """Return 'HH:MM' string in IST for a naive UTC datetime."""
    aware = _to_ist(utc_naive_dt)
    return aware.strftime('%H:%M') if aware else ''


class AttendanceMatrixReport(models.AbstractModel):
    """
    Pure data-service model — no stored table, no ORM records.

    Week-off logic (two separate sources):
    ─────────────────────────────────────
    ROTATIONAL employees  →  planning.slot rows for the employee in the
                             requested month where is_week_off = True
                             (calendar_id is False).  These are uploaded
                             month-by-month by HR so we ONLY look at the
                             current month — no future/past bleed.

    REGULAR employees     →  EDP config params (same keys the EDP bouncer
                             reads):
                               attendance.edp_restrict_sunday
                               attendance.edp_restrict_sat_1 … _sat_5

    EDP badge rule        →  Only shown when the hr.edp.request is
                             'approved' AND the employee already has a
                             check_out on the matching hr.attendance record
                             for that day (i.e. the duty is DONE).
    """
    _name = 'attendance.matrix.report'
    _description = 'Attendance Sheet (A / OT / EDP grid)'

    # ──────────────────────────────────────────────────────────────────
    # REGULAR-SHIFT week-off helpers  (config-param based)
    # ──────────────────────────────────────────────────────────────────
    def _get_regular_weekoff_config(self):
        """Returns (restrict_sunday: bool, restricted_sat_weeks: set[int])."""
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
        """Return set of 'YYYY-MM-DD' strings that are week-offs for
        regular-shift employees in the given month."""
        days_in_month = cal_module.monthrange(year, month)[1]
        weekoffs = set()
        for day_num in range(1, days_in_month + 1):
            d = date(year, month, day_num)
            weekday = d.weekday()          # Mon=0 … Sun=6
            if weekday == 6 and restrict_sunday:
                weekoffs.add(str(d))
            elif weekday == 5:             # Saturday
                week_of_month = (d.day - 1) // 7 + 1
                if week_of_month in restricted_sats:
                    weekoffs.add(str(d))
        return weekoffs

    # ──────────────────────────────────────────────────────────────────
    # ROTATIONAL-SHIFT week-off helpers  (planning.slot based)
    # ──────────────────────────────────────────────────────────────────
    def _rotational_weekoff_days_for_employee(self, emp_id, year, month):
        """Return set of 'YYYY-MM-DD' strings that are week-offs for
        ONE rotational employee, sourced from planning.slot rows where
        is_week_off=True in the given month ONLY."""
        first_day = date(year, month, 1)
        last_day = date(year, month, cal_module.monthrange(year, month)[1])

        # planning.slot stores shift_date as a plain Date field.
        # We filter by that date range + this specific employee + no calendar
        # (is_week_off computed = True when calendar_id is False).
        slots = self.env['planning.slot'].sudo().search([
            ('employee_id', '=', emp_id),
            ('shift_date', '>=', first_day),
            ('shift_date', '<=', last_day),
            ('calendar_id', '=', False),   # is_week_off == True
        ])
        return {str(s.shift_date) for s in slots if s.shift_date}

    # ──────────────────────────────────────────────────────────────────
    # MAIN GRID BUILDER
    # ──────────────────────────────────────────────────────────────────
    @api.model
    def get_matrix_data(self, year, month, employee_ids=None, department_id=None):
        """Build and return the full month grid.

        Returns
        -------
        {
          'employees': [{'id': int, 'name': str, 'shift_type': str}, …],
          'days':      ['YYYY-MM-DD', …],          # all days in month
          'matrix':    {emp_id: {day_key: {'codes': […], 'detail': {…}}}, …},
          'weekoff_days_by_emp': {emp_id: ['YYYY-MM-DD', …], …},
        }
        """
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

        # ── Regular-shift week-off config (computed once) ──
        restrict_sunday, restricted_sats = self._get_regular_weekoff_config()
        regular_weekoffs = self._regular_weekoff_days_for_month(
            year, month, restrict_sunday, restricted_sats)

        # ── Per-employee week-off sets ──
        weekoff_days_by_emp = {}
        for emp in employees:
            if emp.shift_type == 'rotational':
                weekoff_days_by_emp[emp.id] = \
                    self._rotational_weekoff_days_for_employee(emp.id, year, month)
            else:
                # regular (or unset) — use config-param rules
                weekoff_days_by_emp[emp.id] = set(regular_weekoffs)

        # ── Attendance records: widen UTC window ±1 day for IST safety ──
        utc_window_start = datetime(year, month, 1) - timedelta(days=1)
        utc_window_end = datetime(year, month, days_in_month) + timedelta(days=2)

        attendances = self.env['hr.attendance'].search([
            ('employee_id', 'in', emp_ids),
            ('check_in', '>=', utc_window_start),
            ('check_in', '<', utc_window_end),
        ])

        # ── Approved EDP requests for this month ──
        edp_requests = self.env['hr.edp.request'].search([
            ('employee_id', 'in', emp_ids),
            ('date', '>=', first_day),
            ('date', '<=', last_day),
            ('state', '=', 'approved'),
        ])

        # ── att_lookup: (emp_id, 'YYYY-MM-DD' IST) → [hr.attendance, …] ──
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

        # ── edp_lookup: (emp_id, 'YYYY-MM-DD') → hr.edp.request ──
        # RULE: EDP badge only when employee has checked OUT that day.
        #       We check this inside the matrix loop below.
        edp_lookup = {}
        for edp in edp_requests:
            edp_lookup[(edp.employee_id.id, str(edp.date))] = edp

        # ── Build matrix ──
        matrix = {}
        for emp in employees:
            emp_row = {}
            emp_weekoffs = weekoff_days_by_emp[emp.id]

            for day_key in day_list:
                codes = []
                detail = {}

                day_atts = att_lookup.get((emp.id, day_key), [])
                has_checkout = any(a.check_out for a in day_atts)

                if day_atts:
                    codes.append('A')
                    punches = []
                    total_ot = 0.0
                    total_worked = 0.0

                    for a in day_atts:
                        approved_ot = a.approved_extra_hours or 0.0
                        worked = a.worked_hours_custom or 0.0
                        punches.append({
                            'check_in': _ist_hhmm(a.check_in),
                            # Show '-' if employee hasn't checked out yet
                            'check_out': _ist_hhmm(a.check_out) if a.check_out else '-',
                            'worked_hours': round(worked, 2),
                            'extra_hours': round(a.extra_hours or 0.0, 2),
                            'approved_extra_hours': round(approved_ot, 2),
                            'late_checkout_state': a.late_checkout_state,
                        })
                        total_ot += approved_ot
                        total_worked += worked

                    if total_ot > 0:
                        codes.append('OT')

                    detail['punches'] = punches
                    detail['total_worked_hours'] = round(total_worked, 2)
                    detail['total_ot_hours'] = round(total_ot, 2)
                    # Total payable = worked hours + approved OT
                    detail['total_payable_hours'] = round(total_worked + total_ot, 2)

                edp = edp_lookup.get((emp.id, day_key))
                if edp:
                    # ── KEY RULE: EDP badge only if checkout has happened ──
                    if has_checkout:
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
            # Convert sets → lists for JSON serialisation
            'weekoff_days_by_emp': {
                str(emp_id): list(wo_set)
                for emp_id, wo_set in weekoff_days_by_emp.items()
            },
        }