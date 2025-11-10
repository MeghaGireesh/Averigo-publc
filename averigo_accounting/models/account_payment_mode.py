from odoo import models, fields, api, _


class AccountPaymentMode(models.Model):
    _name = 'account.payment.mode'

    name = fields.Char(required=1)
    type = fields.Selection(
        [('check', 'Check'), ('cash', 'Cash'), ('credit_card', 'Credit Card'),
         ('wire_transfer', 'Wire Transfer'),
         ('write_off', 'Write Off'), ('advance', 'Advance'), ], required=1)
    operator_id = fields.Many2one('res.company',
                                  default=lambda self: self.env.company.id)
