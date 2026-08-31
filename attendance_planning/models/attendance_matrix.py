from odoo import api, models
from datetime import date, timedelta, datetime
import calendar as cal_module
import pytz

INDIA_TZ = pytz.timezone('Asia/Kolkata')

# ── Leave type → short code map ────────────────────────────────────────────────
LEAVE_SHORT_CODES = {
    'Privilege Leave': 'PL',
    'Sick Leave': 'SL',
    'Casual Leave': 'CL',
    'Bereavement Leave': 'BL',
    'Maternity Leave': 'ML',
    'Paternity Leave': 'PTL',
    'Wedding Leave': 'WL',
    'Unpaid(LOP)': 'LOP',
    'Loss of Pay': 'LOP',
    'Compensatory Days': 'CO',
    'Compensatory Off': 'CO',
    'Extra Time Off': 'ETO',
    'Sick Leave - Probation': 'SLP',
    'Casual Leave - Probation': 'CLP',
}

LOP_NAMES = {'Unpaid(LOP)', 'Loss of Pay', 'LOP'}
COMPOFF_NAMES = {'Compensatory Days', 'Compensatory Off', 'Comp Off'}


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


def _fmt_hours(h):
    if not h:
        return '0:00'
    hh = int(h)
    mm = int(round((h - hh) * 60))
    return f'{hh}:{mm:02d}'


def _get_leave_short_code(lt_name):
    if lt_name in LEAVE_SHORT_CODES:
        return LEAVE_SHORT_CODES[lt_name]
    words = lt_name.strip().split()
    if len(words) >= 2:
        return ''.join(w[0].upper() for w in words[:4])
    return lt_name[:4].upper()


