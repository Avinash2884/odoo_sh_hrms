from odoo import models, fields, api, _

class ExitInterviewLine(models.Model):
    _name = 'exit.interview.line'
    _description = 'Exit Interview Line'
    _copy = True
    _rec_name = 'question_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    question_id = fields.Many2one('exit.interview.question',string="Question", required=False)
    option_id = fields.Many2one('exit.interview.option',string="Options",domain="[('question_id', '=', question_id)]")
    answer_text = fields.Text(string="Your Answer")
    initiate_separation_id = fields.Many2one('initiate.separation', string="Initiate Separation")

    show_answer_text = fields.Boolean(
        compute="_compute_show_answer_text",
        store=False
    )

    @api.depends('option_id')
    def _compute_show_answer_text(self):
        for rec in self:
            rec.show_answer_text = rec.option_id.is_other if rec.option_id else False