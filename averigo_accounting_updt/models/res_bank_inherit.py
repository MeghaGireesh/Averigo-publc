import re

from odoo import models, api


class ResBankInherit(models.Model):
    _inherit = 'res.partner.bank'

    @api.onchange('acc_number')
    def _onchange_acc_number(self):
        if self.acc_number:
            match = re.match('[0-9]+$', self.acc_number)
            if match is None or len(self.acc_number) < 12:
                self.acc_number = False
                return {
                    'warning': {
                        'title': 'Invalid value',
                        'message': 'Please provide a valid account number.',
                    }
                }


class PartnerCreditCardInherit(models.Model):
    _inherit = 'res.partner.card'

    @api.onchange('card_number')
    def _onchange_card_number(self):
        if self.card_number:
            match = re.match('[0-9]+$', self.card_number)
            if match is None:
                self.card_number = False
                return {
                    'warning': {
                        'title': 'Invalid value',
                        'message': 'Please provide a valid card number.',
                    }
                }




