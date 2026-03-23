from odoo import models, fields, api, _

class ExitInterviewQuestion(models.Model):
    _name = 'exit.interview.question'
    _description = 'Exit Interview Question'
    _order = 'sequence, id'
    _copy = True

    name = fields.Char(string="Question", required=True)
    sequence = fields.Integer(string="Sequence", default=10)
    option_ids = fields.One2many('exit.interview.option', 'question_id', string="Options",copy=True)