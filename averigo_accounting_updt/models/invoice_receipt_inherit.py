from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json,ast
import logging


_logger = logging.getLogger(__name__)


CARD_TYPE = {
    'master_card': 'Master Card',
    'visa': 'Visa'
}


class InvoiceReceiptInherit(models.Model):
    _inherit = 'invoice.receipt'
    _description = 'Payment Receipt'

    customer_ids = fields.Many2many('res.partner',
                                    compute='_compute_partner_ids')
    check_no = fields.Char(string="Check No")
    reference_no = fields.Char(string="Reference No")
    common_reference = fields.Char('Reference No')
    pending_invoice_boolean = fields.Boolean('Pending Invoices List')
    auto_apply = fields.Boolean('Auto Apply')
    is_wire_transfer = fields.Boolean('Is Wire Transfer')
    is_direct_invoice = fields.Boolean('Is Direct Invoice', default=False)
    is_button_clicked = fields.Boolean('Is Button Clicked', default=False)
    applied_amount_total = fields.Float('Amount Applied',
                                        compute='_compute_applied_amount_total')
    partner_id = fields.Many2one('res.partner', string='Customer')
    is_unapplied_amount = fields.Boolean()
    is_ok_save = fields.Boolean()
    payment_confirm = fields.Boolean()
    payment_cancel = fields.Boolean()
    if_after_ok_save = fields.Boolean()
    add_select_all = fields.Boolean()
    advance_payment_ids = fields.One2many('advance.payment.lines',
                                          'invoice_payment_id',
                                          store=True)

    @api.onchange('add_select_all')
    def _onchange_add_select_all(self):
        if not self.is_direct_invoice:
            for rec in self.invoice_ids:
                if self.add_select_all:
                    rec.is_checked = True
                    rec.onchange_is_checked()
                else:
                    rec.is_checked = False
                    self.amount = 0
                    rec.onchange_is_checked()

    @api.depends('invoice_ids.unapplied_amount', 'invoice_ids.amount_received',
                 'amount')
    def compute_unapplied_amount(self):
        for rec in self:
            rec.unapplied_amount = 0
            if not rec.payment_mode_id.type == 'write_off':
                total_received_amount = round(sum(
                    rec.invoice_ids.mapped('amount_received')), 2)
                if total_received_amount < rec.amount:
                    rec.unapplied_amount = rec.amount - total_received_amount
                else:
                    rec.unapplied_amount = 0
                if rec.unapplied_amount > 0:
                    rec.is_unapplied_amount = True
                else:
                    rec.is_unapplied_amount = False
                    rec.if_after_ok_save = False

    def _compute_applied_amount_total(self):
        for rec in self:
            # AV-2860 to set reference
            if rec.reference_no:
                rec.common_reference = rec.reference_no
            elif rec.check_no:
                rec.common_reference = rec.check_no
            elif rec.card_number:
                rec.common_reference = rec.card_number
            rec.applied_amount_total = sum(
                rec.invoice_ids.mapped('amount_received')) or sum(
                rec.invoice_ids.mapped('advance_amount'))

    @api.depends('partner_id')
    def _compute_partner_ids(self):
        for rec in self:
            unpaid_invoice_list = self.env['account.move'].search(
                [('type', '=', 'out_invoice'), ('state', '=', 'posted'),
                 ('invoice_payment_state', '!=', 'paid')])
            partner_ids = unpaid_invoice_list.mapped('partner_id')
            rec.customer_ids = partner_ids.ids

    @api.depends('journal_id')
    def compute_account_dom_ids(self):
        for rec in self:
            if rec.is_write_off:
                account_ids = self.env['account.account'].search(
                    [('user_type_id.internal_group', '=', 'expense')])
                rec.account_dom_ids = account_ids.ids
            else:
                bank_type_id = self.env.ref(
                    'account.data_account_type_liquidity').id
                account_ids = self.env['account.account'].search(
                    [('user_type_id', '=', bank_type_id)])
                rec.account_dom_ids = account_ids.ids

    @api.onchange('payment_mode_id')
    def _onchange_payment_mode_id(self):
        self.amount = 0
        self.is_unapplied_amount = False
        used_advance = self.invoice_ids.mapped('used_advance')
        used_advance_values = any(
            isinstance(value, str) and isinstance(ast.literal_eval(value), dict) and ast.literal_eval(value)
            for value in used_advance
        )
        if used_advance_values and self.advance_move_line_ids:
            for record in self.advance_move_line_ids:
                advance = self.env['advance.payment.lines'].search(
                                [('advance_id', '=', record._origin.id), ('invoice_payment_id', '=', self._origin.id)])
                advance.write({
                            'applied_amount': record._origin.advance_value,
                            'balance_amount': record._origin.balance_vale,
                            'applied_amount_new': 0
                        })
            for rec in self.invoice_ids:
                rec.used_advance = None
        if self.invoice_ids and self.payment_mode_id.type != 'advance' and not self.is_direct_invoice:
            for invoice_id in self.invoice_ids:
                invoice_id.advance_amount = 0
                # invoice_id.amount_received = 0
                invoice_id.advance_move_line_id = None
        elif self.invoice_ids and self.payment_mode_id.type == 'advance' and not self.is_direct_invoice:
            for invoice_id in self.invoice_ids:
                invoice_id.is_checked = False
        self.is_advance = True if self.payment_mode_id.type == 'advance' else False
        self.is_check = True if self.payment_mode_id.type == 'check' else False
        self.is_write_off = True if self.payment_mode_id.type == 'write_off' else False
        self.is_wire_transfer = True if self.payment_mode_id.type == 'wire_transfer' else False
        self.bill_ids = None
        if self.payment_mode_id.type == 'credit_card':
            self.is_credit_card = True
        else:
            self.is_credit_card = False
            self.credit_card_id = None
        if self.payment_mode_id.type == 'check':
            self.check = True
        else:
            self.check = False
            self.check_id = None
        if self.payment_mode_id.type == 'cash':
            journal_id = self.env['account.journal'].search(
                [('type', '=', 'cash')], limit=1)
            self.journal_id = journal_id.id
            self.account_id = self.journal_id.default_debit_account_id.id
        else:
            journal_id = self.env['account.journal'].search(
                [('type', '=', 'bank')], limit=1)
            self.journal_id = journal_id.id
        if self.payment_mode_id.type == 'advance':
            for invoice_id in self.invoice_ids:
                invoice_id.advance_amount = 0
                invoice_id.amount_received = 0
                invoice_id.advance_move_lines_ids = None
                if self.cust_advance_balance == 0:
                    return {
                        'warning': {
                            'title': 'Warning!',
                            'message': 'The Advance Balance is Zero',
                        }
                    }
            # if len(self.advance_move_line_ids) == 1:
            #     advance = self.advance_move_line_ids[0]
            #     if self.invoice_ids and total_amount > 0:
            #
            #         invoice_lines = self.invoice_ids.filtered(
            #             lambda s: s.is_checked)
            #         invoice_lines_is_not_checked = self.invoice_ids.filtered(
            #             lambda s: not s.is_checked)
            #         if not self.is_direct_invoice:
            #             if invoice_lines:
            #                 for invoice_id in invoice_lines:
            #                     if total_amount:
            #                         invoice_id.is_changed = False
            #                         invoice_id.advance_move_lines_ids = advance._origin.ids
            #                         if invoice_id.due_amount >= total_amount:
            #                             if total_amount >= 0:
            #                                 invoice_id.advance_amount = total_amount
            #                                 total_amount = 0
            #                         else:
            #                             if total_amount >= 0:
            #                                 invoice_id.advance_amount = invoice_id.due_amount
            #                                 total_amount -= invoice_id.advance_amount
            #             if invoice_lines_is_not_checked:
            #                 for invoice_id in invoice_lines_is_not_checked:
            #                     if total_amount:
            #                         invoice_id.advance_move_lines_ids = advance._origin.ids
            #                         invoice_id.is_changed = False
            #                         invoice_id.advance_amount = 0
            #                         if invoice_id.due_amount > total_amount >= 0:
            #                             invoice_id.advance_amount = total_amount
            #                             invoice_id.is_checked = True
            #                             total_amount = 0
            #                         elif total_amount >= 0:
            #                             invoice_id.advance_amount = invoice_id.due_amount
            #                             invoice_id.is_checked = True
            #                             total_amount -= invoice_id.advance_amount
            #             else:
            #                 for invoice_id in self.invoice_ids:
            #                     if total_amount:
            #                         invoice_id.advance_move_lines_ids = advance._origin.ids
            #                         invoice_id.is_changed = False
            #                         invoice_id.advance_amount = 0
            #                         if invoice_id.due_amount > total_amount >= 0:
            #                             invoice_id.advance_amount = total_amount
            #                             total_amount = 0
            #                         elif total_amount >= 0:
            #                             invoice_id.advance_amount = invoice_id.due_amount
            #                             total_amount -= invoice_id.advance_amount
            #         elif self.is_direct_invoice:
            #             for invoice_id in invoice_lines:
            #                 if total_amount:
            #                     invoice_id.is_changed = False
            #                     invoice_id.advance_move_lines_ids = advance._origin.ids
            #                     if invoice_id.due_amount >= total_amount:
            #                         if total_amount >= 0:
            #                             invoice_id.advance_amount = total_amount
            #                             total_amount = 0
            #                     else:
            #                         if total_amount >= 0:
            #                             invoice_id.advance_amount = invoice_id.due_amount
            #                             total_amount -= invoice_id.advance_amount

        self.account_id = self.journal_id.default_debit_account_id.id

    @api.onchange('partner_id')
    def clear_lines(self):
        if not self.is_direct_invoice:
            self.invoice_ids = None
            self.advance_payment_ids = None
            self.amount = 0.00
            self.add_select_all = False
            self.is_button_clicked = False
            self.is_ok_save = False
            self.if_after_ok_save = False
            self.is_unapplied_amount = False
            move_ids = self.env['account.move'].search(
                [('partner_id', '=', self.partner_id.id),
                 ('type', '=', 'out_invoice'), ('state', '=', 'posted'),
                 ('invoice_payment_state', '!=', 'paid')],
                order='invoice_date_due asc')
            self.invoice_balance = sum(move_ids.mapped('amount_residual'))
            self.payment_mode_id = self.env['account.payment.mode'].search(
                [('type', '=', 'check')], limit=1).id
            if self.advance_move_line_ids:
                for record in self.advance_move_line_ids:
                    vals = {
                        'invoice_payment_id': self.id,
                        'advance_id': record._origin.id,
                        'partner_id': record._origin.partner_id.id,
                        'total_amount': record._origin.credit,
                        'applied_amount': record._origin.advance_value,
                        'balance_amount': record._origin.balance_vale
                    }
                    print(vals)
                    a = self.advance_payment_ids.create(vals)
            self._onchange_pending_invoice_boolean()

    @api.onchange('payment_confirm')
    def _onchange_payment_confirm(self):
        if self.is_unapplied_amount:
            self.if_after_ok_save = True
            self.is_ok_save = True
            self.is_unapplied_amount = False

    @api.onchange('payment_cancel')
    def _onchange_payment_cancel(self):
        if self.is_unapplied_amount:
            self.if_after_ok_save = True
            self.is_ok_save = False
            self.is_unapplied_amount = False

    @api.onchange('auto_apply')
    def _onchange_auto_apply(self):
        if self.is_direct_invoice:
            for invoice in self.invoice_ids:
                if invoice.amount_residual == self.amount:
                    invoice.is_checked = True
                    invoice.amount_received = self.amount
        # self.is_button_clicked = True
        # invoice_ids = self.env['invoice.receipt.line'].search([('invoice_receipt_id', '=', self.id)],
        #                                                       order='invoice_date_due ASC')
        # if self.invoice_ids:
        #     if self.amount > 0:
        #         total_amount = self.amount
        #         invoice_lines = self.invoice_ids.filtered(
        #             lambda s: s.is_checked)
        #         invoice_lines_is_not_checked = self.invoice_ids.filtered(
        #             lambda s: not s.is_checked)
        #         if invoice_lines:
        #             for invoice_id in invoice_lines:
        #                 invoice_id.is_changed = False
        #                 invoice_id.amount_received = 0
        #                 if invoice_id.due_amount > total_amount:
        #                     invoice_id.amount_received = total_amount
        #                     total_amount = 0
        #                 else:
        #                     invoice_id.amount_received = invoice_id.due_amount
        #                     total_amount -= invoice_id.amount_received
        #             if invoice_lines_is_not_checked:
        #                 for invoice_id in invoice_lines_is_not_checked:
        #                     invoice_id.is_changed = False
        #                     invoice_id.amount_received = 0
        #                     if invoice_id.due_amount > total_amount:
        #                         invoice_id.amount_received = total_amount
        #                         total_amount = 0
        #                     else:
        #                         invoice_id.amount_received = invoice_id.due_amount
        #                         total_amount -= invoice_id.amount_received
        #         else:
        #             for invoice_id in self.invoice_ids:
        #                 invoice_id.is_changed = False
        #                 invoice_id.amount_received = 0
        #                 if invoice_id.due_amount > total_amount:
        #                     invoice_id.amount_received = total_amount
        #                     total_amount = 0
        #                 else:
        #                     invoice_id.amount_received = invoice_id.due_amount
        #                     total_amount -= invoice_id.amount_received
        #     elif self.is_direct_invoice:
        #         raise ValidationError(_("Please enter Amount."))

    @api.onchange('pending_invoice_boolean')
    def _onchange_pending_invoice_boolean(self):
        if self.partner_id and not self.is_direct_invoice:
            move_ids = self.env['account.move'].search(
                [('partner_id', '=', self.partner_id.id),
                 ('type', '=', 'out_invoice'), ('state', '=', 'posted'),
                 ('invoice_payment_state', '!=', 'paid')],
                order='invoice_date_due asc')
            if move_ids:
                invoice_list = []
                for move_id in move_ids:
                    vals = (0, 0, {
                        'invoice_receipt_id': self.id,
                        'invoice_id': move_id.id,
                        'amount_residual': move_id.amount_residual,
                    })
                    invoice_list.append(vals)
                self.invoice_balance = sum(move_ids.mapped('amount_residual'))
                self.invoice_ids = [(2, 0, 0)] + invoice_list
            else:
                raise ValidationError(
                    _("There is no Pending Invoice for this partner"))

    @api.model
    def create(self, vals):
        """Added message post for payment receipt updates AV-2700"""
        res = super(InvoiceReceiptInherit, self).create(vals)
        # res.post()
        message_body = ""
        if res.name:
            message_body += f"Payment Number : {res.name}<br/>"
        if res.receipt_date:
            message_body += f"Receipt Date : {res.receipt_date.strftime('%m/%d/%Y')}<br/>"
        if res.invoice_balance:
            message_body += f"Invoice Balance : {round(res.invoice_balance, 2):.2f}<br/>"
        if res.cust_advance_balance:
            message_body += f"Advance Balance : {round(res.cust_advance_balance, 2):.2f}<br/>"
        if res.payment_mode_id and res.payment_mode_id.name:
            message_body += f"Mode of Payment : {res.payment_mode_id.name}<br/>"
        if res.check_no:
            message_body += f"Check Number : {res.check_no}<br/>"
        if res.amount:
            message_body += f"Amount: {res.amount}<br/>"
        if res.account_id and res.account_id.name:
            message_body += f"Deposit To : {res.account_id.name}<br/→>"
        if res.is_credit_card:
            if res.card_type:
                message_body += f"Credit Card Type : {CARD_TYPE[res.card_type]}<br/>"
            if res.card_number:
                message_body += f"Credit Card# : {res.card_number}<br/>"
        if res.is_wire_transfer:
            if res.reference_no:
                message_body += f"Reference No : {res.reference_no}<br/>"
        if res.unapplied_amount:
            message_body += f"Unapplied Amount : {round(res.unapplied_amount, 2):.2f}<br/>"
        if res.narration:
            message_body += f"Note : {res.narration}<br/>"
        if res.partner_id:
            res.partner_id.message_post(body=message_body)
        else:
            raise ValueError("Partner is not set for the record.")
        return res

    @api.depends('invoice_ids', 'invoice_ids.amount_received')
    @api.onchange('invoice_ids.amount_received', 'invoice_ids')
    def onchange_amount_received(self):
        if self.invoice_ids and not self.is_direct_invoice:
            invoices = self.invoice_ids.mapped('is_checked')
            if all(value is False for value in invoices):
                self.add_select_all = False
                self.amount = 0
            if self.unapplied_amount > 0:
                self.if_after_ok_save = False
                total_amount = self.unapplied_amount
                invoice_lines = self.invoice_ids.filtered(
                    lambda s: s.is_checked)
                invoice_lines_is_not_checked = self.invoice_ids.filtered(
                    lambda s: not s.is_checked)
                if invoice_lines:
                    for invoice_id in invoice_lines:
                        if total_amount:
                            if invoice_id.is_changed:
                                continue
                            elif not invoice_id.is_changed:
                                if invoice_id.due_amount >= total_amount:
                                    invoice_id.amount_received += total_amount
                                    invoice_id.is_checked = True
                                    total_amount = 0
                                elif invoice_id.due_amount < total_amount:
                                    due_amount = invoice_id.due_amount
                                    invoice_id.amount_received += invoice_id.due_amount
                                    invoice_id.is_checked = True
                                    total_amount = total_amount - due_amount
        # invoice_ids = self.invoice_ids
        # advance_lines = invoice_ids.mapped('advance_move_line_id')
        # for advance_line in advance_lines:
        #     same_advance_lines = invoice_ids.filtered(
        #         lambda s: s.advance_move_line_id.id == advance_line.id)
        #     advance_amount = advance_line.amount_residual
        #     mult = -1 if advance_amount < 0 else 1
        #     if float('%.2f' % sum(same_advance_lines.mapped(
        #             'advance_amount'))) > mult * advance_amount:
        #         raise ValidationError(
        #             _("Total advance amount distributed cannot be greater than the selected advance"))
        self.is_direct_invoice = False

    @api.onchange('amount')
    def _onchange_amount(self):
        if self.amount == 0 and not self.is_direct_invoice:
            for rec in self.invoice_ids:
                rec.amount_received = 0
                rec.is_checked = False
        total_received_amount = round(
            sum(self.invoice_ids.mapped('amount_received')), 2)
        if self.amount > total_received_amount and self.payment_mode_id.type == 'write_off':
            self.amount = 0
            return {
                'warning': {
                    'title': 'Warning!',
                    'message': 'Amount is greater than total Amount Received.',
                }
            }
        if self.amount > 0 and self.invoice_ids and not any(
                self.invoice_ids.mapped('is_checked')):
            self.amount = 0
            return {
                'warning': {
                    'title': 'No Invoices are selected!',
                    'message': 'Please select any one invoice to apply the amount.',
                }
            }
        elif self.amount > 0 and self.invoice_ids and any(
                self.invoice_ids.mapped('is_checked')):
            invoice_lines = self.invoice_ids.filtered(
                lambda s: s.is_checked)
            if invoice_lines:
                amount = self.amount
                for invoice in invoice_lines:
                    if amount == 0:
                        invoice.amount_received = 0
                        invoice.is_checked = False
                    if amount:
                        invoice.is_changed = False
                        invoice.amount_received = 0
                        invoice.is_checked = False
                        if invoice.due_amount > amount:
                            invoice.amount_received = amount
                            invoice.is_checked = True
                            amount = 0
                        else:
                            invoice.amount_received = invoice.due_amount
                            invoice.is_checked = True
                            amount -= invoice.amount_received

    def btn_temp(self):
        print("dddddddddd")

    def get_advance_balance(self, res_id):
        print(res_id,"kkkkkkkkkk")
        domain = ['|', ('advance', '=', True), ('credit', '>', 0),
                  ('partner_id', '=', int(res_id['id'])),
                  ('reconciled', '=', False),
                  ('account_internal_type', '=', 'receivable'),
                  ('parent_state', '=', 'posted')]
        advance_move_line = self.env['account.move.line'].sudo().search(
            domain)
        print(advance_move_line,"kkkk")
        mult = -1 if sum(
            advance_move_line.mapped('amount_residual')) < 0 else 1
        cust_advance_balance = mult * sum(
            advance_move_line.mapped('amount_residual'))
        print(cust_advance_balance,"ooooooo")
        return cust_advance_balance


