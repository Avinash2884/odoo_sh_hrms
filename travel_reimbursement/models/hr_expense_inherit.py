from odoo import models, fields, api, _

class HrExpense(models.Model):
    _inherit = 'hr.expense'
    _description = "Expense"

    mileage_expense_ids = fields.One2many(
        'mileage.expense',
        'expense_id',
        string="Mileage Expense",
    )
    show_mileage_tab = fields.Boolean(string="Show Mileage Tab", compute="_compute_show_mileage_tab")

    @api.depends('product_id')
    def _compute_show_mileage_tab(self):
        mileage_product = self.env.ref('hr_expense.expense_product_mileage', raise_if_not_found=False)
        for rec in self:
            rec.show_mileage_tab = bool(mileage_product and rec.product_id == mileage_product)

    @api.onchange('mileage_expense_ids', 'mileage_expense_ids.distance')
    def _onchange_quantity_from_mileage(self):
        for rec in self:
            rec.quantity = 0
            for line in rec.mileage_expense_ids:
                rec.quantity += line.distance
            print(f"Expense ID: {rec.id}, Total Distance (Quantity): {rec.quantity}")

    def _update_employee_total_expenses(self):
        """Helper to update total in hr.employee"""
        for rec in self:
            if rec.employee_id:
                expenses = self.env['hr.expense'].search([
                    ('employee_id', '=', rec.employee_id.id)
                ])
                total_amount = sum(expenses.mapped('total_amount'))
                rec.employee_id.write({'employee_expenses': total_amount})
                print(f"✅ Updated Employee: {rec.employee_id.name}, Total Expenses: {total_amount}")
            else:
                print("⚠️ No employee linked for this record.")

    def create(self, vals_list):
        records = super().create(vals_list)
        records._update_employee_total_expenses()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._update_employee_total_expenses()
        return res