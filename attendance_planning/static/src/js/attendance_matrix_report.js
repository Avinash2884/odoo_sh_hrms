/** @odoo-module **/

import { Component, useState, onWillStart, useExternalListener, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";

// ── Badge code sets ────────────────────────────────────────────────────────────
// SH: = shift name prefix (rotational planned)
// LV: = leave prefix
// :DRAFT suffix = pending leave
const FIXED_CODES = new Set(['P', 'P/A', 'AB', 'CHK', 'OT', 'EDP', 'HO', 'WO']);

const KNOWN_LEAVE_CODES = {
    'Privilege Leave': 'PL', 'Sick Leave': 'SL', 'Casual Leave': 'CL',
    'Bereavement Leave': 'BL', 'Maternity Leave': 'ML',
    'Paternity Leave': 'PTL', 'Wedding Leave': 'WL',
    'Unpaid(LOP)': 'LOP', 'Loss of Pay': 'LOP',
    'Compensatory Days': 'CO', 'Compensatory Off': 'CO',
    'Extra Time Off': 'ETO', 'Sick Leave - Probation': 'SLP',
    'Casual Leave - Probation': 'CLP',
};

// ─── Day-detail popup ──────────────────────────────────────────────────────────
class AttendanceDayDetailDialog extends Component {
    static template = "attendance_planning.AttendanceDayDetailDialog";
    static components = { Dialog };
    static props = ["close", "employeeName", "day", "codes", "detail", "badgeClass", "leaveBadgeStyle", "displayCode"];
}

// ─── Main grid component ───────────────────────────────────────────────────────
export class AttendanceMatrixReport extends Component {
    static template = "attendance_planning.AttendanceMatrixReport";

    setup() {
        this.orm    = useService("orm");
        this.dialog = useService("dialog");

        const today = new Date();
        this.state = useState({
            year:            today.getFullYear(),
            month:           today.getMonth() + 1,
            employees:       [],
            days:            [],
            matrix:          {},
            consolidation:   {},
            weekoffByEmp:    {},
            publicHolidays:  {},
            leaveTypeColors: {},
            allLeaveCodes:   [],
            loading:         true,
            shiftFilter:     'all',
            codeFilter:      'all',
            searchText:      '',
            filtersOpen:     false,
            groupBy:         null,
        });

        onWillStart(() => this.loadData());

        this.filterRootRef = useRef("filterRoot");
        useExternalListener(window, "click", (ev) => {
            if (this.state.filtersOpen && this.filterRootRef.el &&
                !this.filterRootRef.el.contains(ev.target)) {
                this.state.filtersOpen = false;
            }
        });
    }

    // ── Data fetch ─────────────────────────────────────────────────────────────
    async loadData() {
        this.state.loading = true;
        const result = await this.orm.call(
            "attendance.matrix.report", "get_matrix_data",
            [this.state.year, this.state.month],
        );
        this.state.employees      = result.employees;
        this.state.days           = result.days;
        this.state.matrix         = result.matrix;
        this.state.consolidation  = result.consolidation || {};
        this.state.publicHolidays = result.public_holidays || {};
        this.state.leaveTypeColors = result.leave_type_colors || {};
        this.state.allLeaveCodes  = result.all_leave_codes || [];

        const byEmp = {};
        for (const [idStr, days] of Object.entries(result.weekoff_days_by_emp || {})) {
            byEmp[idStr] = new Set(days);
        }
        this.state.weekoffByEmp = byEmp;
        this.state.loading = false;
    }

    // ── Navigation ─────────────────────────────────────────────────────────────
    get monthLabel() {
        return new Date(this.state.year, this.state.month - 1, 1)
            .toLocaleDateString(undefined, { month: "long", year: "numeric" });
    }
    prevMonth() {
        if (--this.state.month < 1)  { this.state.month = 12; this.state.year--; }
        this.loadData();
    }
    nextMonth() {
        if (++this.state.month > 12) { this.state.month = 1;  this.state.year++; }
        this.loadData();
    }
    goToday() {
        const t = new Date();
        this.state.year  = t.getFullYear();
        this.state.month = t.getMonth() + 1;
        this.loadData();
    }

    // ── Filters ────────────────────────────────────────────────────────────────
    setShiftFilter(v) { this.state.shiftFilter = v; }
    setCodeFilter(v)  { this.state.codeFilter  = v; }
    setSearchText(ev) { this.state.searchText  = ev.target.value; }
    toggleFilters()   { this.state.filtersOpen = !this.state.filtersOpen; }
    setGroupBy(v)     { this.state.groupBy = (this.state.groupBy === v) ? null : v; }

    get chips() {
        const chips = [];
        if (this.state.searchText.trim())
            chips.push({ key: 'search', icon: 'fa-search', label: this.state.searchText });
        if (this.state.shiftFilter !== 'all')
            chips.push({ key: 'shift', icon: 'fa-filter',
                label: this.state.shiftFilter === 'regular' ? 'Regular' : 'Rotational' });
        if (this.state.codeFilter !== 'all')
            chips.push({ key: 'code', icon: 'fa-filter', label: this.state.codeFilter });
        if (this.state.groupBy === 'shift_type')
            chips.push({ key: 'group', icon: 'fa-th-large', label: 'Group By: Shift Type' });
        return chips;
    }

    removeChip(key) {
        if (key === 'search') this.state.searchText  = '';
        if (key === 'shift')  this.state.shiftFilter = 'all';
        if (key === 'code')   this.state.codeFilter  = 'all';
        if (key === 'group')  this.state.groupBy     = null;
    }

    // ── Update: Multi-field Search Filter ──────────────────────────────────────
    get baseFilteredEmployees() {
        let list = this.state.employees;
        if (this.state.shiftFilter !== 'all') {
            list = list.filter(e => (e.shift_type || 'regular') === this.state.shiftFilter);
        }

        const q = this.state.searchText.trim().toLowerCase();
        if (q) {
            list = list.filter(e =>
                (e.name || '').toLowerCase().includes(q) ||
                (e.ls_employee_id || '').toLowerCase().includes(q) ||
                (e.work_email || '').toLowerCase().includes(q) ||
                (e.parent_id || '').toLowerCase().includes(q) ||
                (e.department_id || '').toLowerCase().includes(q) ||
                (e.job_id || '').toLowerCase().includes(q)
            );
        }
        return list;
    }

    get filteredEmployees() { return this.baseFilteredEmployees; }

    get groupedEmployees() {
        if (this.state.groupBy !== 'shift_type') return null;
        const list = this.baseFilteredEmployees;
        const regular    = list.filter(e => (e.shift_type || 'regular') === 'regular');
        const rotational = list.filter(e => e.shift_type === 'rotational');
        const groups = [];
        if (regular.length)    groups.push({ key: 'regular',    label: 'Regular',    employees: regular });
        if (rotational.length) groups.push({ key: 'rotational', label: 'Rotational', employees: rotational });
        return groups;
    }

    // ── Consolidation helper ───────────────────────────────────────────────────
    getConsolidation(empId) {
        return this.state.consolidation[empId] || {
            calendar_days: 0, working_days: 0, effective_present: 0,
            ot_hours_fmt: '0:00', ot_days: 0, edp_days: 0, ph_worked: 0, // <-- ADDED ot_days: 0 fallback
            leave_counts_full: {},
        };
    }

    /** Count for one leave short code for this employee — 0 if never taken. */
    leaveCountFor(empId, code) {
        const cons = this.getConsolidation(empId);
        const val = cons.leave_counts_full ? cons.leave_counts_full[code] : undefined;
        return val === undefined ? 0 : val;
    }

    // ── Cell helpers ───────────────────────────────────────────────────────────
    dayNumber(dayKey) { return parseInt(dayKey.split("-")[2], 10); }
    dayLabel(dayKey) {
        return new Date(dayKey + "T00:00:00")
            .toLocaleDateString("en-IN", { weekday: "short" });
    }
    isToday(dayKey)  { return dayKey === new Date().toISOString().slice(0, 10); }
    isWeekoff(empId, dayKey) {
        const s = this.state.weekoffByEmp[String(empId)];
        return s ? s.has(dayKey) : false;
    }
    isPublicHoliday(dayKey) { return !!this.state.publicHolidays[dayKey]; }
    holidayName(dayKey)     { return this.state.publicHolidays[dayKey] || ''; }

    cellCodes(empId, dayKey) {
        const row   = this.state.matrix[empId];
        const codes = (row && row[dayKey]) ? row[dayKey].codes : [];
        if (this.state.codeFilter === 'all') return codes;
        return codes.filter(c => {
            const base = c.replace(':DRAFT', '');
            return base === this.state.codeFilter ||
                   base.startsWith(this.state.codeFilter);
        });
    }

    // ── Badge classification ───────────────────────────────────────────────────
    isDraft(code)       { return code.endsWith(':DRAFT'); }
    isLeave(code)       { return code.startsWith('LV:'); }
    isShiftName(code)   { return code.startsWith('SH:'); }
    isCombined(code)    { return code.startsWith('LV:P/'); }

    _cleanCode(code)    { return code.replace(':DRAFT', '').replace('LV:', '').replace('SH:', ''); }

    /**
     * Returns the CSS class string for any badge code.
     * Handles: P, P/A, AB, CHK, OT, EDP, HO, WO
     *          SH:shiftname  → shift name style
     *          LV:SL, LV:SL½, LV:P/SL → leave badge (color inline)
     *          any :DRAFT suffix → adds o_amc_draft pattern
     */
    badgeClass(code) {
        const isDraft = this.isDraft(code);
        const base    = code.replace(':DRAFT', '');
        let cls = 'o_amc_badge';

        if (base.startsWith('SH:'))   cls += ' o_amc_shift_name';
        else if (base.startsWith('LV:')) cls += ' o_amc_leave_badge';
        else if (FIXED_CODES.has(base))  cls += ` o_amc_${base.replace('/', '_')}`;
        else                             cls += ' o_amc_shift_name';

        if (isDraft) cls += ' o_amc_draft';
        return cls;
    }

    leaveBadgeStyle(code) {
        const base = code.replace(':DRAFT', '');
        if (!base.startsWith('LV:')) return '';
        const inner = base.replace('LV:', '');
        // combined P/SL → get SL part
        const shortCode = inner.startsWith('P/')
            ? inner.slice(2).split('½')[0]
            : inner.split('½')[0].trim();
        const colors = this.state.leaveTypeColors;
        for (const [name, color] of Object.entries(colors)) {
            if (this._matchesShortCode(name, shortCode)) {
                const alpha = code.endsWith(':DRAFT') ? '99' : '';
                return `background-color:${color}${alpha};color:#fff;border-color:${color}`;
            }
        }
        return 'background-color:#64748b;color:#fff';
    }

    _matchesShortCode(leaveTypeName, shortCode) {
        if (KNOWN_LEAVE_CODES[leaveTypeName])
            return KNOWN_LEAVE_CODES[leaveTypeName] === shortCode;
        const words = leaveTypeName.trim().split(' ');
        const auto  = words.length >= 2
            ? words.slice(0, 4).map(w => w[0].toUpperCase()).join('')
            : leaveTypeName.slice(0, 4).toUpperCase();
        return auto === shortCode;
    }

    leaveShortCodeForName(name) {
        if (KNOWN_LEAVE_CODES[name]) return KNOWN_LEAVE_CODES[name];
        const words = name.trim().split(' ');
        return words.length >= 2
            ? words.slice(0, 4).map(w => w[0].toUpperCase()).join('')
            : name.slice(0, 4).toUpperCase();
    }

    // Display clean text inside the badge (No question marks!)
    displayCode(code) {
        const base = code.replace(':DRAFT', '');
        let text = base;
        if (base.startsWith('SH:')) text = base.slice(3);
        else if (base.startsWith('LV:')) text = base.slice(3);

        // Just return the exact short code (e.g., SL, PTO). The CSS stripes will handle the draft look.
        return text;
    }

    // ── Cell class ─────────────────────────────────────────────────────────────
    headerCellClass(dayKey) {
        const cls = ["text-center", "o_amc_day_col"];
        if (this.isToday(dayKey))       cls.push("o_amc_today_header");
        if (this.isPublicHoliday(dayKey)) cls.push("o_amc_ph_header");
        return cls.join(" ");
    }

    dataCellClass(empId, dayKey) {
        const codes = this.cellCodes(empId, dayKey);
        const cls   = ["text-center", "o_attendance_matrix_cell"];
        if (this.isWeekoff(empId, dayKey))  cls.push("o_amc_weekoff_cell");
        if (codes.length)                   cls.push("o_amc_filled");
        if (this.isToday(dayKey))           cls.push("o_amc_today_cell");
        const baseCodes = codes.map(c => c.replace(':DRAFT', ''));
        if (baseCodes.includes('AB'))       cls.push("o_amc_abs_cell");
        if (baseCodes.includes('P/A'))      cls.push("o_amc_half_cell");
        return cls.join(" ");
    }

    // ── Click → popup ──────────────────────────────────────────────────────────
    onCellClick(empId, empName, dayKey) {
        const row  = this.state.matrix[empId];
        const cell = row ? row[dayKey] : null;
        if (!cell || !cell.codes.length) return;
        this.dialog.add(AttendanceDayDetailDialog, {
            employeeName: empName,
            day:          dayKey,
            codes:        cell.codes,
            detail:       cell.detail,
            badgeClass:   (c) => this.badgeClass(c),
            leaveBadgeStyle: (c) => this.leaveBadgeStyle(c),
            displayCode:  (c) => this.displayCode(c),
        });
    }
}

registry.category("actions").add("attendance_matrix_report_action", AttendanceMatrixReport);