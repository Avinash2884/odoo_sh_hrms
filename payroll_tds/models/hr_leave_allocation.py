from odoo import models


class HrLeaveAllocation(models.Model):
    _inherit = "hr.leave.allocation"

    def _track_subtype(self, init_values):
        # Stop posting the approval notification
        if 'state' in init_values and self.state == 'validate':
            return False

        return super()._track_subtype(init_values)