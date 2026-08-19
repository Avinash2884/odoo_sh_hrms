from odoo import api, models
import logging
import pytz
from datetime import datetime

_logger = logging.getLogger(__name__)


class PlanningSlotHoliday(models.Model):
    _inherit = 'planning.slot'

    @api.model
    def get_public_holidays_for_calendar(self):
        """
        Reads public holidays from resource.calendar.leaves.
        Converts UTC datetime to IST date for calendar highlighting.
        """
        result = []

        leaves = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),  # company-wide holidays only
            '|',
            ('company_id', '=', self.env.company.id),
            ('company_id', '=', False),
        ])

        _logger.info("[Holiday] Found %d public holiday leaves", len(leaves))

        # Use company timezone or fallback to Asia/Kolkata
        tz_name = self.env.company.resource_calendar_id.tz or 'Asia/Kolkata'
        local_tz = pytz.timezone(tz_name)

        for leaf in leaves:
            if leaf.date_from:
                # Convert UTC → local date
                utc_dt = leaf.date_from.replace(tzinfo=pytz.utc)
                local_dt = utc_dt.astimezone(local_tz)
                date_str = local_dt.strftime('%Y-%m-%d')
                result.append({
                    'date': date_str,
                    'name': leaf.name or 'Holiday',
                })
                _logger.info("[Holiday] %s → %s", leaf.name, date_str)

        return result