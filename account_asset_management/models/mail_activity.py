from odoo import models, fields


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    rule_id = fields.Many2one('reordering.rule', string="Reordering Rule", help="Used to get rule id in activity")
