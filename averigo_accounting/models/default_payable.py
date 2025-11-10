# -*- coding: utf-8 -*-
######################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2019-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>))
#
#    This program is under the terms of the Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the Software
#    or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#    IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#    DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
#    ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
########################################################################################
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class DefaultPayable(models.Model):
    _name = 'default.payable'
    _inherit = 'mail.thread'
    _description = 'Default Payable'
    """Default Values In Payable"""

    name = fields.Char(default='Payable')
    operator_id = fields.Many2one('res.company', default=lambda self: self.env.company.id)
    payable_account_id = fields.Many2one('account.account',
                                         domain="[('internal_type', '=', 'payable'),('deprecated', '=', False)]")
    terms_discount_account_id = fields.Many2one('account.account',
                                                domain="[('internal_type', '=', 'other'),('deprecated', '=', False)]")
    accrued_account_id = fields.Many2one('account.account', domain="[('deprecated', '=', False)]")
    purchase_discount_account_id = fields.Many2one('account.account',
                                                   domain="[('internal_type', '=', 'other'),('deprecated', '=', False)]")
    insurance_account_id = fields.Many2one('account.account',
                                           domain="[('internal_type', '=', 'other'),('deprecated', '=', False)]")
    misc_bill_account_id = fields.Many2one('account.account', domain="[('deprecated', '=', False)]")
    advance_account_id = fields.Many2one('account.account',
                                         domain="[('internal_type', '=', 'payable'),('deprecated', '=', False)]")
    tax_account_id = fields.Many2one('account.account',
                                     domain="[('internal_type', '=', 'other'),('deprecated', '=', False)]")
    ship_handling_account_id = fields.Many2one('account.account',
                                               domain="[('internal_type', '=', 'other'),('deprecated', '=', False)]")
    write_off_account_id = fields.Many2one('account.account',
                                           domain="[('internal_type', '=', 'other'),('deprecated', '=', False)]")
    bill_seq_id = fields.Many2one('ir.sequence', string="Bill Sequence", domain="[('bill_seq', '=', True)]")
    bill_refund_seq_id = fields.Many2one('ir.sequence', string="Debit Note Sequence",
                                         domain="[('bill_refund_seq', '=', True)]")
    adv_payment_vendor_seq_id = fields.Many2one('ir.sequence', string="Advance Sequence",
                                                domain="[('adv_payment_vendor_seq', '=', True)]")
    payment_vendor_seq_id = fields.Many2one('ir.sequence', string="Payment Sequence",
                                            domain="[('payment_vendor_seq', '=', True)]")

    @api.onchange('bill_seq_id', 'bill_refund_seq_id')
    def _onchange_inv_seq_id(self):
        bill_journal = self.env['account.journal'].search([('code', '=', 'BILL')])
        if self.bill_seq_id:
            bill_journal.sequence_id = self.bill_seq_id.id
        if self.bill_refund_seq_id:
            bill_journal.refund_sequence_id = self.bill_refund_seq_id.id
