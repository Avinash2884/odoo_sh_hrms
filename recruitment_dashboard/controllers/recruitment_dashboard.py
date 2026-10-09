from odoo import http
from odoo.http import request


class RecruitmentDashboard(http.Controller):

    @http.route('/recruitment/summary', auth='user', type='jsonrpc')
    def get_recruitment_summary(self, from_date=None, to_date=None):

        domain = []
        offer_domain = []

        # -----------------------------
        # Date Filters
        # -----------------------------
        if from_date:
            domain.append(('create_date', '>=', from_date))
            offer_domain.append(('create_date', '>=', from_date))

        if to_date:
            domain.append(('create_date', '<=', to_date))
            offer_domain.append(('create_date', '<=', to_date))   # ✅ FIXED

        try:
            print("\n================ Recruitment Dashboard Debug Start ================\n")

            Job = request.env['hr.job'].sudo()
            Applicant = request.env['hr.applicant'].sudo()
            Offer = request.env['hr.contract.salary.offer'].sudo()
            Stage = request.env['hr.recruitment.stage'].sudo()

            # -----------------------------
            # Overall Totals
            # -----------------------------
            total_jobs = Job.search_count(domain)

            total_applicants = Applicant.search_count([
                ('job_id', '!=', False),
                *domain
            ])

            total_offers = Offer.search_count([
                ('applicant_id.job_id', '!=', False),
                *offer_domain
            ])

            total_refused = Applicant.search_count([
                ('active', '=', False),
                *domain   # ✅ FIXED (filter applied)
            ])

            print(f"Totals -> Jobs:{total_jobs}, Applicants:{total_applicants}, "
                  f"Offers:{total_offers}, Refused:{total_refused}")

            # -----------------------------
            # Stage
            # -----------------------------
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
                    ('job_id', '=', job.id),
                    *domain
                ])

                contract_offered = Offer.search_count([
                    ('applicant_id.job_id', '=', job.id),
                    ('state', 'in', ['open', 'half_signed']),
                    *offer_domain
                ])

                contract_accepted = Offer.search_count([
                    ('applicant_id.job_id', '=', job.id),
                    ('state', '=', 'full_signed'),
                    *offer_domain   # ✅ FIXED
                ])

                contract_expired = Offer.search_count([
                    ('applicant_id.job_id', '=', job.id),
                    ('state', '=', 'expired'),
                    *offer_domain   # ✅ FIXED
                ])

                contract_refused = Offer.search_count([
                    ('applicant_id.job_id', '=', job.id),
                    ('state', '=', 'refused'),
                    *offer_domain   # ✅ FIXED
                ])

                contract_cancelled = Offer.search_count([
                    ('applicant_id.job_id', '=', job.id),
                    ('state', '=', 'cancelled'),
                    *offer_domain   # ✅ FIXED
                ])

                not_shown_count = Applicant.search_count([
                    ('job_id', '=', job.id),
                    ('stage_id', '=', not_shown_stage.id if not_shown_stage else False),
                    *domain
                ])

                job_refused_count = Applicant.search_count([
                    ('job_id', '=', job.id),
                    ('active', '=', False),
                    *domain
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
                    'job_id': job.id,
                    'job_name': job.name,
                    'job_display': f"{job.name} (#{job.id})",  # ✅ UNIQUE DISPLAY
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

    @http.route('/recruitment/stage_pie', auth='user', type='jsonrpc')
    def get_stage_pie(self, job_id=None):

        Applicant = request.env['hr.applicant'].sudo()
        Stage = request.env['hr.recruitment.stage'].sudo()

        stages = Stage.search([], order="sequence")

        data = []

        for stage in stages:
            domain = [('stage_id', '=', stage.id)]

            if job_id:
                domain.append(('job_id', '=', int(job_id)))

            count = Applicant.search_count(domain)

            data.append({
                'stage_name': stage.name,
                'count': count
            })

        return data