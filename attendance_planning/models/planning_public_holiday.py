from odoo import api, models
import pytz


class PlanningSlotHoliday(models.Model):
    _inherit = 'planning.slot'

    @api.model
    def get_public_holidays_for_calendar(self):
        result = []

        leaves = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),
            '|',
            ('company_id', '=', self.env.company.id),
            ('company_id', '=', False),
        ])

        tz_name = (
            self.env.user.tz
            or self.env.company.resource_calendar_id.tz
            or 'Asia/Calcutta'
        )

        local_tz = pytz.timezone(tz_name)

        for leaf in leaves:
            if leaf.date_from:
                utc_dt = leaf.date_from.replace(tzinfo=pytz.utc)
                local_dt = utc_dt.astimezone(local_tz)
                date_str = local_dt.strftime('%Y-%m-%d')
                result.append({
                    'date': date_str,
                    'name': leaf.name or 'Holiday',
                })

        return result