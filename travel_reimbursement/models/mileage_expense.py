from odoo import models, fields, api

class MileageExpense(models.Model):
    _name = 'mileage.expense'
    _description = 'Mileage Expense'

    date = fields.Datetime(string='Date', required=True)
    from_location = fields.Char(string="From", required=True)
    to_location = fields.Char(string="To", required=True)
    distance = fields.Float(string="Distance (km)")
    travel_time = fields.Float(string="Travel Time (hrs)", compute="_compute_distance", store=True)
    expense_id = fields.Many2one('hr.expense', string="Expense")

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if rec.expense_id:
                rec.expense_id._onchange_quantity_from_mileage()
        return res

    def create(self, vals):
        rec = super().create(vals)
        if rec.expense_id:
            rec.expense_id._onchange_quantity_from_mileage()
        return rec

    def unlink(self):
        """Recompute parent when mileage line is deleted."""
        expenses = self.mapped('expense_id')
        res = super().unlink()
        for expense in expenses:
            expense._onchange_quantity_from_mileage()
        return res

