/** @odoo-module **/

import { registry } from "@web/core/registry";

const planningHolidayService = {
    dependencies: ["orm"],

    async start(env, { orm }) {
        let holidayMap = {};

        async function loadHolidays() {
            try {
                const result = await orm.call(
                    "planning.slot",
                    "get_public_holidays_for_calendar",
                    []
                );
                holidayMap = {};
                (result || []).forEach(h => {
                    holidayMap[h.date] = h.name;
                });
            } catch (e) {
                console.error("[Holiday] Failed to load:", e);
            }
        }

        function applyHighlights() {
            if (!document.querySelector('.fc-daygrid-body')) return;

            Object.entries(holidayMap).forEach(([date, name]) => {
                // Exact selector as recommended — avoids 7-day offset bug
                const cell = document.querySelector(
                    `td.fc-daygrid-day[data-date="${date}"]`
                );

                if (cell && !cell.classList.contains('o_public_holiday_cell')) {
                    cell.classList.add('o_public_holiday_cell');

                    // Append inside frame, not td directly
                    const frame = cell.querySelector('.fc-daygrid-day-frame');
                    if (frame && !frame.querySelector('.o_holiday_badge')) {
                        const badge = document.createElement('div');
                        badge.className = 'o_holiday_badge';
                        badge.textContent = name;
                        badge.title = name;
                        frame.appendChild(badge);
                    }
                }
            });
        }

        function startObserver() {
            const observer = new MutationObserver(() => {
                clearTimeout(window._holidayTimer);
                window._holidayTimer = setTimeout(applyHighlights, 300);
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true,
            });
        }

        await loadHolidays();
        startObserver();
    },
};

registry.category("services").add("planning_holiday_highlight", planningHolidayService);