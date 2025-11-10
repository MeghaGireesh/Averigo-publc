from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json,ast



class BillPayment(models.Model):
    _inherit = "bill.payment"

    bill_line_ids = fields.One2many('bill.payment.line', 'bill_payment_id')
    customer_ids = fields.Many2many('res.partner',
                                    compute='_compute_partner_ids')
    check_no = fields.Char(string="Check No")
    add_pending_bill = fields.Boolean('Pending Bills List')
    auto_apply = fields.Boolean('Auto Apply')
    reference_no = fields.Char(string="Reference No")
    partner_id = fields.Many2one('res.partner', string='Vendor')
    is_wire_transfer = fields.Boolean('Is Wire Transfer')
    account_id = fields.Many2one('account.account', string='Deposit To',
                                 required=True, tracking=True)
    payment_type = fields.Selection(
        [('check', 'Check'), ('cash', 'Cash'), ('credit_card', 'Credit Card'),
         ('wire_transfer', 'Wire Transfer'),
         ('write_off', 'Write Off'), ('advance', 'Credit Balance'), ],
        required=1,
        default='check')
    is_direct_bill = fields.Boolean('Is Direct Bill', default=False)
    is_button_clicked = fields.Boolean('Is Button Clicked', default=False)
    applied_amount_total = fields.Float('Amount Applied',
                                        compute='_compute_applied_amount_total')
    bill_no = fields.Many2one('account.move')
    is_unapplied_amount = fields.Boolean()
    is_ok_save = fields.Boolean()
    payment_confirm = fields.Boolean()
    payment_cancel = fields.Boolean()
    if_after_ok_save = fields.Boolean()
    add_select_all = fields.Boolean()
    advance_payment_ids = fields.One2many('advance.payment.lines',
                                          'bill_payment_id',
                                          store=True)

    @api.onchange('add_select_all')
    def _onchange_add_select_all(self):
        if not self.is_direct_bill:
            for rec in self.bill_line_ids:
                if self.add_select_all:
                    rec.is_checked = True
                    rec.onchange_is_checked()
                else:
                    rec.is_checked = False
                    self.amount = 0
                    rec.onchange_is_checked()

    def _compute_applied_amount_total(self):
        for rec in self:
            rec.applied_amount_total = sum(
                rec.bill_line_ids.mapped('amount_received')) or sum(
                rec.bill_line_ids.mapped('advance_amount'))

    @api.depends('bill_line_ids')
    def compute_bill_ids_len(self):
        for rec in self:
            rec.bill_ids_len = len(rec.bill_line_ids)

    @api.depends('bill_line_ids.unapplied_amount',
                 'bill_line_ids.amount_received',
                 'amount')
    def compute_unapplied_amount(self):
        for rec in self:
            rec.unapplied_amount = 0
            if not rec.payment_mode_id.type == 'write_off':
                total_received_amount = round(sum(
                    rec.bill_line_ids.mapped('amount_received')), 2)
                if total_received_amount < rec.amount:
                    rec.unapplied_amount = rec.amount - total_received_amount
                else:
                    rec.unapplied_amount = 0
                if rec.unapplied_amount > 0:
                    rec.is_unapplied_amount = True
                else:
                    rec.is_unapplied_amount = False
                    rec.if_after_ok_save = False

    @api.onchange('partner_id')
    def clear_lines(self):
        if not self.is_direct_bill:
            self.bill_line_ids = None
            self.amount = 0.00
            self.payment_type = 'check'
            self.is_button_clicked = False
            self.advance_payment_ids = None
            self.is_ok_save = False
            self.add_select_all = False
            self.if_after_ok_save = False
            self.is_unapplied_amount = False
            if self.partner_id:
                if self.advance_move_line_ids:
                    for record in self.advance_move_line_ids:
                        vals = {
                            'bill_payment_id': self.id,
                            'advance_id': record._origin.id,
                            'partner_id': record._origin.partner_id.id,
                            'total_amount': record._origin.debit,
                            'applied_amount': record._origin.credit_value,
                            'balance_amount': record._origin.bal_val
                        }
                        a = self.advance_payment_ids.create(vals)
                move_ids = self.env['account.move'].search(
                    [('partner_id', '=', self.partner_id.id),
                     ('type', '=', 'in_invoice'), ('state', '=', 'posted'),
                     ('invoice_payment_state', '!=', 'paid')],
                    order='invoice_date_due asc')
                if move_ids:
                    invoice_list = []
                    for move_id in move_ids:
                        vals = (0, 0, {
                            'bill_payment_id': self.id,
                            'bill_id': move_id.id,
                            'amount_residual': move_id.amount_residual,
                        })
                        invoice_list.append(vals)
                    self.bill_balance = sum(move_ids.mapped('amount_residual'))
                    self.bill_line_ids = [(2, 0, 0)] + invoice_list
                    # self._onchange_invoice_ids()
                else:
                    raise ValidationError(
                        _("There is no Pending Bill for this vendor"))

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

    # @api.onchange('bill_line_ids')
    # def onchange_bill_ids(self):
    #     advance_lines = self.bill_line_ids.mapped('advance_move_line_id')
    #     for advance_line in advance_lines:
    #         same_advance_lines = self.bill_line_ids.filtered(
    #             lambda s: s.advance_move_line_id.id == advance_line.id)
    #         advance_amount = advance_line.amount_residual
    #         mult = -1 if advance_amount < 0 else 1
    #         if sum(same_advance_lines.mapped(
    #                 'advance_amount')) > mult * advance_amount:
    #             raise ValidationError(
    #                 _("Total Credit Amount distributed cannot be greater than the selected Credit"))
    #     total_amount_received = sum(
    #         self.bill_line_ids.mapped('amount_received'))
    #     if total_amount_received > self.amount:
    #         raise ValidationError(
    #             _("Total Amount Paid cannot be greater than the given amount"))

    @api.onchange('payment_mode_id')
    def _onchange_payment_mode_id(self):
        self.amount = 0
        self.is_unapplied_amount = False
        used_advance = self.bill_line_ids.mapped('used_advance')
        used_advance_values = any(
            isinstance(value, str) and isinstance(ast.literal_eval(value), dict) and ast.literal_eval(value)
            for value in used_advance
        )
        if used_advance_values and self.advance_move_line_ids:
            for record in self.advance_move_line_ids:
                advance = self.env['advance.payment.lines'].search(
                    [('advance_id', '=', record._origin.id), ('bill_payment_id', '=', self._origin.id)])
                advance.write({
                    'applied_amount': record._origin.credit_value,
                    'balance_amount': record._origin.bal_val,
                    'applied_amount_new': 0
                })
            for rec in self.bill_line_ids:
                rec.used_advance = None



        if self.bill_line_ids and self.payment_mode_id.type != 'advance' and not self.is_direct_bill:
            for bill_id in self.bill_line_ids:
                bill_id.advance_amount = 0
                # bill_id.amount_received = 0
                # bill_id.is_checked = False
                bill_id.advance_move_line_id = None
        elif self.bill_line_ids and self.payment_mode_id.type == 'advance' and not self.is_direct_bill:
            for bill in self.bill_line_ids:
                bill.is_checked = False
        self.is_advance = True if self.payment_mode_id.type == 'advance' else False
        self.is_check = True if self.payment_mode_id.type == 'check' else False
        self.is_write_off = True if self.payment_mode_id.type == 'write_off' else False
        self.is_wire_transfer = True if self.payment_mode_id.type == 'wire_transfer' else False
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
            self.account_id = self.journal_id.default_credit_account_id.id
        else:
            journal_id = self.env['account.journal'].search(
                [('type', '=', 'bank')], limit=1)
            self.journal_id = journal_id.id
        if self.payment_mode_id.type == 'advance':
            total_amount = self.vendor_advance_balance
            advance = []
            for bill_id in self.bill_line_ids:
                bill_id.advance_amount = 0
                bill_id.amount_received = 0
                bill_id.advance_move_lines_ids = None
            # if len(self.advance_move_line_ids) == 1:
            #     advance = self.advance_move_line_ids[0]
            #     if self.bill_line_ids and total_amount > 0:
            #         bill_lines = self.bill_line_ids.filtered(
            #             lambda s: s.is_checked)
            #         bill_lines_is_not_checked = self.bill_line_ids.filtered(
            #             lambda s: not s.is_checked)
            #         if not self.is_direct_bill:
            #             if bill_lines:
            #                 for bill in bill_lines:
            #                     if total_amount:
            #                         bill.is_changed = False
            #                         bill.advance_move_line_id = advance._origin.id
            #                         if bill.due_amount >= total_amount:
            #                             if total_amount >= 0:
            #                                 bill.advance_amount = total_amount
            #                                 total_amount = 0
            #                         else:
            #                             if total_amount >= 0:
            #                                 bill.advance_amount = bill.due_amount
            #                                 total_amount -= bill.advance_amount
            #             if bill_lines_is_not_checked:
            #                 for bill_not in bill_lines_is_not_checked:
            #                     if total_amount:
            #                         bill_not.advance_move_line_id = advance._origin.id
            #                         bill_not.is_changed = False
            #                         bill_not.advance_amount = 0
            #                         if bill_not.due_amount > total_amount >= 0:
            #                             bill_not.advance_amount = total_amount
            #                             bill_not.is_checked = True
            #                             total_amount = 0
            #                         elif total_amount >= 0:
            #                             bill_not.advance_amount = bill_not.due_amount
            #                             bill_not.is_checked = True
            #                             total_amount -= bill_not.advance_amount
            #             else:
            #                 for bill_id in self.bill_line_ids:
            #                     if total_amount:
            #                         bill_id.advance_move_line_id = advance._origin.id
            #                         bill_id.is_changed = False
            #                         bill_id.advance_amount = 0
            #                         if bill_id.due_amount > total_amount >= 0:
            #                             bill_id.advance_amount = total_amount
            #                             total_amount = 0
            #                         elif total_amount >= 0:
            #                             bill_id.advance_amount = bill_id.due_amount
            #                             total_amount -= bill_id.advance_amount
            #         elif self.is_direct_bill:
            #             for bill_line in bill_lines:
            #                 if total_amount:
            #                     bill_line.is_changed = False
            #                     bill_line.advance_move_line_id = advance._origin.id
            #                     if bill_line.due_amount >= total_amount:
            #                         if total_amount >= 0:
            #                             bill_line.advance_amount = total_amount
            #                             total_amount = 0
            #                     else:
            #                         if total_amount >= 0:
            #                             bill_line.advance_amount = bill_line.due_amount
            #                             total_amount -= bill_line.advance_amount

        self.account_id = self.journal_id.default_credit_account_id.id

    @api.onchange('auto_apply')
    def _onchange_auto_apply(self):
        if self.is_direct_bill:
            for bill in self.bill_line_ids:
                if bill.amount_residual == self.amount:
                    bill.is_checked = True
                    bill.amount_received = self.amount
        # if self.bill_line_ids:
        #     if self.amount > 0:
        #         total_amount = self.amount
        #         bill_lines = self.bill_line_ids.filtered(lambda s: s.is_checked)
        #         bills_lines_is_not_checked = self.bill_line_ids.filtered(
        #             lambda s: not s.is_checked)
        #         if bill_lines:
        #             for bill_id in bill_lines:
        #                 bill_id.is_changed = False
        #                 bill_id.amount_received = 0
        #                 if bill_id.due_amount > total_amount:
        #                     bill_id.amount_received = total_amount
        #                     total_amount = 0
        #                 else:
        #                     bill_id.amount_received = bill_id.due_amount
        #                     total_amount -= bill_id.amount_received
        #             if bills_lines_is_not_checked:
        #                 for bil_id in bills_lines_is_not_checked:
        #                     bil_id.is_changed = False
        #                     bil_id.amount_received = 0
        #                     if bil_id.due_amount > total_amount:
        #                         bil_id.amount_received = total_amount
        #                         total_amount = 0
        #                     else:
        #                         bil_id.amount_received = bil_id.due_amount
        #                         total_amount -= bil_id.amount_received
        #         else:
        #             for b_id in self.bill_line_ids:
        #                 b_id.is_changed = False
        #                 b_id.amount_received = 0
        #                 if b_id.due_amount > total_amount:
        #                     b_id.amount_received = total_amount
        #                     total_amount = 0
        #                 else:
        #                     b_id.amount_received = b_id.due_amount
        #                     total_amount -= b_id.amount_received
        #     else:
        #         raise ValidationError(_("Please enter the amount"))

    @api.onchange('payment_type')
    def onchange_payment_type(self):
        if self.payment_type == 'check':
            check = self.env['account.payment.mode'].search(
                [('type', '=', 'check')])
            self.payment_mode_id = check.id
        if self.payment_type == 'cash':
            cash = self.env['account.payment.mode'].search(
                [('type', '=', 'cash')])
            self.payment_mode_id = cash.id
        if self.payment_type == 'credit_card':
            credit_card = self.env['account.payment.mode'].search(
                [('type', '=', 'credit_card')])
            self.payment_mode_id = credit_card.id
        if self.payment_type == 'wire_transfer':
            wire_transfer = self.env['account.payment.mode'].search(
                [('type', '=', 'wire_transfer')])
            self.payment_mode_id = wire_transfer.id
        if self.payment_type == 'write_off':
            write_off = self.env['account.payment.mode'].search(
                [('type', '=', 'write_off')])
            self.payment_mode_id = write_off.id
        if self.payment_type == 'advance':
            advance = self.env['account.payment.mode'].search(
                [('type', '=', 'advance')])
            self.payment_mode_id = advance.id
            if self.vendor_advance_balance == 0:
                return {
                    'warning': {
                        'title': 'Warning!',
                        'message': 'The Credit Balance is Zero',
                    }
                }


    @api.depends('partner_id')
    def _compute_partner_ids(self):
        for rec in self:
            unpaid_bills_list = self.env['account.move'].search(
                [('type', '=', 'in_invoice'), ('state', '=', 'posted'),
                 ('invoice_payment_state', '!=', 'paid')])
            partner_ids = unpaid_bills_list.mapped('partner_id')
            rec.customer_ids = partner_ids.ids

    @api.model
    def create(self, vals):
        res = super(BillPayment, self).create(vals)
        # res.post()
        return res

    @api.depends('bill_line_ids', 'bill_line_ids.amount_received')
    @api.onchange('bill_line_ids.amount_received', 'bill_line_ids')
    def onchange_amount_received(self):
        if self.bill_line_ids and not self.is_direct_bill:
            bills = self.bill_line_ids.mapped('is_checked')
            if all(value is False for value in bills):
                self.add_select_all = False
                self.amount = 0
            if self.unapplied_amount > 0:
                self.if_after_ok_save = False
                total_amount = self.unapplied_amount
                bill_lines = self.bill_line_ids.filtered(
                    lambda s: s.is_checked)
                # bill_lines_is_not_checked = self.bill_line_ids.filtered(
                #     lambda s: not s.is_checked)
                if bill_lines:
                    for bill_id in bill_lines:
                        if total_amount:
                            if bill_id.is_changed:
                                continue
                            elif not bill_id.is_changed:
                                if bill_id.due_amount >= total_amount:
                                    bill_id.amount_received += total_amount
                                    bill_id.is_checked = True
                                    total_amount = 0
                                elif bill_id.due_amount < total_amount:
                                    due_amount = bill_id.due_amount
                                    bill_id.amount_received += bill_id.due_amount
                                    bill_id.is_checked = True
                                    total_amount = total_amount - due_amount

        # advance_lines = self.bill_line_ids.mapped('advance_move_line_id')
        # for advance_line in advance_lines:
        #     same_advance_lines = self.bill_line_ids.filtered(
        #         lambda s: s.advance_move_line_id.id == advance_line.id)
        #     advance_amount = advance_line.amount_residual
        #     mult = -1 if advance_amount < 0 else 1
        #     if float('%.2f' % sum(same_advance_lines.mapped(
        #             'advance_amount'))) > mult * advance_amount:
        #         raise ValidationError(
        #             _("Total Credit Amount distributed cannot be greater than the selected Credit"))
        self.is_direct_bill = False

    @api.onchange('amount')
    def _onchange_amount(self):
        if not self.is_direct_bill:
            if self.amount == 0:
                for rec in self.bill_line_ids:
                    rec.amount_received = 0
                    rec.is_checked = False
            total_received_amount = round(
                sum(self.bill_line_ids.filtered(
                    lambda s: s.is_checked).mapped('amount_residual')), 2)
            if self.amount > total_received_amount and self.payment_mode_id.type == 'write_off' and any(
                    self.bill_line_ids.mapped('is_checked')):
                self.amount = 0
                for rec in self.bill_line_ids:
                    rec.amount_received = 0
                return {
                    'warning': {
                        'title': 'Warning!',
                        'message': 'Amount is greater than total Amount Paid.',
                    }
                }
            if self.amount > 0 and self.bill_line_ids and not any(
                    self.bill_line_ids.mapped('is_checked')):
                self.amount = 0
                return {
                    'warning': {
                        'title': 'No Bills are selected!',
                        'message': 'Please select any one bill to apply the amount.',
                    }
                }
            elif self.amount > 0 and self.bill_line_ids and any(
                    self.bill_line_ids.mapped('is_checked')) and self.payment_mode_id.type != 'write_off':
                total_amount = self.amount
                received = sum(self.bill_line_ids.mapped('amount_received'))
                if total_amount > received:
                    bill_lines = self.bill_line_ids.filtered(
                        lambda s: s.is_checked and s.due_amount != 0)
                    bill_lines_is_not_checked = self.bill_line_ids.filtered(
                        lambda s: not s.is_checked)
                    total_amount -= received
                    if bill_lines:
                        for bill in bill_lines:
                            if total_amount:
                                bill.is_changed = False
                                bill.amount_received = 0
                                if bill.due_amount > total_amount:
                                    bill.amount_received = total_amount
                                    bill.is_checked = True
                                    total_amount = 0
                                else:
                                    bill.amount_received = bill.due_amount
                                    bill.is_checked = True
                                    total_amount -= bill.amount_received

                else:
                    bill_lines = self.bill_line_ids.filtered(
                        lambda s: s.is_checked)
                    if bill_lines:
                        amount = self.amount
                        for bill in bill_lines:
                            if amount == 0:
                                bill.amount_received = 0
                                bill.is_checked = False
                            if amount:
                                bill.is_changed = False
                                bill.amount_received = 0
                                bill.is_checked = False
                                if bill.due_amount > amount:
                                    bill.amount_received = amount
                                    bill.is_checked = True
                                    amount = 0
                                else:
                                    bill.amount_received = bill.due_amount
                                    bill.is_checked = True
                                    amount -= bill.amount_received
            elif self.amount > 0 and self.bill_line_ids and any(
                    self.bill_line_ids.mapped('is_checked')) and self.payment_mode_id.type == 'write_off':
                total_amount = self.amount
                received = sum(self.bill_line_ids.mapped('amount_received'))
                bill_lines = self.bill_line_ids.filtered(
                    lambda s: s.is_checked)
                if bill_lines:
                    amount = self.amount
                    for bill in bill_lines:
                        if amount == 0:
                            bill.amount_received = 0
                            bill.is_checked = False
                        if amount:
                            bill.is_changed = False
                            bill.amount_received = 0
                            bill.is_checked = False
                            if bill.due_amount > amount:
                                bill.amount_received = amount
                                bill.is_checked = True
                                amount = 0
                            else:
                                bill.amount_received = bill.due_amount
                                bill.is_checked = True
                                amount -= bill.amount_received

        else:
            if self.amount > 0 and self.bill_line_ids and any(
                    self.bill_line_ids.mapped('is_checked')):
                bill_lines = self.bill_line_ids.filtered(
                    lambda s: s.is_checked)
                if bill_lines:
                    amount = self.amount
                    for bill in bill_lines:
                        if self.bill_no.name in self.bill_line_ids.filtered(
                                lambda s: s.is_checked).mapped('name'):
                            if amount:
                                current_bill = self.bill_line_ids.filtered(
                                    lambda
                                        s: s.is_checked and s.name == self.bill_no.name)
                                if current_bill and amount:
                                    bill.is_changed = False
                                    bill.amount_received = 0
                                    bill.is_checked = False
                                    if self.bill_no.name == bill.name:
                                        if current_bill.due_amount > amount:
                                            current_bill.amount_received = amount
                                            current_bill.is_checked = True
                                            amount = 0
                                            for bills in bill_lines:
                                                if self.bill_no.name != bills.name:
                                                    bills.is_changed = False
                                                    bills.amount_received = 0
                                                    bills.is_checked = False
                                        else:
                                            current_bill.amount_received = current_bill.due_amount
                                            current_bill.is_checked = True
                                            amount -= current_bill.amount_received
                                            if amount:
                                                for bill_id in bill_lines:
                                                    if str(bill_id.name) != str(
                                                            self.bill_no.name):
                                                        bill_id.is_changed = False
                                                        bill_id.amount_received = 0
                                                        bill_id.is_checked = False
                                                        if bill_id.due_amount > amount:
                                                            bill_id.amount_received = amount
                                                            bill_id.is_checked = True
                                                            amount = 0
                                                        else:
                                                            bill_id.amount_received = bill_id.due_amount
                                                            bill_id.is_checked = True
                                                            amount -= bill_id.amount_received
                                                        if bill_id.amount_received == 0:
                                                            bill_id.is_checked = False

                        else:
                            if amount == 0:
                                bill.amount_received = 0
                                bill.is_checked = False
                            if amount:
                                bill.is_changed = False
                                bill.amount_received = 0
                                bill.is_checked = False
                                if bill.due_amount > amount:
                                    bill.amount_received = amount
                                    bill.is_checked = True
                                    amount = 0
                                else:
                                    bill.amount_received = bill.due_amount
                                    bill.is_checked = True
                                    amount -= bill.amount_received
            elif self.amount > 0 and self.bill_line_ids and not any(
                    self.bill_line_ids.mapped('is_checked')):
                self.amount = 0
                return {
                    'warning': {
                        'title': 'No Bills are selected!',
                        'message': 'Please select any one bill to apply the amount.',
                    }
                }

    def btn_temporary(self):
        print("dddddddddd")

    def get_credit_balance(self, res_id):
        domain = [('partner_id', '=', int(res_id['id'])),
                  ('reconciled', '=', False),
                  ('debit', '>', 0), ('parent_state', '=', 'posted'),
                  ('account_internal_type', '=', 'payable')]
        advance_move_line = self.env['account.move.line'].sudo().search(
            domain)
        mult = -1 if sum(
            advance_move_line.mapped('amount_residual')) < 0 else 1
        vendor_advance_balance = mult * sum(
            advance_move_line.mapped('amount_residual'))
        print(vendor_advance_balance,"kkkkkkkkkkkkk")
        return vendor_advance_balance



