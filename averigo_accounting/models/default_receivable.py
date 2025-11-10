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


class DefaultReceivable(models.Model):
    _name = 'default.receivable'
    _inherit = 'mail.thread'
    _description = 'Default Receivable'
    """Default Values In Receivable"""

    name = fields.Char(default='Receivable')
    operator_id = fields.Many2one('res.company', default=lambda self: self.env.company.id)
    due_days = fields.Integer('Aging Invoice Report (Due Days)', default=30, required=True)
    due_days_2 = fields.Integer(default=60, required=True)
    due_days_3 = fields.Integer(default=90, required=True)

    receivables_control_account_id = fields.Many2one('account.account',
                                                     domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False)]")
    terms_discount_account_id = fields.Many2one('account.account',
                                                domain="[('internal_type', '=', 'other'),('deprecated', '=', False)]")
    sales_tax_liability_account_id = fields.Many2one('account.account',
                                                     domain="[('internal_type', '=', 'other'),('deprecated', '=', False)]")
    s_h_account_id = fields.Many2one('account.account',
                                     domain="[('internal_type', '=', 'other'),('deprecated', '=', False)]")
    accrued_receivable_account_id = fields.Many2one('account.account', domain=[('deprecated', '=', False)])
    rental_receivable_account_id = fields.Many2one('account.account',
                                                   domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False)]")
    sugar_tax_account_id = fields.Many2one('account.account',
                                           domain="[('internal_type', '=', 'other'),('deprecated', '=', False)]")
    hazard_fee_account_id = fields.Many2one('account.account',
                                            domain="[('internal_type', '=', 'other'),('deprecated', '=', False)]")
    miscellaneous_receipt_control_account_id = fields.Many2one('account.account', domain=[('deprecated', '=', False)])
    sales_discount_account_id = fields.Many2one('account.account',
                                                domain="[('internal_type', '=', 'other'),('deprecated', '=', False)]")
    advance_account_id = fields.Many2one('account.account',
                                         domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False)]")
    insurance_account_id = fields.Many2one('account.account',
                                           domain="[('internal_type', '=', 'other'),('deprecated', '=', False)]")
    write_off_account_id = fields.Many2one('account.account',
                                           domain="[('internal_type', '=', 'other'),('deprecated', '=', False)]")
    service_receivable_account_id = fields.Many2one('account.account',
                                                    domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False)]")
    fuel_charge_account_id = fields.Many2one('account.account',
                                             domain="[('internal_type', '=', 'other'),('deprecated', '=', False)]")
    inv_seq_id = fields.Many2one('ir.sequence', string="Invoice Sequence", domain="[('inv_seq', '=', True)]")
    inv_refund_seq_id = fields.Many2one('ir.sequence', string="Credit Note Sequence",
                                        domain="[('inv_refund_seq', '=', True)]")
    adv_payment_customer_seq_id = fields.Many2one('ir.sequence', string="Advance Sequence",
                                                  domain="[('adv_payment_customer_seq', '=', True)]")
    invoice_receipt_seq_id = fields.Many2one('ir.sequence', string="Invoice Receipt Sequence",
                                             domain="[('invoice_receipt_seq', '=', True)]")

    @api.onchange('inv_seq_id', 'inv_refund_seq_id')
    def _onchange_inv_seq_id(self):
        inv_journal = self.env['account.journal'].search([('code', '=', 'INV')])
        if self.inv_seq_id:
            inv_journal.sequence_id = self.inv_seq_id.id
        if self.inv_refund_seq_id:
            inv_journal.refund_sequence_id = self.inv_refund_seq_id.id

    @api.onchange('due_days', 'due_days_2', 'due_days_3')
    def _onchange_due_days(self):
        if self.due_days:
            if self.due_days >= self.due_days_2 or self.due_days >= self.due_days_3:
                raise ValidationError("First limit cannot be greater than or equal to second and third limit")
        if self.due_days_2:
            if self.due_days_2 >= self.due_days_3:
                raise ValidationError("Second limit cannot be greater than or equal to third")
        if self.due_days_3:
            if self.due_days_3 <= self.due_days or self.due_days_3 <= self.due_days_2:
                raise ValidationError("Third limit cannot be less than or equal to first and second limit")
