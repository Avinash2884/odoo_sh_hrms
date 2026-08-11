/** @odoo-module **/

import { Component, useState, onWillStart, useExternalListener, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";

// ─── Day-detail popup ─────────────────────────────────────────────────────────
class AttendanceDayDetailDialog extends Component {
    static template = "attendance_planning.AttendanceDayDetailDialog";
    static components = { Dialog };
    static props = ["close", "employeeName", "day", "codes", "detail"];
}

// ─── Main grid component ──────────────────────────────────────────────────────
export class AttendanceMatrixReport extends Component {
    static template = "attendance_planning.AttendanceMatrixReport";

    setup() {
        this.orm    = useService("orm");
        this.dialog = useService("dialog");

        const today = new Date();
        this.state = useState({
            year:             today.getFullYear(),
            month:            today.getMonth() + 1,   // 1-12
            employees:        [],
            days:             [],
            matrix:           {},
            weekoffByEmp:     {},   // { empId(str) : Set<'YYYY-MM-DD'> }
            loading:          true,
            shiftFilter:      'all',   // 'all' | 'regular' | 'rotational'
            codeFilter:       'all',   // 'all' | 'A' | 'OT' | 'EDP'
            searchText:       '',      // employee name search
            filtersOpen:      false,   // dropdown panel toggle
            groupBy:          null,    // null | 'shift_type'
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

    // ── Data fetch ────────────────────────────────────────────────────────────
    async loadData() {
        this.state.loading = true;
        const result = await this.orm.call(
            "attendance.matrix.report",
            "get_matrix_data",
            [this.state.year, this.state.month],
        );

        this.state.employees    = result.employees;
        this.state.days         = result.days;
        this.state.matrix       = result.matrix;

        // Convert lists → Sets for O(1) lookup
        const byEmp = {};
        for (const [empIdStr, days] of Object.entries(result.weekoff_days_by_emp || {})) {
            byEmp[empIdStr] = new Set(days);
        }
        this.state.weekoffByEmp = byEmp;
        this.state.loading      = false;
    }

    // ── Navigation ────────────────────────────────────────────────────────────
    get monthLabel() {
        const d = new Date(this.state.year, this.state.month - 1, 1);
        return d.toLocaleDateString(undefined, { month: "long", year: "numeric" });
    }

    prevMonth() {
        if (--this.state.month < 1) { this.state.month = 12; this.state.year--; }
        this.loadData();
    }
    nextMonth() {
        if (++this.state.month > 12) { this.state.month = 1; this.state.year++; }
        this.loadData();
    }
    goToday() {
        const t = new Date();
        this.state.year  = t.getFullYear();
        this.state.month = t.getMonth() + 1;
        this.loadData();
    }

    // ── Cell helpers ──────────────────────────────────────────────────────────
    dayNumber(dayKey) { return parseInt(dayKey.split("-")[2], 10); }

    dayLabel(dayKey) {
        // New Date with explicit time avoids off-by-one from timezone
        return new Date(dayKey + "T00:00:00")
            .toLocaleDateString("en-IN", { weekday: "short" });
    }

    isToday(dayKey) {
        return dayKey === new Date().toISOString().slice(0, 10);
    }

    // ── Filters ────────────────────────────────────────────────────────────────
    setShiftFilter(value) {
        this.state.shiftFilter = value;
    }
    setCodeFilter(value) {
        this.state.codeFilter = value;
    }
    setSearchText(ev) {
        this.state.searchText = ev.target.value;
    }
    toggleFilters() {
        this.state.filtersOpen = !this.state.filtersOpen;
    }
    setGroupBy(value) {
        // clicking the already-active option turns grouping off again
        this.state.groupBy = (this.state.groupBy === value) ? null : value;
    }

    /** Chips shown inside the search bar — each one removable */
    get chips() {
        const chips = [];
        if (this.state.searchText.trim()) {
            chips.push({ key: 'search', icon: 'fa-search', label: this.state.searchText });
        }
        if (this.state.shiftFilter !== 'all') {
            chips.push({
                key: 'shift', icon: 'fa-filter',
                label: this.state.shiftFilter === 'regular' ? 'Regular' : 'Rotational',
            });
        }
        if (this.state.codeFilter !== 'all') {
            chips.push({ key: 'code', icon: 'fa-filter', label: this.state.codeFilter });
        }
        if (this.state.groupBy === 'shift_type') {
            chips.push({ key: 'group', icon: 'fa-th-large', label: 'Group By: Shift Type' });
        }
        return chips;
    }

    removeChip(key) {
        if (key === 'search') this.state.searchText = '';
        if (key === 'shift') this.state.shiftFilter = 'all';
        if (key === 'code') this.state.codeFilter = 'all';
        if (key === 'group') this.state.groupBy = null;
    }

    /** Employees after shift-type + name-search filters (flat list, pre-grouping) */
    get baseFilteredEmployees() {
        let list = this.state.employees;
        if (this.state.shiftFilter !== 'all') {
            list = list.filter((e) => (e.shift_type || 'regular') === this.state.shiftFilter);
        }
        const q = this.state.searchText.trim().toLowerCase();
        if (q) {
            list = list.filter((e) => e.name.toLowerCase().includes(q));
        }
        return list;
    }

    /** Flat list, used when no Group By is active */
    get filteredEmployees() {
        return this.baseFilteredEmployees;
    }

    /** [{ key, label, employees: [...] }] used when Group By is active */
    get groupedEmployees() {
        const list = this.baseFilteredEmployees;
        if (this.state.groupBy !== 'shift_type') return null;

        const regular = list.filter((e) => (e.shift_type || 'regular') === 'regular');
        const rotational = list.filter((e) => e.shift_type === 'rotational');
        const groups = [];
        if (regular.length) groups.push({ key: 'regular', label: 'Regular', employees: regular });
        if (rotational.length) groups.push({ key: 'rotational', label: 'Rotational', employees: rotational });
        return groups;
    }

    /** Is this day a week-off for this specific employee? */
    isWeekoff(empId, dayKey) {
        const s = this.state.weekoffByEmp[String(empId)];
        return s ? s.has(dayKey) : false;
    }

    cellCodes(empId, dayKey) {
        const row = this.state.matrix[empId];
        const codes = (row && row[dayKey]) ? row[dayKey].codes : [];
        if (this.state.codeFilter === 'all') return codes;
        return codes.filter((c) => c === this.state.codeFilter);
    }

    /** CSS classes for a header <th> */
    headerCellClass(dayKey) {
        const cls = ["text-center", "o_amc_day_col"];
        if (this.isToday(dayKey)) cls.push("o_amc_today_header");
        return cls.join(" ");
    }

    /** CSS classes for a data <td> — weekoff is per employee */
    dataCellClass(empId, dayKey) {
        const codes = this.cellCodes(empId, dayKey);
        const cls   = ["text-center", "o_attendance_matrix_cell"];
        if (this.isWeekoff(empId, dayKey)) cls.push("o_amc_weekoff_cell");
        if (codes.length)                  cls.push("o_amc_filled");
        if (this.isToday(dayKey))          cls.push("o_amc_today_cell");
        return cls.join(" ");
    }

    // ── Click handler ─────────────────────────────────────────────────────────
    onCellClick(empId, empName, dayKey) {
        const row   = this.state.matrix[empId];
        const cell  = row ? row[dayKey] : null;
        const codes = cell ? cell.codes : [];
        if (!codes.length) return;

        this.dialog.add(AttendanceDayDetailDialog, {
            employeeName: empName,
            day:          dayKey,
            codes:        codes,
            detail:       cell.detail,
        });
    }
}

registry.category("actions").add("attendance_matrix_report_action", AttendanceMatrixReport);