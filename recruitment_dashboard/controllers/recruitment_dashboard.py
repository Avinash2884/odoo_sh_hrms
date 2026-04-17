from odoo import http
from odoo.http import request


class RecruitmentDashboard(http.Controller):

    @http.route('/recruitment/summary', auth='user', type='jsonrpc')
    def get_recruitment_summary(self):
        try:
            print("\n================ Recruitment Dashboard Debug Start ================\n")

            Job = request.env['hr.job'].sudo()
            Applicant = request.env['hr.applicant'].sudo()
            Offer = request.env['hr.contract.salary.offer'].sudo()

            # -----------------------------
            # Overall Totals
            # -----------------------------
            total_jobs = Job.search_count([])
            total_applicants = Applicant.search_count([
                ('job_id', '!=', False)
            ])
            total_offers = Offer.search_count([
                ('applicant_id.job_id', '!=', False)
            ])
            total_refused = Applicant.search_count([
                ('active', '=', False),  # ✅ only refused applicants for this job
            ])

            print(f"Totals -> Jobs:{total_jobs}, Applicants:{total_applicants}, "
                  f"Offers:{total_offers}, Refused:{total_refused}")

            # -----------------------------
            # Get Stage IDs
            # -----------------------------
            Stage = request.env['hr.recruitment.stage'].sudo()

            contract_offered_stage = self.env['hr.contract.salary.offer'].search_count([
                ('state', 'in', ['open', 'half_signed'])
            ])

            contract_accepted_stage = self.env['hr.contract.salary.offer'].search_count([
                ('state', '=', 'full_signed')
            ])

            contract_expired_stage = self.env['hr.contract.salary.offer'].search_count([
                ('state', '=', 'expired')
            ])

            contract_refused_stage = self.env['hr.contract.salary.offer'].search_count([
                ('state', '=', 'refused')
            ])

            contract_cancelled_stage = self.env['hr.contract.salary.offer'].search_count([
                ('state', '=', 'cancelled')
            ])

            not_shown_stage = Stage.search([
                ('name', '=', 'No Shown')
            ], limit=1)

            # -----------------------------
            # Job-wise Summary
            # -----------------------------
            jobs = Job.search([])
            job_summary = []

            print("\n================ Job-wise Details ================\n")

            for job in jobs:
                print(f"Processing Job: {job.name} (ID: {job.id})")

                job_total_applicants = Applicant.search_count([
                    ('job_id', '=', job.id)
                ])

                contract_offered = Offer.search_count([
                    ('applicant_id.job_id', '=', job.id),
                    ('state', 'in', ['open', 'half_signed'])
                ])

                contract_accepted = Offer.search_count([
                    ('applicant_id.job_id', '=', job.id),
                    ('state', '=', 'full_signed')
                ])

                contract_expired = Offer.search_count([
                    ('applicant_id.job_id', '=', job.id),
                    ('state', '=', 'expired')
                ])

                contract_refused = Offer.search_count([
                    ('applicant_id.job_id', '=', job.id),
                    ('state', '=', 'refused')
                ])

                contract_cancelled = Offer.search_count([
                    ('applicant_id.job_id', '=', job.id),
                    ('state', '=', 'cancelled')
                ])

                not_shown_count = Applicant.search_count([
                    ('job_id', '=', job.id),
                    ('stage_id', '=', not_shown_stage.id if not_shown_stage else False)
                ])

                job_refused_count = Applicant.search_count([
                    ('job_id', '=', job.id),
                    ('active', '=', 'false'),
                ])

                print(f"  Target Recruitment: {job.no_of_recruitment or 0}")
                print(f"  Total Applicants: {job_total_applicants}")
                print(f"  Contract Offered: {contract_offered}")
                print(f"  Contract Accepted: {contract_accepted}")
                print(f"  Contract Expired: {contract_expired}")
                print(f"  Contract Refused: {contract_refused}")
                print(f"  Contract Cancelled: {contract_cancelled}")
                print(f"  Not Shown: {not_shown_count}")
                print(f"  Refused Offers: {job_refused_count}")
                print("--------------------------------------------------")

                job_summary.append({
                    'job_name': job.name,
                    'target': job.no_of_recruitment or 0,
                    'total_applicants': job_total_applicants,
                    'contract_offered': contract_offered,
                    'contract_accepted': contract_accepted,
                    'contract_expired': contract_expired,
                    'contract_refused': contract_refused,
                    'contract_cancelled': contract_cancelled,
                    'not_shown': not_shown_count,
                    'refused_offers': job_refused_count,
                })
            return {
                'total_applicants': total_applicants,
                'total_jobs': total_jobs,
                'total_offers': total_offers,
                'refused_count': total_refused,
                'job_summary': job_summary,
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            print("ERROR OCCURRED:", str(e))
            return {'error': str(e)}
