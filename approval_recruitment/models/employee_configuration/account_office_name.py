from odoo import models, fields, api
import requests


class AccountOfficeName(models.Model):
    _name = 'account.office.name'
    _description = 'Account Office Name'

    name = fields.Char(string="Name")
    external_id = fields.Integer(string="External ID")
    account_manager = fields.Many2one('hr.employee', string="Account Manager")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )

    # @api.model
    # def fetch_account_management_name(self):
    #
    #     url = "https://lsops.odoo.com/api/accounts"
    #
    #     headers = {
    #         "ls-api-key-for-account-management": "ls_secret_key_for_account_management"
    #     }
    #
    #     try:
    #         response = requests.get(url, headers=headers)
    #         data = response.json()
    #
    #         for rec in data:
    #
    #             existing = self.search([
    #                 ('external_id', '=', rec['id'])
    #             ], limit=1)
    #
    #             if existing:
    #                 existing.write({
    #                     'name': rec['name']
    #                 })
    #             else:
    #                 self.create({
    #                     'name': rec['name'],
    #                     'external_id': rec['id']
    #                 })
    #
    #     except Exception as e:
    #         print("API ERROR:", e)

    @api.model
    def fetch_account_management_name(self):

        url = "https://lsops.odoo.com/api/accounts"

        headers = {
            "ls-api-key-for-account-management": "ls_secret_key_for_account_management"
        }

        try:
            response = requests.get(url, headers=headers)
            data = response.json()

            # 1. API-la irundhu vandha IDs-a collection panrom
            fetched_external_ids = [rec['id'] for rec in data if 'id' in rec]

            # 2. Existing Update & New Create
            for rec in data:
                existing = self.search([
                    ('external_id', '=', rec['id'])
                ], limit=1)

                if existing:
                    existing.write({
                        'name': rec['name']
                    })
                else:
                    self.create({
                        'name': rec['name'],
                        'external_id': rec['id']
                    })

            # 3. Anga (API-la) delete aana records-a ingayum delete panrom
            missing_records = self.search([
                ('external_id', 'not in', fetched_external_ids),
                ('external_id', '!=', False)
            ])
            missing_records.unlink()

        except Exception as e:
            print("API ERROR:", e)

    @api.model
    def cron_get_account_management_name(self):
        self.fetch_account_management_name()