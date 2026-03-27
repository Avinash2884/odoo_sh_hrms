from odoo import models, fields, api, _

class ExitInterviewLine(models.Model):
    _name = 'exit.interview.line'
    _description = 'Exit Interview Line'
    _copy = True
    _rec_name = 'question_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    question_id = fields.Many2one('exit.interview.question',string="Question", required=False)
    option_id = fields.Many2one('exit.interview.option',string="Options",domain="[('question_id', '=', question_id)]")

    initiate_separation_id = fields.Many2one('initiate.separation', string="Initiate Separation")