/** @odoo-module **/

import { Component, onWillStart, onMounted, useState, useRef } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class RecruitmentDashboard extends Component {

    setup() {
        this.action = useService("action");
        this.state = useState({
            total_applicants: 0,
            total_jobs: 0,
            total_offers: 0,
            refused_count: 0,
            job_summary: [],
            from_date: null,
            to_date: null,
            stage_pie_data: [],
            jobs: [],                // ✅ ADD THIS
            selected_job_id: null
        });

        this.jobPieChart = useRef("jobPieChart");
        this.stagePieChart = useRef("stagePieChart");
        this.openApplicants = this.openApplicants.bind(this);
        this.openJobs = this.openJobs.bind(this);
        this.openOffers = this.openOffers.bind(this);
        this.openRefused = this.openRefused.bind(this);
        this.applyFilter = this.applyFilter.bind(this);
        this.onJobChange = this.onJobChange.bind(this);
        this.chartInstance = null;

        onWillStart(async () => {
            this.state.from_date = sessionStorage.getItem("from_date");
            this.state.to_date = sessionStorage.getItem("to_date");

            await this.loadDashboardData();
            await this.loadJobs();
            await this.loadStagePieData();
        });

       onMounted(() => {
            this.renderCharts();
            this.renderStagePie();   // ✅ ADD THIS
        });
    }
    generateColors(count) {
        const colors = [];

        for (let i = 0; i < count; i++) {
            const hue = Math.floor((360 / count) * i);

            const saturation = 60;   // less strong
            const lightness = 75;

            colors.push(`hsl(${hue}, ${saturation}%, ${lightness}%)`);
        }

        return colors;
    }
    async loadJobs() {
        const jobs = await rpc("/web/dataset/call_kw/hr.job/search_read", {
            model: "hr.job",
            method: "search_read",
            args: [[], ["id", "name", "department_id"]],
            kwargs: {},
        });

        this.state.jobs = jobs.map(job => {
            return {
                id: job.id,
                name: job.name,
                department: job.department_id ? job.department_id[1] : ""
            };
        });
    }

    async onJobChange(ev) {
        this.state.selected_job_id = parseInt(ev.target.value) || null;
        await this.loadStagePieData();
    }
    openApplicants() {
        const domain = [];

        if (this.state.from_date) {
            domain.push(["create_date", ">=", this.state.from_date]);
        }

        if (this.state.to_date) {
            domain.push(["create_date", "<=", this.state.to_date]);
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Applicants",
            res_model: "hr.applicant",
            views: [[false, "list"], [false, "form"]],
            domain: domain,   // ✅ THIS FIXES YOUR ISSUE
            target: "current"
        });
    }

    openJobs() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Jobs",
            res_model: "hr.job",
            views: [[false, "list"], [false, "form"]],
            target: "current"
        });
    }

    openOffers() {
        const domain = [];

        if (this.state.from_date) {
            domain.push(["create_date", ">=", this.state.from_date]);
        }

        if (this.state.to_date) {
            domain.push(["create_date", "<=", this.state.to_date]);
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Offers",
            res_model: "hr.contract.salary.offer",  // ✅ FIX
            views: [[false, "list"], [false, "form"]],
            domain: domain,
            target: "current"
        });
    }

    openRefused() {
        const domain = [
            ["active", "=", false],
            ["refuse_reason_id", "!=", false]
        ];

        if (this.state.from_date) {
            domain.push(["create_date", ">=", this.state.from_date]);
        }

        if (this.state.to_date) {
            domain.push(["create_date", "<=", this.state.to_date + " 23:59:59"]);
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Refused",
            res_model: "hr.applicant",
            views: [[false, "list"], [false, "form"]],
            domain: domain,
            target: "current"
        });
    }

    async loadStagePieData() {
        const data = await rpc("/recruitment/stage_pie", {
            job_id: this.state.selected_job_id,
        });

        this.state.stage_pie_data = data;

        setTimeout(() => {
            this.renderStagePie();
        }, 0);
    }
    renderStagePie() {

        const el = this.stagePieChart.el;

        if (!el || !this.state.stage_pie_data || !this.state.stage_pie_data.length) {
            console.warn("No stage pie data");
            return;
        }

        if (this.stageChartInstance) {
            this.stageChartInstance.destroy();
        }

        const labels = [];
        const values = [];

        this.state.stage_pie_data.forEach(s => {
            labels.push(s.stage_name);
            values.push(s.count);
        });

        // ✅ ADD COLORS HERE
        const colors = this.generateColors(labels.length);

        this.stageChartInstance = new Chart(el, {
            type: "pie",
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,   // ✅ IMPORTANT
                }],
            },
            options: {
                plugins: {
                    legend: {
                        position: "bottom"
                    }
                }
            }
        });
    }

    async loadDashboardData() {
        try {
            const data = await rpc("/recruitment/summary", {
                from_date: this.state.from_date,
                to_date: this.state.to_date,
            });

            if (data.error) {
                console.error("Server Error:", data.error);
                return;
            }

            // Assign all backend values
            this.state.total_applicants = data.total_applicants ?? 0;
            this.state.total_jobs = data.total_jobs ?? 0;
            this.state.total_offers = data.total_offers ?? 0;
            this.state.refused_count = data.refused_count ?? 0;
            this.state.job_summary = data.job_summary ?? [];

            console.log("Recruitment Summary Loaded:", this.state);

        } catch (error) {
            console.error("RPC Error:", error);
        }
    }

    async applyFilter() {

        sessionStorage.setItem("from_date", this.state.from_date || "");
        sessionStorage.setItem("to_date", this.state.to_date || "");

        await this.loadDashboardData();
        this.renderCharts();
        await this.loadStagePieData();
    }

    renderCharts() {
        this.renderJobDoughnut();
    }

    renderJobDoughnut() {

        if (!this.jobPieChart.el || !this.state.job_summary.length) {
            console.warn("No data available for Job Chart");
            return;
        }

        if (this.chartInstance) {
            this.chartInstance.destroy();
        }

        const labels = [];
        const values = [];

        this.state.job_summary.forEach(job => {

            labels.push(`${job.job_name} - Selected`);
            values.push(job.selected);

            labels.push(`${job.job_name} - Not Shown`);
            values.push(job.not_shown);

            labels.push(`${job.job_name} - Refused`);
            values.push(job.refused_offers);
        });

        // ✅ UNIQUE COLORS (MAIN FIX)
        const colors = this.generateColors(labels.length);

        this.chartInstance = new Chart(this.jobPieChart.el, {
            type: "doughnut",
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    hoverOffset: 8,
                    borderWidth: 1
                }],
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: "bottom",
                    },
                },
            },
        });
    }
}

RecruitmentDashboard.template = "RecruitmentDashboard";

registry.category("actions").add("recruitment_dashboard", RecruitmentDashboard);