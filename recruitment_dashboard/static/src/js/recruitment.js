/** @odoo-module **/

import { Component, onWillStart, onMounted, useState, useRef } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export class RecruitmentDashboard extends Component {

    setup() {
        this.state = useState({
            total_applicants: 0,
            total_jobs: 0,
            total_offers: 0,
            refused_count: 0,
            job_summary: [],
        });

        this.jobPieChart = useRef("jobPieChart");
        this.chartInstance = null;

        onWillStart(async () => {
            await this.loadDashboardData();
        });

        onMounted(() => {
            this.renderCharts();
        });
    }

    async loadDashboardData() {
        try {
            const data = await rpc("/recruitment/summary", {});

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

    renderCharts() {
        this.renderJobDoughnut();
    }

    renderJobDoughnut() {

        if (!this.jobPieChart.el || !this.state.job_summary.length) {
            console.warn("No data available for Job Chart");
            return;
        }

        // Destroy old chart if exists (important)
        if (this.chartInstance) {
            this.chartInstance.destroy();
        }

        const labels = [];
        const values = [];
        const colors = [];

        this.state.job_summary.forEach(job => {

            labels.push(`${job.job_name} - Selected`);
            values.push(job.selected);
            colors.push("#28a745");

            labels.push(`${job.job_name} - Not Shown`);
            values.push(job.not_shown);
            colors.push("#dc3545");

            labels.push(`${job.job_name} - Refused`);
            values.push(job.refused_offers);
            colors.push("#6c757d");
        });

        this.chartInstance = new Chart(this.jobPieChart.el, {
            type: "doughnut",
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
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