class BillPaymentLines(models.Model):
    _inherit = "bill.payment.line"

    is_checked = fields.Boolean(string="")
    is_changed = fields.Boolean(string="", default=False)
    invoice_date = fields.Date(related='bill_id.invoice_date')
    advance_move_lines_ids = fields.Many2many('account.move.line',
                                              string="Advance")
    used_advance = fields.Char(string="Used Advance")


    @api.onchange('amount_received')
    def onchange_amount_received(self):
        if self.amount_received < 0:
            raise ValidationError(
                _("Amount Paid cannot be less than 0"))
        self.is_changed = True
        if self.amount_received == 0.00 and not self.bill_payment_id.is_direct_bill:
            self.is_checked = False
        elif self.amount_received > 0:
            self.is_checked = True
        if self.amount_residual_changed:
            raise ValidationError(
                _("Amount Balance is changed in the bill. Please update it here"))
        due_amount = self.amount_residual - self.advance_amount - self.amount_received
        if round(due_amount, 2) < 0:
            raise ValidationError(
                _("Amount Paid cannot be greater than due amount"))

    def write(self, vals):
        if vals.get('is_checked') == False:
            for each in self.advance_move_lines_ids.ids:
                self.advance_move_lines_ids = [(3, each)]
        return super().write(vals)

    @api.onchange('is_checked')
    def onchange_is_checked(self):
        if not self.bill_payment_id.is_direct_bill:
            if self.is_checked:
                if self.bill_payment_id.amount and self.bill_payment_id.unapplied_amount:
                    if self.bill_payment_id.unapplied_amount == self.bill_payment_id.amount > 0:
                        self.amount_received = self.bill_payment_id.amount if self.bill_payment_id.amount < self.amount_residual else self.amount_residual
                        if self.amount_received >= self.bill_payment_id.amount:
                            balance = 0
                        if self.amount_received < self.bill_payment_id.amount:
                            balance = self.bill_payment_id.amount - self.amount_received
                        if not self.bill_payment_id.payment_mode_id.type == 'write_off':
                            self.bill_payment_id.unapplied_amount = balance
                    elif self.bill_payment_id.unapplied_amount > 0:
                        self.amount_received = self.bill_payment_id.unapplied_amount if self.bill_payment_id.unapplied_amount < self.amount_residual else self.amount_residual
                        if self.amount_received >= self.bill_payment_id.unapplied_amount:
                            balance = 0
                        if self.amount_received < self.bill_payment_id.unapplied_amount:
                            balance = self.bill_payment_id.unapplied_amount - self.amount_received
                        if not self.bill_payment_id.payment_mode_id.type == 'write_off':
                            self.bill_payment_id.unapplied_amount = balance
                elif not self.bill_payment_id.amount or not self.bill_payment_id.unapplied_amount:
                    if self.bill_payment_id.payment_mode_id.type != 'advance':
                        self.amount_received = self.amount_residual
            else:
                if self.amount_received > 0:
                    self.amount_received = 0
                    if not self.bill_payment_id.payment_mode_id.type == 'write_off':
                        self.bill_payment_id.unapplied_amount += self.amount_received
                if self.bill_payment_id.is_advance == True:
                    self.advance_amount = 0
                    used_advance_dict = {}
                    if self.used_advance:
                        formatted_text = self.used_advance.replace("'", '"')
                        dict_obj = json.loads(formatted_text)
                        used_advance_dict.update(dict_obj)
                        for key, value in used_advance_dict.items():
                            advance = self.env['advance.payment.lines'].search([('advance_id', '=', int(key)), (
                            'bill_payment_id', '=', self._origin.bill_payment_id.id)])
                            advance.write({
                                'applied_amount': advance.applied_amount - float(value),
                                'balance_amount': advance.balance_amount + float(value),
                                'applied_amount_new': advance.applied_amount_new - float(value),
                            })
                        self.used_advance = None

    @api.onchange('advance_amount')
    def onchange_advance_amount(self):
        if self.advance_amount:
            self.is_checked = True
        if self.amount_residual_changed:
            raise ValidationError(
                _("Amount Balance is changed in the bill please update it here"))
        # advance_amount = self.advance_move_line_id._origin.amount_residual
        # mult = -1 if advance_amount < 0 else 1
        # if self.advance_amount > mult * advance_amount or self.advance_amount > self.amount_residual:
        #     raise ValidationError(        self.is_unapplied_amount = False

        #         _("Credit amount cannot be greater than the selected credit amount or balance amount"))
        due_amount = self.amount_residual - self.advance_amount - self.amount_received
        if round(due_amount, 2) < 0:
            raise ValidationError(
                _("Credit Amount cannot be greater than due amount"))

    # @api.onchange('advance_move_line_id')
    # def _onchange_advance_move_line_ids(self):
    #     if self.amount_residual_changed:
    #         raise ValidationError(
    #             _("Amount Balance is changed in the bill please update it here"))
    #     if self.advance_move_line_id:
    #         amount_used = 0
    #         for line in self.bill_payment_id.bill_line_ids:
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
            'averigo_accounting_updt.add_multi_bill_advance_wizard').id
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_payment_id': self.bill_payment_id.id,
            'default_bill_payment_line_id': self.id,
            'create': False,
            'delete': False
        })
        return {
            'name': _('Add Credit Balance'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': view_id,
            'res_model': 'bill.advance.payment.wizard',
            'context': ctx,
            'target': 'new',
            # 'domain': [('id', 'in', advances.mapped('id'))]
        }



class BillAdvancePaymentWizard(models.TransientModel):
    _name = "bill.advance.payment.wizard"
    _description = "Advance Payments Wizard"

    payment_id = fields.Many2one('bill.payment')
    bill_payment_line_id = fields.Many2one('bill.payment.line')
    advance_payment_ids = fields.One2many('bill.advance.payment.wizard.lines',
                                          'advance_payment_id',
                                          store=True)
    is_advance_lines = fields.Boolean()


    @api.onchange("payment_id")
    def onchange_payment_advance_id(self):
        delivery_list = []
        if not self.payment_id.is_direct_bill:
            for advances in self.payment_id.advance_payment_ids:
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
                self.is_advance_lines = True
            self.advance_payment_ids = [(5, 0, 0)] + delivery_list


    def action_confirm_bill_advance_payment(self):
        selected_advance = self.advance_payment_ids.filtered(
            lambda s: s.is_checked is True)
        if selected_advance:
            total_advance = sum(selected_advance.mapped('apply_amount'))
            advance_ids = selected_advance.mapped('advance_id')
            for rec in selected_advance:
                if rec.apply_amount == 0:
                    raise ValidationError(
                        _("The selected credit applied amount is zero."))

            if advance_ids:
                self.bill_payment_line_id.write({
                    'advance_move_lines_ids': advance_ids.ids
                })
            for advances in self.payment_id.advance_payment_ids:
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
            if self.bill_payment_line_id.advance_amount:
                total_advance += self.bill_payment_line_id.advance_amount
            self.bill_payment_line_id.write({
                'advance_amount': total_advance,
                # 'is_checked': True
            })
            self.bill_payment_line_id.onchange_advance_amount()
            used_advance_dict = {}
            if self.bill_payment_line_id.used_advance:
                formatted_text = self.bill_payment_line_id.used_advance.replace("'",
                                                                           '"')
                dict_obj = json.loads(formatted_text)
                used_advance_dict.update(dict_obj)
            for record in selected_advance:
                record_id = str(record.advance_id.id)
                if record_id in used_advance_dict:
                    used_advance_dict[record_id] += record.apply_amount
                else:
                    used_advance_dict[record_id] = record.apply_amount
            print(used_advance_dict, "kkk")
            self.bill_payment_line_id.used_advance = str(used_advance_dict)



class BillAdvancePaymentWizardLines(models.TransientModel):
    _name = "bill.advance.payment.wizard.lines"
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
    advance_payment_id = fields.Many2one('bill.advance.payment.wizard')

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
            receipt_balance = self.advance_payment_id.bill_payment_line_id.amount_residual
            new_balance = receipt_balance - total_apply_amount
            if total_apply_amount == 0:
                self.apply_amount = min(receipt_balance, self.balance_amount)
            else:
                self.apply_amount = min(new_balance, self.balance_amount)

        if not self.is_checked:
            self.apply_amount = 0
