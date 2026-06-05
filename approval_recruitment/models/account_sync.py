import requests
from odoo import models, fields

class AccountSync(models.Model):
    _name = 'account.sync'
    _description = 'Account Sync'

    name = fields.Char(string="Account Name")
    external_id = fields.Integer(string="External ID")

    def sync_accounts(self):

        url = "http://localhost:8080/api/accounts"

        response = requests.get(url)

        if response.status_code != 200:
            return

        data = response.json()

        for rec in data:
            existing = self.search([('external_id', '=', rec['id'])], limit=1)

            if existing:
                existing.write({
                    'name': rec['name']
                })
            else:
                self.create({
                    'name': rec['name'],
                    'external_id': rec['id']
                })