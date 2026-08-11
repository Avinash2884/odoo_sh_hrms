from odoo import fields, models, tools


class HrWorkEntryAttendanceView(models.Model):

    _name = 'hr.work.entry.attendance.view'
    _description = 'Work Entries (Read-Only Gantt for Attendance)'
    _auto = False
    _order = 'date_start desc'

    name = fields.Char(readonly=True)
    employee_id = fields.Many2one('hr.employee', readonly=True)
    department_id = fields.Many2one('hr.department', readonly=True)
    work_entry_type_id = fields.Many2one('hr.work.entry.type', readonly=True)
    date_start = fields.Datetime(readonly=True)
    date_stop = fields.Datetime(readonly=True)
    duration = fields.Float(readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
        ('cancelled', 'Cancelled'),
    ], readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    we.id                                                       AS id,
                    we.name                                                     AS name,
                    we.employee_id                                              AS employee_id,
                    we.department_id                                            AS department_id,
                    we.work_entry_type_id                                       AS work_entry_type_id,
                    we.date::timestamp                                          AS date_start,
                    (we.date::timestamp
                        + (GREATEST(we.duration, 1) || ' hours')::interval)     AS date_stop,
                    we.duration                                                 AS duration,
                    we.state                                                    AS state,
                    we.company_id                                               AS company_id
                FROM hr_work_entry we
            )
        """ % self._table)