from odoo import models, fields, api, _

class ExitInterviewOption(models.Model):
    _name = 'exit.interview.option'
    _description = 'Exit Interview Option'
    _order = 'sequence, id'
    _copy = True

    name = fields.Char(string="Option", required=True)
    sequence = fields.Integer(string="Sequence", default=10)
    question_id = fields.Many2one('exit.interview.question', string="Question",ondelete='restrict')