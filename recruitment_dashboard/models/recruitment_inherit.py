from odoo import models, api, fields
from datetime import date

class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    @api.model
    def get_recruitment_tiles(self):
        applicants = self.env['hr.applicant'].search([])

        # 🔥 PRINT / LOG
        print("Applicants Records => %s", applicants)
        print("Applicants Count => %s", len(applicants))

        return {
            'total_applicants': len(applicants),
            'applicant_ids': applicants.ids,
        }

    @api.model
    def get_job_stage_wise_data(self):
        result = []

        # Get all stages in correct order
        stages = self.env['hr.recruitment.stage'].search([], order="sequence")
        print("✅ Stages Fetched:")
        print([(s.id, s.name, s.sequence, s.hired_stage) for s in stages])

        # Get all jobs
        jobs = self.env['hr.job'].search([])
        print("✅ Jobs Fetched:")
        print([(j.id, j.name) for j in jobs])

        # -------------------------
        # JOB WISE DATA
        # -------------------------
        for job in jobs:
            job_dict = {
                'job_id': job.id,
                'job_name': job.name,
                'stages': []
            }

            for stage in stages:
                applicants = self.search([
                    ('job_id', '=', job.id),
                    ('stage_id', '=', stage.id)
                ])
                stage_info = {
                    'stage_id': stage.id,
                    'stage_name': stage.name,
                    'count': len(applicants),
                    'hired_stage': stage.hired_stage,
                    'applicant_ids': applicants.ids,
                }
                job_dict['stages'].append(stage_info)
                print(f"🔹 Job: {job.name}, Stage: {stage.name}, Count: {len(applicants)}, Applicants: {applicants.ids}")

            result.append(job_dict)

        # -------------------------
        # NOT ASSIGNED JOB
        # -------------------------
        no_job_dict = {
            'job_id': False,
            'job_name': 'Not Assigned',
            'stages': []
        }

        for stage in stages:
            applicants = self.search([
                ('job_id', '=', False),
                ('stage_id', '=', stage.id)
            ])
            stage_info = {
                'stage_id': stage.id,
                'stage_name': stage.name,
                'count': len(applicants),
                'hired_stage': stage.hired_stage,
                'applicant_ids': applicants.ids,
            }
            no_job_dict['stages'].append(stage_info)
            print(f"🔹 Job: Not Assigned, Stage: {stage.name}, Count: {len(applicants)}, Applicants: {applicants.ids}")

        result.append(no_job_dict)

        final_data = {
            'stages': [
                {
                    'stage_id': s.id,
                    'stage_name': s.name,
                    'sequence': s.sequence,
                    'hired_stage': s.hired_stage,
                } for s in stages
            ],
            'jobs': result
        }

        print("✅ Final Data:")
        print(final_data)

        return final_data
