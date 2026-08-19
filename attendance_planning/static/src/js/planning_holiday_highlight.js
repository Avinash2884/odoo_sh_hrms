/** @odoo-module **/

import { registry } from "@web/core/registry";

console.log("[Holiday] planning_holiday_highlight.js loaded ✅");

const planningHolidayService = {
    dependencies: ["orm"],

    async start(env, { orm }) {
        console.log("[Holiday] Service starting...");

        let holidayMap = {};

        async function loadHolidays() {
            console.log("[Holiday] Loading public holidays from server...");
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
                console.log("[Holiday] Loaded holidays:", holidayMap);
            } catch (e) {
                console.error("[Holiday] Failed to load holidays:", e);
            }
        }

        function applyHighlights() {
            // Remove previous
            document.querySelectorAll(".o_public_holiday_cell").forEach(el => {
                el.classList.remove("o_public_holiday_cell");
            });
            document.querySelectorAll(".o_holiday_badge").forEach(el => el.remove());

            if (!Object.keys(holidayMap).length) {
                console.warn("[Holiday] No holidays in map, skipping highlight.");
                return;
            }

            // Try all possible FullCalendar cell selectors
            const cells = document.querySelectorAll(
                ".fc-daygrid-day[data-date], .fc-day[data-date], td[data-date]"
            );

            console.log("[Holiday] Found", cells.length, "calendar day cells in DOM");

            cells.forEach(cell => {
                const date = cell.getAttribute("data-date");
                if (date && holidayMap[date]) {
                    console.log("[Holiday] Highlighting:", date, "→", holidayMap[date]);
                    cell.classList.add("o_public_holiday_cell");
                    if (!cell.querySelector(".o_holiday_badge")) {
                        const badge = document.createElement("div");
                        badge.className = "o_holiday_badge";
                        badge.textContent = holidayMap[date];
                        badge.title = holidayMap[date];
                        cell.appendChild(badge);
                    }
                }
            });
        }

        function startObserver() {
            console.log("[Holiday] Starting MutationObserver...");
            const observer = new MutationObserver(() => {
                clearTimeout(window._holidayTimer);
                window._holidayTimer = setTimeout(() => {
                    // Only apply if calendar cells exist in DOM
                    const hasCells = document.querySelector(
                        ".fc-daygrid-day[data-date], .fc-day[data-date], td[data-date]"
                    );
                    if (hasCells) applyHighlights();
                }, 200);
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true,
            });

            console.log("[Holiday] MutationObserver started ✅");
        }

        // Boot
        await loadHolidays();
        startObserver();

        console.log("[Holiday] Service ready ✅");
    },
};

registry.category("services").add("planning_holiday_highlight", planningHolidayService);