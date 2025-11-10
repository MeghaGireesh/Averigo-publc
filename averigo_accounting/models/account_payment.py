from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

import logging

_logger = logging.getLogger(__name__)


class AverigoAccountPayment(models.Model):
    _inherit = 'account.payment'

    def _get_payment_mode_id(self):
        payment_mode_id = self.env['account.payment.mode'].search(
            [('type', '=', 'check')], limit=1)
        return payment_mode_id

    customer_no = fields.Char('Customer No', size=10, related='partner_id.code',
                              states={'draft': [('readonly', False)]})
    vendor_no = fields.Char('Vendor No', size=10,
                            related='partner_id.vendor_code',
                            states={'draft': [('readonly', False)]})
    customer_debit = fields.Char('Customer Balance',
                                 compute='_compute_customer_debit', copy=False)
    vendor_debit = fields.Char('Vendor Balance',
                               compute='_compute_customer_debit', copy=False)
    partner_card_id = fields.Many2one('res.partner.card',
                                      string='Customer Card',
                                      states={'draft': [('readonly', False)]})
    check_id = fields.Many2one('res.partner.check', string='Check',
                               states={'draft': [('readonly', False)]})
    check_no = fields.Char('Check No')
    check_date = fields.Date('Check Date')
    check_amount = fields.Float('Amount')
    check_bank_id = fields.Many2one('res.bank')
    partner_bank_name = fields.Char()
    notes = fields.Text()
    internal_notes = fields.Text()
    revision_no = fields.Integer('Revision No', default=0)
    revision_date = fields.Date('Revision Date',
                                default=fields.Date.context_today)
    user_id = fields.Many2one('res.users', string='Owner', readonly=False,
                              default=lambda self: self.env.user.id)
    advance_payment = fields.Boolean('Advance Payment',
                                     help="This is used to identify advance payment record")
    payment_mode_id = fields.Many2one('account.payment.mode',
                                      string="Mode Of Payment",
                                      default=_get_payment_mode_id)
    check = fields.Boolean('Is Check', help="This is used to give attribute")
    balance_amount = fields.Monetary(string='Balance Amount',
                                     compute="_compute_reconciled_misc_receipts_ids",
                                     required=True, readonly=True,
                                     states={'draft': [('readonly', False)]},
                                     tracking=True)
    reconciled_misc_receipts_ids = fields.Many2many('account.move',
                                                    string='Reconciled Misc recipts',
                                                    compute='_compute_reconciled_misc_receipts_ids',
                                                    help="Misc Recipts whose journal items have been reconciled with these payments.")
    has_misc_receipts = fields.Boolean(
        compute="_compute_reconciled_misc_receipts_ids",
        help="Technical field used for usability purposes")
    reconciled_misc_receipts_count = fields.Integer(
        compute="_compute_reconciled_misc_receipts_ids")
    advance_count = fields.Integer(
        help="Used to hide the payment difference if there is any advance payment")
    bill_ids = fields.One2many('payment.bill.line', 'payment_id')
    unapplied_amount = fields.Float(compute='compute_unapplied_amount')
    extra_unapplied_amount = fields.Float(compute='compute_unapplied_amount')
    narration = fields.Text()
    is_advance = fields.Boolean()
    is_bank = fields.Boolean()
    is_credit_card = fields.Boolean()
    is_write_off = fields.Boolean()
    invoice_balance = fields.Float()
    cust_advance_balance = fields.Float(store=True,
                                        compute='_compute_cust_advance_amount')
    advance_move_line_ids = fields.Many2many('account.move.line', store=True,
                                             compute='_compute_cust_advance_amount')
    phone = fields.Char(related='partner_id.phone')
    division_id = fields.Many2one('res.division')
    bill_ids_len = fields.Integer(compute='compute_bill_ids_len')
    account_id = fields.Many2one('account.account', string='Account',
                                 tracking=True)
    account_dom_ids = fields.Many2many('account.account',
                                       compute='compute_account_dom_ids')
    credit_card_id = fields.Many2one('res.partner.card', string='Credit Card',
                                     states={'draft': [('readonly', False)]})
    card_type = fields.Selection(
        [('master_card', 'Master Card'), ('visa', 'Visa')], string='Card Type',
        default='master_card')
    card_number = fields.Char('Card #')
    card_name = fields.Char('Name')
    card_expiry = fields.Date(default=fields.Date.context_today)

    @api.depends('journal_id')
    def compute_account_dom_ids(self):
        for rec in self:
            bank_and_cash_account_id = self.env.ref(
                'account.data_account_type_liquidity')
            # credit_card_account_id = self.env.ref('account.data_account_type_credit_card')
            if rec.advance_payment and rec.payment_type == 'inbound':
                # account_ids = self.env['account.account'].search([('user_type_id.internal_group', '=', 'asset')])
                account_ids = self.env['account.account'].search(
                    [('user_type_id', '=', bank_and_cash_account_id.id)])
                rec.account_dom_ids = account_ids.ids
            else:
                # account_ids = self.env['account.account'].search([('user_type_id.internal_group', '!=', 'income')])
                account_ids = self.env['account.account'].search(
                    [('user_type_id', '=', bank_and_cash_account_id.id)])
                rec.account_dom_ids = account_ids.ids

    @api.depends('bill_ids')
    def compute_bill_ids_len(self):
        for rec in self:
            rec.bill_ids_len = len(rec.bill_ids)

    @api.depends('partner_id')
    def _compute_cust_advance_amount(self):
        for rec in self:
            rec.advance_move_line_ids = None
            domain = [('partner_id', '=', rec.partner_id.id),
                      ('reconciled', '=', False), ('advance', '=', True),
                      ('account_internal_type', '=', 'payable'),
                      ('company_id', '=', rec.company_id.id)]
            advance_move_line = rec.env['account.move.line'].sudo().search(
                domain)
            rec.advance_move_line_ids = advance_move_line.ids
            mult = -1 if sum(
                advance_move_line.mapped('amount_residual')) < 0 else 1
            rec.cust_advance_balance = mult * sum(
                advance_move_line.mapped('amount_residual'))

    def fetch_bill(self):
        move_ids = self.env['account.move'].search(
            [('partner_id', '=', self.partner_id.id),
             ('type', '=', 'in_invoice'), ('state', '=', 'posted'),
             ('invoice_payment_state', '!=', 'paid')])
        if move_ids:
            invoice_list = []
            for move_id in move_ids:
                vals = (0, 0, {
                    'payment_id': self.id,
                    'invoice_id': move_id.id,
                    'amount_residual': move_id.amount_residual,
                })
                invoice_list.append(vals)
            self.invoice_balance = sum(move_ids.mapped('amount_residual'))
            _logger.info('averigo_accounting_account_payment_5_0_0_invoice')
            self.bill_ids = [(5, 0, 0)] + invoice_list
        else:
            raise ValidationError(
                _("There is no Pending Invoice for this partner"))

    def auto_apply(self):
        bill_ids = self.bill_ids.sorted(lambda o: o.invoice_date_due)
        total_amount = self.amount
        for bill_id in bill_ids:
            bill_id.amount_received = 0
            if bill_id.due_amount > total_amount:
                bill_id.amount_received = total_amount
                total_amount = 0
            else:
                bill_id.amount_received = bill_id.due_amount
                total_amount -= bill_id.amount_received

    @api.onchange('bill_ids')
    def onchange_bill_ids(self):
        bill_ids = self.bill_ids
        advance_lines = bill_ids.mapped('advance_move_line_id')
        for advance_line in advance_lines:
            same_advance_lines = bill_ids.filtered(
                lambda s: s.advance_move_line_id.id == advance_line.id)
            advance_amount = advance_line.amount_residual
            mult = -1 if advance_amount < 0 else 1
            if sum(same_advance_lines.mapped(
                    'advance_amount')) > mult * advance_amount:
                raise ValidationError(
                    _("Total advance amount distributed cannot be greater than the selected advance"))
        total_amount_received = sum(bill_ids.mapped('amount_received'))
        if total_amount_received > self.amount:
            raise ValidationError(
                _("Total received amount cannot be greater than receipt amount"))

    @api.onchange('partner_id')
    def clear_lines(self):
        self.bill_ids = None
        self.invoice_balance = None

    @api.depends('bill_ids.unapplied_amount', 'bill_ids.amount_received',
                 'amount')
    def compute_unapplied_amount(self):
        for rec in self:
            total_received_amount = sum(rec.bill_ids.mapped('amount_received'))
            if total_received_amount < rec.amount:
                rec.unapplied_amount = rec.amount - total_received_amount
            else:
                rec.unapplied_amount = 0

    @api.onchange('partner_id')
    def _onchange_partner_id_card(self):
        if self.partner_id and len(self.partner_id.card_ids) > 0:
            self.partner_card_id = self.partner_id.card_ids[0]
        return {'domain': {
            'partner_card_id': [('partner_id', 'in', [self.partner_id.id,
                                                      self.partner_id.commercial_partner_id.id])]}}

    # @api.onchange('partner_type', 'partner_id')
    # def _onchange_payment_type_domain(self):
    #     if self.partner_type == 'supplier':
    #         return {'domain': {
    #             'partner_id': [('is_vendor', '=', True), ('parent_id', '=', False), ('type', '=', 'contact'),
    #                            ('vendor_approve', '=', True)]}}

    @api.onchange('check')
    def _onchange_check(self):
        if self.check:
            check_ids = self.env['account.payment'].search(
                [('check_id', '!=', False)]).mapped('check_id')
            return {'domain': {'check_id': [('id', 'not in', check_ids.ids)]}}

    # def post(self):
    #     if self._context.get('direct_payment'):
    #         for bill in self.invoice_ids:
    #             if len(bill.advance_move_line_ids) > 1:
    #                 for advance_line_id in bill.advance_move_line_ids:
    #                     lines = advance_line_id
    #                     lines += bill.line_ids.filtered(
    #                         lambda line: line.account_id == lines[0].account_id and not line.reconciled)
    #                     lines.with_context(paid_amount=advance_line_id.amount_residual).reconcile()
    #             elif len(bill.advance_move_line_ids) == 1:
    #                 lines = bill.advance_move_line_ids
    #                 lines += bill.line_ids.filtered(
    #                     lambda line: line.account_id == lines[0].account_id and not line.reconciled)
    #                 lines.with_context(paid_amount=bill.advance_amount).reconcile()
    #     res = super(AverigoAccountPayment, self).post()
    #     if not self._context.get('direct_payment'):
    #         journal_items = self.env['account.move.line'].search([('payment_id', 'in', self.ids)])
    #         for journal_item in journal_items:
    #             journal_item.write({
    #                 'advance': True,
    #                 'check_id': self.check_id.id,
    #             })
    #     return res

    def post_bill(self):
        bill_ids = self.bill_ids
        if bill_ids:
            advance_lines = bill_ids.mapped('advance_move_line_id')
            if not advance_lines and self.is_advance:
                raise ValidationError(_("Not added any advance payments"))
            for bill_id in bill_ids:
                lines = bill_id.advance_move_line_id
                lines += bill_id.invoice_id.line_ids.filtered(
                    lambda
                        line: line.account_id == lines.account_id and not line.reconciled)
                lines.with_context(
                    paid_amount=bill_id.advance_amount).reconcile()
                if bill_id.amount_received and not self.is_advance:
                    self.communication = bill_id.name
                    self.invoice_ids |= bill_id.invoice_id
                    # payment_id.move_line_ids.filtered(lambda s: s.debit != 0).account_id = self.account_id.id
            if sum(bill_ids.mapped(
                    'amount_received')) <= 0 and not self.is_advance:
                raise ValidationError(_("Amount Received is not given"))
            if self.unapplied_amount > 0:
                self.advance_payment = True
        else:
            raise ValidationError(_("There is no Bills"))

    def post(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconcilable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconcilable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        if self.amount == 0:
            raise UserError(_("Amount is not given"))
        if self._context.get('direct_payment'):
            # direct payment will be reconciled with the advance and bill
            self.post_bill()
        AccountMove = self.env['account.move'].with_context(
            default_type='entry')
        for rec in self:

            if rec.state != 'draft':
                raise UserError(_("Only a draft payment can be posted."))

            if any(inv.state != 'posted' for inv in rec.invoice_ids):
                raise ValidationError(
                    _("The payment cannot be processed because the invoice is not open!"))

            # keep the name in case of a payment reset to draft
            if not rec.name:
                # Use the right sequence to set the name
                if rec.payment_type == 'transfer':
                    sequence_code = 'account.payment.transfer'
                else:
                    if rec.partner_type == 'customer':
                        if rec.payment_type == 'inbound' and not rec.advance_payment:
                            sequence_code = 'account.payment.customer.invoice'
                        # get sequence based on default receivable setup
                        if rec.payment_type == 'inbound' and rec.advance_payment:
                            default_receivable = self.env[
                                'default.receivable'].search(
                                [('operator_id', '=', self.env.company.id)],
                                limit=1)
                            if default_receivable.adv_payment_customer_seq_id:
                                rec.name = default_receivable.adv_payment_customer_seq_id.with_context(
                                    ir_sequence_date=rec.payment_date).next_by_id()
                            sequence_code = 'advance'
                        if rec.payment_type == 'outbound':
                            sequence_code = 'account.payment.customer.refund'
                    if rec.partner_type == 'supplier':
                        if rec.payment_type == 'inbound':
                            sequence_code = 'account.payment.supplier.refund'
                        if rec.payment_type == 'outbound':
                            sequence_code = 'account.payment.supplier.invoice'
                        # get sequence based on default payable setup
                        # if rec.payment_type == 'outbound' and self._context.get('direct_bill', False):
                        #     default_payable = self.env['default.payable'].search(
                        #         [('operator_id', '=', self.env.company.id)], limit=1)
                        #     if default_payable.payment_vendor_seq_id:
                        #         rec.name = default_payable.payment_vendor_seq_id.with_context(
                        #             ir_sequence_date=rec.payment_date).next_by_id()
                        #     sequence_code = 'payment'
                        if rec.payment_type == 'outbound' and rec.advance_payment:
                            default_payable = self.env[
                                'default.payable'].search(
                                [('operator_id', '=', self.env.company.id)],
                                limit=1)
                            if default_payable.adv_payment_vendor_seq_id:
                                rec.name = default_payable.adv_payment_vendor_seq_id.with_context(
                                    ir_sequence_date=rec.payment_date).next_by_id()
                            sequence_code = 'advance'
                if sequence_code not in ['advance', 'payment']:
                    rec.name = self.env['ir.sequence'].next_by_code(
                        sequence_code, sequence_date=rec.payment_date)
                if not rec.name and rec.payment_type != 'transfer':
                    raise UserError(
                        _("You have to define a sequence for %s in your company.") % (
                            sequence_code,))
            payment_move = rec._prepare_payment_moves()
            if self._context.get('direct_payment'):
                credit_line = payment_move[0]['line_ids'][1]
                for a in credit_line:
                    if a != 0:
                        a['account_id'] = rec.account_id.id
            moves = AccountMove.create(payment_move)
            moves.filtered(
                lambda move: move.journal_id.post_at != 'bank_rec').post()

            # Update the state / move before performing any reconciliation.
            move_name = self._get_move_name_transfer_separator().join(
                moves.mapped('name'))
            rec.write({'state': 'posted', 'move_name': move_name})
            if rec.payment_type in ('inbound', 'outbound'):
                # ==== 'inbound' / 'outbound' ====
                if rec.invoice_ids:
                    if self._context.get('direct_payment'):
                        for move in moves:
                            invoice_id = rec.invoice_ids.filtered(
                                lambda l: l.id in move.bill_ids.ids)
                            (move + invoice_id).line_ids \
                                .filtered(
                                lambda
                                    line: not line.reconciled and line.account_id == rec.destination_account_id) \
                                .reconcile()
                    else:
                        (moves + rec.invoice_ids).line_ids \
                            .filtered(
                            lambda
                                line: not line.reconciled and line.account_id == rec.destination_account_id) \
                            .reconcile()
            elif rec.payment_type == 'transfer':
                # ==== 'transfer' ====
                moves.mapped('line_ids') \
                    .filtered(lambda
                                  line: line.account_id == rec.company_id.transfer_account_id) \
                    .reconcile()

        # if not self._context.get('direct_payment'):
        if self.advance_payment:
            # passed value to journal items if the payment is advance or direct
            journal_items = self.env['account.move.line'].search(
                [('payment_id', 'in', self.ids)])
            for journal_item in journal_items:
                if self.payment_type == 'inbound' and journal_item.debit != 0:
                    journal_item.write({
                        'account_id': self.account_id.id
                    })
                elif self.payment_type == 'outbound' and journal_item.credit != 0:
                    journal_item.write({
                        'account_id': self.account_id.id
                    })
                journal_item.write({
                    'advance': True,
                    'check_id': self.check_id.id,
                    'payment_mode_id': self.payment_mode_id.id
                })
        elif self.account_id:
            journal_items = self.env['account.move.line'].search(
                [('payment_id', 'in', self.ids)])
            for journal_item in journal_items:
                if self.payment_type == 'inbound' and journal_item.debit != 0:
                    journal_item.write({
                        'account_id': self.account_id.id
                    })
                elif self.payment_type == 'outbound' and journal_item.credit != 0:
                    journal_item.write({
                        'account_id': self.account_id.id
                    })
        return True

    @api.onchange('check_id')
    def _onchange_check_id(self):
        self.amount = self.check_id.check_amount

    @api.onchange('payment_mode_id')
    def _onchange_payment_mode_id(self):
        self.is_advance = True if self.payment_mode_id.type == 'advance' else False
        self.is_bank = True if self.payment_mode_id.type == 'check' else False
        self.is_write_off = True if self.payment_mode_id.type == 'write_off' else False
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
        if self.payment_type == 'inbound':
            self.account_id = self.journal_id.default_debit_account_id.id
        elif self.payment_type == 'outbound':
            self.account_id = self.journal_id.default_credit_account_id.id

    # @api.onchange('journal_id')
    # def _onchange_journal_id(self):
    #     self.is_advance = True if self.journal_id.name == 'Advance' else False
    #     self.is_bank = True if self.journal_id.name == 'Bank' else False
    #     self.is_credit_card = True if self.journal_id.name == 'Credit Card' else False
    #     self.is_write_off = True if self.journal_id.name == 'Write Off' else False
    #     self.bill_ids = None
    #     if self.journal_id.name.lower() == 'check':
    #         self.check = True
    #     else:
    #         self.check = False
    #         self.check_id = None

    # advance_check_ids = fields.One2many('res.partner.check', 'advance_id', string='Checks')
    # total_check_amount = fields.Float(compute='_compute_total_check_amount')

    # @api.depends('advance_check_ids.check_amount')
    # def _compute_total_check_amount(self):
    #     for check in self:
    #         check_amount = 0.0
    #         for line in check.advance_check_ids:
    #             check_amount += line.check_amount
    #         check.update({
    #             'total_check_amount': check_amount,
    #         })

    # @api.onchange('total_check_amount')
    # def onchange_total_check_amount(self):
    #     self.amount = self.total_check_amount

    @api.model
    def fields_view_get(self, view_id=None, view_type='tree', toolbar=False,
                        submenu=False):
        res = super(AverigoAccountPayment, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar,
            submenu=submenu)
        self.env['ir.rule'].clear_caches()
        return res

    @api.onchange('partner_id')
    def _compute_customer_debit(self):
        for rec in self:
            rec.customer_debit = 0
            rec.vendor_debit = 0
            if rec.partner_id:
                """Change self.partner_id to rec.partner_id to avoid singleton issue"""
                rec.customer_debit = -(
                    rec.partner_id.credit) if rec.partner_id.credit else 0
                rec.vendor_debit = -(
                    rec.partner_id.credit) if rec.partner_id.credit else 0

    @api.onchange('customer_no')
    def _onchange_customer_no(self):
        if self.customer_no:
            partner = self.env['res.partner'].search(
                [('code', '=', self.customer_no)])
            if partner:
                self.partner_id = partner.id
            else:
                raise ValidationError(
                    "There is no customer with no %s" % self.customer_no)

    @api.onchange('vendor_no')
    def _onchange_vendor_no(self):
        if self.vendor_no:
            partner = self.env['res.partner'].search(
                [('vendor_code', '=', self.vendor_no)])
            if partner:
                self.partner_id = partner.id
            else:
                raise ValidationError(
                    "There is no Vendor with no %s" % self.vendor_no)

    @api.depends('move_line_ids.matched_debit_ids',
                 'move_line_ids.matched_credit_ids')
    def _compute_reconciled_misc_receipts_ids(self):

        for record in self:
            reconciled_moves = record.move_line_ids.mapped(
                'matched_debit_ids.debit_move_id.move_id') \
                               + record.move_line_ids.mapped(
                'matched_credit_ids.credit_move_id.move_id')
            record.reconciled_misc_receipts_ids = reconciled_moves.filtered(
                lambda move: move.is_misc_receipt)
            record.reconciled_move_ids = reconciled_moves

            if record.reconciled_misc_receipts_ids:
                balance = self.amount + sum(
                    record.reconciled_misc_receipts_ids.mapped(
                        'amount_total_signed'))
                record.has_misc_receipts = bool(record.reconciled_move_ids)
                record.reconciled_misc_receipts_count = len(
                    record.reconciled_move_ids)
                record.balance_amount = balance
            else:
                record.balance_amount = record.amount
                record.reconciled_misc_receipts_count = 0

    def button_misc_receipts(self):
        return {
            'name': _('Paid Misc. Receipts'),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'views': [(self.env.ref(
                'averigo_accounting.view_misc_receipt_tree').id, 'tree'),
                      (self.env.ref(
                          'averigo_accounting.view_misc_receipt_form').id,
                       'form')],
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in',
                        [x.id for x in self.reconciled_misc_receipts_ids])],
            'context': {'create': False},
        }

    def action_register_payment(self):
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            return ''

        return {
            'name': _('Register Payment'),
            'res_model': len(
                active_ids) == 1 and 'account.payment' or 'account.payment.register',
            'view_mode': 'form',
            'view_id': len(active_ids) != 1 and self.env.ref(
                'account.view_account_payment_form_multi').id or self.env.ref(
                'averigo_accounting.view_account_payment_invoice_bill_form').id,
            'context': self.env.context,
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def _prepare_direct_payment_moves(self):
        ''' Prepare the creation of journal entries (account.move) by creating a list of python dictionary to be passed
        to the 'create' method.
        Example 1: outbound with write-off:
        Account             | Debit     | Credit
        ---------------------------------------------------------
        BANK                |   900.0   |
        RECEIVABLE          |           |   1000.0
        WRITE-OFF ACCOUNT   |   100.0   |
        Example 2: internal transfer from BANK to CASH:
        Account             | Debit     | Credit
        ---------------------------------------------------------
        BANK                |           |   1000.0
        TRANSFER            |   1000.0  |
        CASH                |   1000.0  |
        TRANSFER            |           |   1000.0
        :return: A list of Python dictionary to be passed to env['account.move'].create.
        '''
        all_move_vals = []
        for payment in self:
            company_currency = payment.company_id.currency_id
            move_names = payment.move_name.split(
                payment._get_move_name_transfer_separator()) if payment.move_name else None

            # Compute amounts.
            write_off_amount = payment.payment_difference_handling == 'reconcile' and -payment.payment_difference or 0.0
            if payment.payment_type in ('outbound', 'transfer'):
                counterpart_amount = payment.amount
                liquidity_line_account = payment.journal_id.default_debit_account_id
            else:
                counterpart_amount = -payment.amount
                liquidity_line_account = payment.journal_id.default_credit_account_id

            # Manage currency.
            if payment.currency_id == company_currency:
                # Single-currency.
                balance = counterpart_amount
                write_off_balance = write_off_amount
                counterpart_amount = write_off_amount = 0.0
                currency_id = False
            else:
                # Multi-currencies.
                balance = payment.currency_id._convert(counterpart_amount,
                                                       company_currency,
                                                       payment.company_id,
                                                       payment.payment_date)
                write_off_balance = payment.currency_id._convert(
                    write_off_amount, company_currency, payment.company_id,
                    payment.payment_date)
                currency_id = payment.currency_id.id

            # Manage custom currency on journal for liquidity line.
            if payment.journal_id.currency_id and payment.currency_id != payment.journal_id.currency_id:
                # Custom currency on journal.
                if payment.journal_id.currency_id == company_currency:
                    # Single-currency
                    liquidity_line_currency_id = False
                else:
                    liquidity_line_currency_id = payment.journal_id.currency_id.id
                liquidity_amount = company_currency._convert(
                    balance, payment.journal_id.currency_id, payment.company_id,
                    payment.payment_date)
            else:
                # Use the payment currency.
                liquidity_line_currency_id = currency_id
                liquidity_amount = counterpart_amount

            # Compute 'name' to be used in receivable/payable line.

            # Compute 'name' to be used in liquidity line.

            liquidity_line_name = payment.name

            # ==== 'inbound' / 'outbound' ====
            bill_ids = payment.bill_ids.mapped('invoice_id')
            branches = bill_ids.mapped('division_id')
            for branch in branches:
                bills = bill_ids.filtered(
                    lambda l: l.division_id.id == branch.id)
                total_amount = sum(bills.mapped('amount_total'))
                rec_pay_line_name = _("Vendor Payment") + ': %s' % ', '.join(
                    bills.mapped('name'))
                move_vals = {
                    'date': payment.payment_date,
                    'ref': ', '.join(bills.mapped('name')),
                    'journal_id': payment.journal_id.id,
                    'currency_id': payment.journal_id.currency_id.id or payment.company_id.currency_id.id,
                    'partner_id': payment.partner_id.id,
                    'division_id': branch.id,
                    'bill_ids': [(4, bill.id) for bill in bills],
                    'line_ids': [
                        # Receivable / Payable / Transfer line.
                        (0, 0, {
                            'name': rec_pay_line_name,
                            'amount_currency': counterpart_amount + write_off_amount if currency_id else 0.0,
                            'currency_id': currency_id,
                            'debit': total_amount,
                            'credit': 0.0,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.commercial_partner_id.id,
                            'account_id': payment.destination_account_id.id,
                            'payment_id': payment.id,
                        }),
                        # Liquidity line.
                        (0, 0, {
                            'name': liquidity_line_name,
                            'amount_currency': -liquidity_amount if liquidity_line_currency_id else 0.0,
                            'currency_id': liquidity_line_currency_id,
                            'debit': 0.0,
                            'credit': total_amount,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.commercial_partner_id.id,
                            'account_id': liquidity_line_account.id,
                            'payment_id': payment.id,
                        }),
                    ],
                }
                all_move_vals.append(move_vals)
        return all_move_vals

    def _prepare_payment_moves(self):
        vals = super(AverigoAccountPayment, self)._prepare_payment_moves()
        if self._context.get('direct_payment'):
            vals = self._prepare_direct_payment_moves()
        return vals

    def write(self, values):
        if values:
            if len(values) == 1 and 'revision_no' in values:
                return super(AverigoAccountPayment, self).write(values)
            else:
                self.revision_no += 1
        return super(AverigoAccountPayment, self).write(values)