class AttendanceMatrixReport(models.AbstractModel):
    _name = 'attendance.matrix.report'
    _description = 'Attendance Sheet Matrix'

    def _get_regular_weekoff_config(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param

        def is_active(key):
            return str(get_param(key, 'False')).strip().lower() in ('true', '1', 't', 'yes', 'y')

        restrict_sunday = is_active('attendance.edp_restrict_sunday')
        restricted_sats = {n for n in range(1, 6)
                           if is_active(f'attendance.edp_restrict_sat_{n}')}
        return restrict_sunday, restricted_sats

    def _regular_weekoff_days_for_month(self, year, month, restrict_sunday, restricted_sats):
        days_in_month = cal_module.monthrange(year, month)[1]
        weekoffs = set()
        for day_num in range(1, days_in_month + 1):
            d = date(year, month, day_num)
            wd = d.weekday()
            if wd == 6 and restrict_sunday:
                weekoffs.add(str(d))
            elif wd == 5:
                week_of_month = (d.day - 1) // 7 + 1
                if week_of_month in restricted_sats:
                    weekoffs.add(str(d))
        return weekoffs

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

    def _rotational_shift_slots_for_employee(self, emp_id, year, month):
        first_day = date(year, month, 1)
        last_day = date(year, month, cal_module.monthrange(year, month)[1])
        slots = self.env['planning.slot'].sudo().search([
            ('employee_id', '=', emp_id),
            ('shift_date', '>=', first_day),
            ('shift_date', '<=', last_day),
            ('calendar_id', '!=', False),
            ('state', '=', 'published'),
        ])
        result = {}
        for s in slots:
            if s.shift_date:
                result[str(s.shift_date)] = s.calendar_id.name or 'SHIFT'
        return result

    def _get_comp_off_leave_type(self):
        return self.env['hr.leave.type'].sudo().search(
            ['|', ('name', '=', 'Compensatory Days'),
             ('name', '=', 'Compensatory Off')], limit=1)

    def _grant_compensatory_off(self, emp, worked_date):
        comp_type = self._get_comp_off_leave_type()
        if not comp_type:
            return
        marker = f'[PH-WORKED:{worked_date}]'
        existing = self.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', emp.id),
            ('holiday_status_id', '=', comp_type.id),
            ('name', 'like', marker),
        ], limit=1)
        if existing:
            return
        allocation = self.env['hr.leave.allocation'].sudo().create({
            'name': f'Comp-off for working on public holiday {worked_date} {marker}',
            'employee_id': emp.id,
            'holiday_status_id': comp_type.id,
            'number_of_days': 1,
            'date_from': worked_date,
        })
        try:
            allocation.sudo().action_confirm()
            allocation.sudo().action_validate()
        except Exception:
            pass

    @api.model
    def get_matrix_data(self, year, month, employee_ids=None, department_id=None):
        Employee = self.env['hr.employee']
        domain = []
        if employee_ids:
            domain.append(('id', 'in', employee_ids))
        if department_id:
            domain.append(('department_id', '=', department_id))

        # Forces sequential employee ID sorting
        employees = Employee.search(domain, order='ls_employee_id asc, name asc')

        days_in_month = cal_module.monthrange(year, month)[1]
        first_day = date(year, month, 1)
        last_day = date(year, month, days_in_month)
        day_list = [str(first_day + timedelta(days=i)) for i in range(days_in_month)]
        day_set = set(day_list)

        today_str = str(datetime.now(INDIA_TZ).date())

        if not employees:
            return {'employees': [], 'days': day_list, 'matrix': {}, 'consolidation': {}, 'weekoff_days_by_emp': {},
                    'public_holidays': {}, 'leave_type_colors': {}, 'all_leave_codes': []}

        emp_ids = employees.ids
        restrict_sunday, restricted_sats = self._get_regular_weekoff_config()
        regular_weekoffs = self._regular_weekoff_days_for_month(year, month, restrict_sunday, restricted_sats)

        weekoff_days_by_emp = {}
        shift_slots_by_emp = {}
        for emp in employees:
            if emp.shift_type == 'rotational':
                weekoff_days_by_emp[emp.id] = self._rotational_weekoff_days_for_employee(emp.id, year, month)
                shift_slots_by_emp[emp.id] = self._rotational_shift_slots_for_employee(emp.id, year, month)
            else:
                weekoff_days_by_emp[emp.id] = set(regular_weekoffs)
                shift_slots_by_emp[emp.id] = {}

        utc_window_start = datetime(year, month, 1) - timedelta(days=1)
        utc_window_end = datetime(year, month, days_in_month) + timedelta(days=2)
        attendances = self.env['hr.attendance'].search([
            ('employee_id', 'in', emp_ids),
            ('check_in', '>=', utc_window_start),
            ('check_in', '<', utc_window_end),
        ])

        local_tz = pytz.timezone('Asia/Calcutta')
        ph_leaves = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),
            '|', ('company_id', '=', self.env.company.id), ('company_id', '=', False),
        ])
        public_holiday_map = {}
        for leaf in ph_leaves:
            if leaf.date_from:
                utc_dt = leaf.date_from.replace(tzinfo=pytz.utc)
                local_date = utc_dt.astimezone(local_tz).date()
                date_str = str(local_date)
                if date_str in day_set:
                    public_holiday_map[date_str] = leaf.name or 'Public Holiday'

        edp_requests = self.env['hr.edp.request'].search([
            ('employee_id', 'in', emp_ids),
            ('date', '>=', first_day), ('date', '<=', last_day),
            ('state', '=', 'approved'),
        ])

        all_leaves = self.env['hr.leave'].sudo().search([
            ('employee_id', 'in', emp_ids),
            ('state', 'in', ['validate', 'confirm', 'validate1']),
        ])

        all_leave_type_records = self.env['hr.leave.type'].search([], order='name')
        all_leave_codes = []
        _seen_codes = set()
        for lt in all_leave_type_records:
            code = _get_leave_short_code(lt.name or 'Leave')
            if code not in _seen_codes:
                _seen_codes.add(code)
                all_leave_codes.append(code)

        leave_lookup = {}
        leave_counts_by_emp = {e.id: {} for e in employees}
        leave_type_colors = {}
        color_palette = ['#6366f1', '#ec4899', '#14b8a6', '#f59e0b', '#8b5cf6', '#ef4444', '#10b981', '#f97316',
                         '#06b6d4', '#84cc16', '#a855f7', '#64748b']
        color_index = 0

        for leave in all_leaves:
            lt_name = leave.holiday_status_id.name or 'Leave'
            is_validated = leave.state == 'validate'
            is_draft = not is_validated

            lv_start = None
            lv_end = None
            if leave.date_from:
                lv_start = _ist_date(leave.date_from)
            elif getattr(leave, 'request_date_from', False):
                lv_start = leave.request_date_from
            if leave.date_to:
                lv_end = _ist_date(leave.date_to)
            elif getattr(leave, 'request_date_to', False):
                lv_end = leave.request_date_to
            elif lv_start:
                lv_end = lv_start

            if not lv_start or not lv_end:
                continue
            if lv_end < first_day or lv_start > last_day:
                continue

            if lt_name not in leave_type_colors:
                leave_type_colors[lt_name] = color_palette[color_index % len(color_palette)]
                color_index += 1

            short_code = _get_leave_short_code(lt_name)
            is_lop = lt_name in LOP_NAMES or short_code == 'LOP'
            is_compoff = lt_name in COMPOFF_NAMES or short_code == 'CO'

            is_half = False
            try:
                if float(leave.number_of_days) <= 0.5:
                    is_half = True
            except Exception:
                pass

            current = max(lv_start, first_day)
            end = min(lv_end, last_day)
            while current <= end:
                day_str = str(current)
                if day_str in day_set:
                    leave_lookup[(leave.employee_id.id, day_str)] = {
                        'name': lt_name,
                        'short_code': short_code,
                        'half_day': is_half,
                        'is_lop': is_lop,
                        'is_compoff': is_compoff,
                        'draft': is_draft,
                        'validated': is_validated,
                    }
                    if is_validated:
                        counts = leave_counts_by_emp[leave.employee_id.id]
                        inc = 0.5 if is_half else 1.0
                        counts[short_code] = counts.get(short_code, 0.0) + inc
                current += timedelta(days=1)

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

        edp_lookup = {}
        for edp in edp_requests:
            edp_lookup[(edp.employee_id.id, str(edp.date))] = edp

        all_permissions = self.env['hr.attendance.permission'].search([
            ('employee_id', 'in', emp_ids),
            ('date', '>=', first_day),
            ('date', '<=', last_day),
            ('state', '=', 'approved'),
        ])
        permission_by_emp = {}
        for perm in all_permissions:
            permission_by_emp.setdefault(perm.employee_id.id, []).append(str(perm.date))

        matrix = {}
        consolidation = {}

        for emp in employees:
            emp_row = {}
            is_rotational = (emp.shift_type == 'rotational')
            emp_shifts = shift_slots_by_emp.get(emp.id, {})
            emp_weekoffs = weekoff_days_by_emp.get(emp.id, set())

            c_working_days = 0
            c_present_full = 0
            c_present_half = 0
            c_absent = 0
            c_ot_hours = 0.0
            c_ot_days = 0
            c_edp_days = 0
            c_comp_off_used = 0.0
            c_ph_worked = 0

            for day_key in day_list:
                codes = []
                detail = {}

                is_weekoff = day_key in emp_weekoffs
                is_public_holiday = day_key in public_holiday_map

                if is_public_holiday:
                    detail['is_public_holiday'] = True
                    detail['holiday_name'] = public_holiday_map[day_key]

                day_atts = att_lookup.get((emp.id, day_key), [])
                has_checkin = bool(day_atts)
                has_checkout = any(a.check_out for a in day_atts)
                leave_info = leave_lookup.get((emp.id, day_key))

                actual_duration = 0.0
                for a in day_atts:
                    if a.check_in and a.check_out:
                        actual_duration += (a.check_out - a.check_in).total_seconds() / 3600.0

                if is_public_holiday or is_weekoff:
                    daily_worked_hrs = actual_duration
                else:
                    daily_worked_hrs = sum(a.worked_hours_custom or 0.0 for a in day_atts)

                daily_perm_hrs = sum(a.permission_credit_applied or 0.0 for a in day_atts)
                effective_hrs = daily_worked_hrs + daily_perm_hrs

                raw_ot = sum(a.approved_extra_hours or 0.0 for a in day_atts)
                capped_ot = min(raw_ot, 4.0)

                shift_name = emp_shifts.get(day_key) if is_rotational else None

                if shift_name and not has_checkin:
                    codes.append(f'SH:{shift_name}')
                    detail['shift_name'] = shift_name
                    detail['shift_status'] = 'planned'
                elif has_checkin and not has_checkout:
                    codes.append('CHK')
                    if shift_name:
                        detail['shift_name'] = shift_name
                    detail['shift_status'] = 'in_progress'
                elif has_checkin and has_checkout:
                    rep_att = max(day_atts, key=lambda a: a.check_in)

                    if effective_hrs >= 8.0:
                        codes.append('P')
                        detail['absence_status'] = 'full_present'
                    elif effective_hrs >= 4.0:
                        codes.append('P/A')
                        detail['absence_status'] = 'half_absent'
                        detail['half_day_type'] = getattr(rep_att, 'half_day_type', 'second') or 'second'
                    elif not is_public_holiday and not is_weekoff:
                        codes.append('AB')
                        detail['absence_status'] = 'full_absent'

                    if shift_name:
                        detail['shift_name'] = shift_name
                    detail['shift_status'] = 'done'

                if has_checkout and not is_public_holiday:
                    if effective_hrs > 0 and capped_ot > 0:
                        codes.append('OT')
                        c_ot_hours += capped_ot

                        if capped_ot >= 4.0:
                            c_ot_days += 1

                if is_public_holiday:
                    codes.append('HO')

                if is_weekoff and not codes:
                    codes.append('WO')

                if leave_info:
                    sc = leave_info['short_code']
                    is_half = leave_info['half_day']
                    is_draft_leave = leave_info['draft']
                    is_comp = leave_info['is_compoff']

                    if 'AB' in codes and not is_half:
                        codes.remove('AB')

                    if is_half and has_checkin:
                        badge = f'LV:P/{sc}'
                        codes = [c for c in codes if c not in ('P', 'P/A', 'AB')]
                    elif is_half:
                        badge = f'LV:{sc}½'
                    else:
                        badge = f'LV:{sc}'

                    if is_draft_leave:
                        badge = badge + ':DRAFT'

                    codes.append(badge)

                    if is_comp:
                        c_comp_off_used += 0.5 if is_half else 1.0

                    detail['leave_type'] = leave_info['name']
                    detail['leave_code'] = sc
                    detail['leave_half_day'] = is_half
                    detail['leave_draft'] = is_draft_leave

                if is_public_holiday and has_checkin:
                    if actual_duration >= 6.0:
                        self._grant_compensatory_off(emp, day_key)
                        detail['comp_off_granted'] = True
                    c_ph_worked += 1

                if has_checkin:
                    if daily_perm_hrs > 0:
                        detail['permission_credit'] = round(daily_perm_hrs, 2)

                    rep_att = max(day_atts, key=lambda a: a.check_in) if day_atts else None
                    base_sched = getattr(rep_att, 'base_scheduled_hours', 8.0) if rep_att else 8.0

                    detail['daily_total_hours'] = round(effective_hrs, 2)
                    detail['base_scheduled_hours'] = round(base_sched or 8.0, 2)

                if day_atts:
                    punches = []
                    for a in sorted(day_atts, key=lambda x: x.check_in):
                        if is_public_holiday or is_weekoff:
                            worked = (
                                             a.check_out - a.check_in).total_seconds() / 3600.0 if a.check_in and a.check_out else 0.0
                        else:
                            worked = a.worked_hours_custom or 0.0

                        punches.append({
                            'check_in': _ist_hhmm(a.check_in),
                            'check_out': _ist_hhmm(a.check_out) if a.check_out else '-',
                            'worked_hours': round(worked, 2),
                            'extra_hours': round(a.extra_hours or 0.0, 2),
                            'approved_extra_hours': round(a.approved_extra_hours or 0.0, 2),
                            'permission_credit': round(a.permission_credit_applied or 0.0, 2),
                        })
                    detail['punches'] = punches
                    detail['total_worked_hours'] = round(daily_worked_hrs, 2)
                    detail['total_ot_hours'] = round(capped_ot, 2)
                    detail['total_payable_hours'] = round(min(effective_hrs + capped_ot, 12.0), 2)

                edp = edp_lookup.get((emp.id, day_key))
                if edp and has_checkout:
                    codes.append('EDP')
                    detail['edp'] = {'shift_template': edp.calendar_id.name if edp.calendar_id else '',
                                     'state': edp.state}
                    c_edp_days += 1

                if not codes and not is_weekoff and not is_public_holiday and day_key <= today_str:
                    codes.append('AB')
                    detail['absence_status'] = 'full_absent'

                # ── WYSIWYG COUNTERS ──
                if not is_weekoff and not is_public_holiday:
                    c_working_days += 1

                    if 'P' in codes:
                        c_present_full += 1

                    if 'P/A' in codes:
                        c_present_half += 1

                    for c in codes:
                        # Ensures Comp Off visually reads 'CO' but counts mathematically as 'Present'
                        if c == 'LV:CO':
                            c_present_full += 1
                        elif c == 'LV:CO½':
                            c_present_half += 1
                        elif c.startswith('LV:P/'):
                            c_present_half += 1
                            if 'CO' in c:
                                c_present_half += 1

                    if 'AB' in codes:
                        c_absent += 1

                emp_row[day_key] = {'codes': codes, 'detail': detail}

            matrix[emp.id] = emp_row

            emp_leave_counts = leave_counts_by_emp.get(emp.id, {})
            c_permissions = len(permission_by_emp.get(emp.id, []))

            c_leave_total = sum(v for k, v in emp_leave_counts.items() if k not in ('LOP', 'CO'))
            c_comp_off_used_total = emp_leave_counts.get('CO', 0.0)

            leave_breakup = {k: v for k, v in emp_leave_counts.items() if v > 0}
            leave_counts_full = {code: emp_leave_counts.get(code, 0.0) for code in all_leave_codes}

            consolidation[emp.id] = {
                'calendar_days': days_in_month,
                'working_days': c_working_days,
                'present_full': c_present_full,
                'present_half': c_present_half,
                'absent': c_absent,
                'leave_total': c_leave_total,
                'leave_breakup': leave_breakup,
                'leave_counts_full': leave_counts_full,
                'ot_hours': round(c_ot_hours, 2),
                'ot_days': c_ot_days,
                'ot_hours_fmt': _fmt_hours(c_ot_hours),
                'permissions_used': c_permissions,
                'edp_days': c_edp_days,
                'comp_off_used': c_comp_off_used_total,
                'ph_worked': c_ph_worked,
                'effective_present': round(c_present_full + c_present_half * 0.5, 1),
            }

        return {
            'employees': [{
                'id': e.id,
                'name': e.name,
                'shift_type': e.shift_type or 'regular',
                'ls_employee_id': getattr(e, 'ls_employee_id', '') or '',
                'work_email': e.work_email or '',
                'parent_id': e.parent_id.name if e.parent_id else '',
                'department_id': e.department_id.name if e.department_id else '',
                'job_id': e.job_id.name if e.job_id else '',
            } for e in employees],
            'days': day_list,
            'matrix': matrix,
            'consolidation': consolidation,
            'weekoff_days_by_emp': {str(eid): list(wo) for eid, wo in weekoff_days_by_emp.items()},
            'public_holidays': public_holiday_map,
            'leave_type_colors': leave_type_colors,
            'all_leave_codes': all_leave_codes,
        }