class InvoiceReceiptLine(models.Model):
    _inherit = "invoice.receipt.line"

    is_checked = fields.Boolean(string="")
    is_changed = fields.Boolean(string="", default=False)
    have_advance_value = fields.Boolean(force_save=True)
    invoice_date = fields.Date(related='invoice_id.invoice_date')
    advance_move_lines_ids = fields.Many2many('account.move.line',
                                              string="Advance")
    used_advance = fields.Char(string="Used Advance")

    @api.onchange('amount_received')
    def onchange_amount_received(self):
        self.is_changed = True
        if self.amount_received == 0.00 and not self.invoice_receipt_id.is_direct_invoice:
            self.is_checked = False
        elif self.amount_received > 0:
            self.is_checked = True
        if self.amount_residual_changed:
            raise ValidationError(
                _("Amount Balance is changed in the invoice please update "
                  "it here"))
        due_amount = self.amount_residual - self.advance_amount - self.amount_received
        if round(due_amount, 2) < 0:
            raise ValidationError(
                _("Amount Received cannot be greater than Balance"))
        if self.amount_received < 0:
            raise ValidationError(
                _("Amount Received cannot be less than 0"))

    def write(self, vals):
        if vals.get('is_checked') == False:
            print("sssssssssssss")
            for each in self.advance_move_lines_ids.ids:
                self.advance_move_lines_ids = [(3, each)]
        return super().write(vals)

    @api.onchange('is_checked')
    def onchange_is_checked(self):
        if not self.invoice_receipt_id.is_direct_invoice:
            if self.is_checked:
                if self.invoice_receipt_id.amount and self.invoice_receipt_id.unapplied_amount:
                    if self.invoice_receipt_id.unapplied_amount == self.invoice_receipt_id.amount > 0:
                        self.amount_received = self.invoice_receipt_id.amount if self.invoice_receipt_id.amount < self.amount_residual else self.amount_residual
                        if self.amount_received >= self.invoice_receipt_id.amount:
                            balance = 0
                        if self.amount_received < self.invoice_receipt_id.amount:
                            balance = self.invoice_receipt_id.amount - self.amount_received
                        if not self.invoice_receipt_id.payment_mode_id.type == 'write_off':
                            self.invoice_receipt_id.unapplied_amount = balance
                    elif self.invoice_receipt_id.unapplied_amount > 0:
                        if self.amount_received > 0:
                            self.amount_received = self.amount_received
                        else:
                            self.amount_received = self.invoice_receipt_id.unapplied_amount if self.invoice_receipt_id.unapplied_amount < self.amount_residual else self.amount_residual
                            if self.amount_received >= self.invoice_receipt_id.unapplied_amount:
                                balance = 0
                            if self.amount_received < self.invoice_receipt_id.unapplied_amount:
                                balance = self.invoice_receipt_id.unapplied_amount - self.amount_received
                            if not self.invoice_receipt_id.payment_mode_id.type == 'write_off':
                                self.invoice_receipt_id.unapplied_amount = balance
                elif not self.invoice_receipt_id.amount or not self.invoice_receipt_id.unapplied_amount:
                    if self.invoice_receipt_id.payment_mode_id.type != 'advance':
                        self.amount_received = self.amount_residual
            else:
                if self.amount_received > 0:
                    self.amount_received = 0
                    if not self.invoice_receipt_id.payment_mode_id.type == 'write_off':
                        self.invoice_receipt_id.unapplied_amount += self.amount_received
                if self.invoice_receipt_id.is_advance == True:
                    self.advance_amount = 0
                    used_advance_dict = {}
                    if self.used_advance:
                        formatted_text = self.used_advance.replace("'",'"')
                        dict_obj = json.loads(formatted_text)
                        used_advance_dict.update(dict_obj)
                        for key, value in used_advance_dict.items():
                            advance = self.env['advance.payment.lines'].search([('advance_id', '=', int(key)),('invoice_payment_id','=', self._origin.invoice_receipt_id.id)])
                            advance.write({
                                'applied_amount': advance.applied_amount - float(value) ,
                                'balance_amount': advance.balance_amount +  float(value),
                                'applied_amount_new': advance.applied_amount_new - float(value),
                            })
                        self.used_advance = None

    @api.onchange('advance_amount')
    def onchange_advance_amount(self):
        if self.advance_amount:
            self.is_checked = True
            if self.amount_residual_changed:
                raise ValidationError(
                    _("Amount Balance is changed in the invoice please update it here"))
            # advance_amount = self.advance_move_line_id._origin.amount_residual
            # mult = -1 if advance_amount < 0 else 1
            # if self.advance_amount > mult * advance_amount or self.advance_amount > self.amount_residual:
            #     raise ValidationError(
            #         _("Advance amount cannot be greater than the selected advance amount or balance amount"))
            due_amount = self.amount_residual - self.advance_amount - self.amount_received
            if round(due_amount,2) < 0:
                raise ValidationError(
                    _("Advance Amount cannot be greater than due amount"))

    # @api.onchange('advance_move_line_id')
    # def _onchange_advance_move_line_ids(self):
    #     if self.amount_residual_changed:
    #         raise ValidationError(
    #             _("Amount Balance is changed in the invoice please update it here"))
    #     if self.advance_move_line_id:
    #         amount_used = 0
    #         for line in self.invoice_receipt_id.invoice_ids:
    #             if line.advance_move_line_id == self.advance_move_line_id:
    #                 amount_used += line.advance_amount
    #         if amount_used == 0:
    #             self.have_advance_value = True
    #             advance_amount = self.advance_move_line_id._origin.amount_residual
    #             mult = -1 if advance_amount < 0 else 1
    #             if mult * advance_amount > self.amount_residual and mult * advance_amount > 0:
    #                 self.advance_amount = self.amount_residual - self.amount_received
    #             elif mult * advance_amount > 0:
    #                 self.advance_amount = mult * advance_amount
    #             else:
    #                 self.advance_amount = 0
    #         elif amount_used > 0:
    #             self.have_advance_value = True
    #             advance_amount = self.advance_move_line_id._origin.amount_residual
    #             mult = -1 if advance_amount < 0 else 1
    #             advance = (mult * advance_amount) - amount_used
    #             if advance > self.amount_residual and advance > 0:
    #                 self.advance_amount = self.amount_residual - self.amount_received
    #             elif advance > 0:
    #                 self.advance_amount = advance
    #             else:
    #                 self.advance_amount = 0
    #     else:
    #         self.have_advance_value = False
    #         self.advance_amount = 0
    #         self.is_checked = False

    def add_multi_advance(self):
        view_id = self.env.ref(
            'averigo_accounting_updt.add_multi_advance_wizard').id
        advances = self.invoice_receipt_id.advance_payment_ids
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_receipt_id': self.invoice_receipt_id.id,
            'default_receipt_line_id': self.id,
            'create': False,
            'delete': False
        })
        return {
            'name': _('Add Advances'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': view_id,
            'res_model': 'advance.payment.wizard',
            'context': ctx,
            'target': 'new',
            # 'domain': [('id', 'in', advances.mapped('id'))]
        }


class AdvancePaymentLines(models.Model):
    _name = "advance.payment.lines"
    _description = "Advance Payments"
    _rec_name = 'move_name'

    advance_id = fields.Many2one('account.move.line', 'Advance Id')
    date = fields.Date(related='advance_id.date', store=True, readonly=True,
                       index=True, copy=False)
    move_name = fields.Char(related='advance_id.move_name', store=True,
                            readonly=True)
    company_id = fields.Many2one(related='advance_id.company_id', store=True,
                                 readonly=True)
    partner_id = fields.Many2one('res.partner')
    type = fields.Char(related='advance_id.name', store=True, readonly=True)
    total_amount = fields.Float()
    applied_amount = fields.Float()
    balance_amount = fields.Float()
    applied_amount_new = fields.Float()
    invoice_payment_id = fields.Many2one('invoice.receipt')
    bill_payment_id = fields.Many2one('bill.payment')


class AdvancePaymentLinesWizard(models.TransientModel):
    _name = "advance.payment.wizard"
    _description = "Advance Payments Wizard"

    receipt_id = fields.Many2one('invoice.receipt')
    receipt_line_id = fields.Many2one('invoice.receipt.line')
    advance_payment_ids = fields.One2many('advance.payment.wizard.lines',
                                          'advance_payment_id',
                                          store=True)
    is_receipt_lines = fields.Boolean()

    @api.onchange("receipt_id")
    def onchange_receipt_advance_id(self):
        delivery_list = []
        if not self.receipt_id.is_direct_invoice:
            for advances in self.receipt_id.advance_payment_ids:
                if advances._origin.balance_amount != 0:
                    vals = (0, 0, {
                        'advance_id': advances.advance_id.id,
                        'partner_id': advances._origin.partner_id.id,
                        'total_amount': advances._origin.total_amount,
                        'applied_amount': advances._origin.applied_amount,
                        'balance_amount': advances._origin.balance_amount,
                        'applied_amount_new': advances._origin.applied_amount_new,
                        'apply_amount': 0
                    })
                    delivery_list.append(vals)
            if not delivery_list:
                self.is_receipt_lines = True
            self.advance_payment_ids = [(5, 0, 0)] + delivery_list

    def action_confirm_advance_payment(self):
        selected_advance = self.advance_payment_ids.filtered(
            lambda s: s.is_checked is True)
        if selected_advance:
            total_advance = sum(selected_advance.mapped('apply_amount'))
            advance_ids = selected_advance.mapped('advance_id')
            for rec in selected_advance:
                if rec.apply_amount == 0:
                    raise ValidationError(
                        _("The selected advance applied amount is zero."))

            if advance_ids:
                self.receipt_line_id.write({
                    'advance_move_lines_ids': advance_ids.ids
                })
            for advances in self.receipt_id.advance_payment_ids:
                for adv in selected_advance:
                    if adv.advance_id.id == advances.advance_id.id:
                        allocation = adv.apply_amount
                        advance_applied_new = adv.apply_amount
                        if advances.applied_amount_new:
                            advance_applied_new = advances.applied_amount_new + adv.apply_amount
                        if advances.applied_amount:
                            allocation = advances.applied_amount + adv.apply_amount
                        balance_amount = advances.total_amount - allocation
                        advances.write(
                            {'applied_amount': allocation,
                             'balance_amount': balance_amount,
                             'applied_amount_new': advance_applied_new})
            if self.receipt_line_id.advance_amount:
                total_advance += self.receipt_line_id.advance_amount
            self.receipt_line_id.write({
                'advance_amount': total_advance,
                # 'is_checked': True
            })
            self.receipt_line_id.onchange_advance_amount()
            used_advance_dict = {}
            if self.receipt_line_id.used_advance:
                formatted_text = self.receipt_line_id.used_advance.replace("'",
                                                                           '"')
                dict_obj = json.loads(formatted_text)
                used_advance_dict.update(dict_obj)
            for record in selected_advance:
                record_id = str(record.advance_id.id)
                if record_id in used_advance_dict:
                    used_advance_dict[record_id] += record.apply_amount
                else:
                    used_advance_dict[record_id] = record.apply_amount
            print(used_advance_dict,"kkk")
            self.receipt_line_id.used_advance = str(used_advance_dict)



class AdvancePaymentWizardLines(models.TransientModel):
    _name = "advance.payment.wizard.lines"
    _description = "Advance Payments"

    is_checked = fields.Boolean(string="")
    advance_id = fields.Many2one('account.move.line', 'Advance Id')
    date = fields.Date(related='advance_id.date', store=True, readonly=True,
                       index=True, copy=False)
    move_name = fields.Char(related='advance_id.move_name', store=True,
                            readonly=True)
    company_id = fields.Many2one(related='advance_id.company_id', store=True,
                                 readonly=True)
    partner_id = fields.Many2one('res.partner')
    type = fields.Char(related='advance_id.name', store=True, readonly=True)
    total_amount = fields.Float(store=True)
    applied_amount = fields.Float(store=True)
    balance_amount = fields.Float(store=True)
    apply_amount = fields.Float()
    applied_amount_new = fields.Float()
    advance_payment_id = fields.Many2one('advance.payment.wizard')

    @api.onchange("apply_amount")
    def onchange_apply_amount(self):
        if self.apply_amount:
            self.is_checked = True
            if self.apply_amount > self.balance_amount:
                raise ValidationError(
                    _("The apply amount should be less than or equal to the balance amount"))
        else:
            self.is_checked = False

    @api.onchange("is_checked")
    def onchange_is_checked(self):
        if not self.apply_amount and self.is_checked:
            total_apply_amount = sum(
                rec.apply_amount for rec in self.advance_payment_id.advance_payment_ids if rec.is_checked)
            receipt_balance = self.advance_payment_id.receipt_line_id.amount_residual
            new_balance = receipt_balance - total_apply_amount
            if total_apply_amount == 0:
                self.apply_amount = min(receipt_balance, self.balance_amount)
            else:
                self.apply_amount = min(new_balance, self.balance_amount)

        if not self.is_checked:
            self.apply_amount = 0

    # @api.onchange("is_checked")
    # def onchange_is_checked(self):
    #     if not self.apply_amount:
    #         if self.is_checked:
    #             amount = 0
    #             for rec in self.advance_payment_id.advance_payment_ids:
    #                 if rec.is_checked:
    #                     amount += rec.apply_amount
    #             new_bal_val =  self.advance_payment_id.receipt_line_id.amount_residual - amount
    #             if amount == 0 and self.advance_payment_id.receipt_line_id.amount_residual > self.balance_amount:
    #                 self.apply_amount = self.balance_amount
    #             elif amount == 0 and  self.advance_payment_id.receipt_line_id.amount_residual < self.balance_amount:
    #                 self.apply_amount = self.advance_payment_id.receipt_line_id.amount_residual
    #             elif amount != 0 and new_bal_val < self.advance_payment_id.receipt_line_id.amount_residual and new_bal_val < self.balance_amount:
    #                 self.apply_amount = new_bal_val
    #             elif amount != 0 and new_bal_val < self.advance_payment_id.receipt_line_id.amount_residual and new_bal_val > self.balance_amount:
    #                 self.apply_amount = self.balance_amount
    #             else:
    #                 self.apply_amount = 0
    #         else:
    #             self.apply_amount = 0
    #
    #     if not self.is_checked:
    #         self.apply_amount = 0
    #     _logger.info(f"eeeeeeeeee-----{self.apply_amount}")



