from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import json
import logging

_logger = logging.getLogger(__name__)


class BillPayment(models.Model):
    _name = "bill.payment"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Bill Payment'
    """Bill Payment"""

    def _get_payment_mode_id(self):
        payment_mode_id = self.env['account.payment.mode'].search(
            [('type', '=', 'check')], limit=1)
        return payment_mode_id

    name = fields.Char()
    partner_id = fields.Many2one('res.partner')
    amount = fields.Float()
    payment_date = fields.Date(default=fields.Date.context_today)
    state = fields.Selection(
        [('draft', 'Draft'), ('done', 'Done'), ('cancelled', 'Cancelled')],
        default='draft')
    operator_id = fields.Many2one('res.company',
                                  default=lambda self: self.env.company.id)
    user_id = fields.Many2one('res.users',
                              default=lambda self: self.env.user.id)
    currency_id = fields.Many2one('res.currency',
                                  related='operator_id.currency_id')
    journal_id = fields.Many2one('account.journal', string='Journal',
                                 required=True, tracking=True,
                                 domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', operator_id)]")
    payment_mode_id = fields.Many2one('account.payment.mode',
                                      string="Mode Of Payment",
                                      default=_get_payment_mode_id)
    account_id = fields.Many2one('account.account', string='Deposit To',
                                 required=True, tracking=True)
    account_dom_ids = fields.Many2many('account.account',
                                       compute='compute_account_dom_ids')
    partner_bank_account_id = fields.Many2one('res.partner.bank',
                                              string="Customer Bank Account",
                                              domain="['|', ('company_id', '=', False), ('company_id', '=', operator_id)]")
    partner_bank_name = fields.Char()
    check_id = fields.Many2one('res.partner.check', string='Check')
    partner_card_id = fields.Many2one('res.partner.card',
                                      string='Customer Card')
    card_type = fields.Selection(
        [('master_card', 'Master Card'), ('visa', 'Visa')], string='Card Type',
        default='master_card')
    card_number = fields.Char('Card #')
    vendor_advance_balance = fields.Float(store=True,
                                          compute='_compute_vendor_advance_amount')
    advance_move_line_ids = fields.Many2many('account.move.line', store=True,
                                             compute='_compute_vendor_advance_amount')
    # filter_advance_ids = fields.Many2many('account.move.line', compute='compute_filter_advance_ids')
    bill_balance = fields.Float()
    phone = fields.Char(related='partner_id.phone')
    bill_ids = fields.One2many('bill.payment.line', 'bill_payment_id')
    bill_ids_len = fields.Integer(compute='compute_bill_ids_len')
    unapplied_amount = fields.Float(compute='compute_unapplied_amount')
    extra_unapplied_amount = fields.Float(compute='compute_unapplied_amount')
    narration = fields.Text()
    is_advance = fields.Boolean()
    is_bank = fields.Boolean()
    is_credit_card = fields.Boolean()
    is_check = fields.Boolean()
    is_write_off = fields.Boolean()
    check_no = fields.Char()

    @api.depends('journal_id')
    def compute_account_dom_ids(self):
        for rec in self:
            if rec.is_write_off:
                account_ids = self.env['account.account'].search(
                    [('user_type_id.internal_group', '=', 'expense')])
                rec.account_dom_ids = account_ids.ids
            else:
                account_ids = self.env['account.account'].search([])
                rec.account_dom_ids = account_ids.ids

    # @api.onchange('payment_mode_id')
    # def _onchange_payment_mode_id(self):
    #     self.is_advance = True if self.payment_mode_id.type == 'advance' else False
    #     self.is_check = True if self.payment_mode_id.type == 'check' else False
    #     self.is_write_off = True if self.payment_mode_id.type == 'write_off' else False
    #     self.bill_line_ids = None
    #     if self.payment_mode_id.type == 'credit_card':
    #         self.is_credit_card = True
    #     else:
    #         self.is_credit_card = False
    #         self.credit_card_id = None
    #     if self.payment_mode_id.type == 'check':
    #         self.check = True
    #     else:
    #         self.check = False
    #         self.check_id = None
    #     if self.payment_mode_id.type == 'cash':
    #         journal_id = self.env['account.journal'].search(
    #             [('type', '=', 'cash')], limit=1)
    #         self.journal_id = journal_id.id
    #         self.account_id = self.journal_id.default_credit_account_id.id
    #     else:
    #         journal_id = self.env['account.journal'].search(
    #             [('type', '=', 'bank')], limit=1)
    #         self.journal_id = journal_id.id
    #     self.account_id = self.journal_id.default_credit_account_id.id

    # @api.onchange('journal_id')
    # def onchange_journal_id(self):
    #     self.is_advance = True if self.journal_id.name == 'Advance' else False
    #     self.is_bank = True if self.journal_id.name == 'Bank' else False
    #     self.is_credit_card = True if self.journal_id.name == 'Credit Card' else False
    #     self.is_check = True if self.journal_id.name == 'Check' else False
    #     self.is_write_off = True if self.journal_id.name == 'Write Off' else False
    #     self.invoice_ids = None

    def post(self):
        # if not self.if_after_ok_save and self.payment_mode_id.type != 'advance':
        #     raise ValidationError(
        #         _("Please confirm the message."))
        if self.bill_line_ids:
            if self.amount == 0 and self.payment_mode_id.type != 'advance':
                raise ValidationError(
                    _("The Entered Amount is zero."))
            _logger.info(f"Summmmmmmmmmm{sum(self.bill_line_ids.mapped('amount_received')) }")
            _logger.info(f"Ammmouuuuuuuuuunnnnnnttttttt {self.amount}")
            if round(sum(self.bill_line_ids.mapped('amount_received')), 2) > self.amount:
                raise ValidationError(
                    _("Amount Paid is greater than Amount"))
            if self.if_after_ok_save == False and self.unapplied_amount != 0:
                raise ValidationError(
                    _("Please confirm the message."))
            self.bill_balance = sum(self.bill_line_ids.mapped('due_amount'))
            payment_method_id = self.env['account.payment.method'].search(
                [('payment_type', '=', 'outbound'), ('code', '=', 'manual')],
                limit=1)
            advance_lines = self.bill_line_ids.mapped('advance_move_lines_ids')
            if not advance_lines and self.is_advance:
                raise ValidationError(_("The Credit Applied Amount is zero."))
            for bill_id in self.bill_line_ids:
                if len(bill_id.advance_move_lines_ids) == 1:
                    lines = bill_id.advance_move_lines_ids
                    lines += bill_id.bill_id.line_ids.filtered(
                        lambda
                            line: line.account_id == lines.account_id and not line.reconciled)
                    lines.with_context(
                        paid_amount=bill_id.advance_amount).reconcile()
                else:
                    advance_payment_lines = bill_id.advance_move_lines_ids
                    used_advance_dict = {}
                    advance_amount = 0
                    for advance_line_id in advance_payment_lines:
                        if bill_id.used_advance:
                            formatted_text = bill_id.used_advance.replace("'", '"')
                            dict_obj = json.loads(formatted_text)
                            used_advance_dict.update(dict_obj)
                            for key, value in used_advance_dict.items():
                                if advance_line_id.id == int(key):
                                    advance_amount = float(value)
                        lines = advance_line_id
                        lines += bill_id.bill_id.line_ids.filtered(lambda
                                                                             line: line.account_id == lines.account_id and not line.reconciled)
                        lines.with_context(
                            paid_amount=advance_amount).reconcile()

                if bill_id.amount_received and not self.is_advance:
                    vals = {
                        'invoice_ids': bill_id.bill_id.ids,
                        'partner_id': self.partner_id.id,
                        'communication': bill_id.name,
                        'amount': bill_id.amount_received,
                        'journal_id': self.journal_id.id,
                        'payment_mode_id': self.payment_mode_id.id,
                        'account_id': self.account_id.id,
                        'payment_type': 'outbound',
                        'partner_type': 'supplier',
                        'payment_method_id': payment_method_id.id,
                    }
                    payment_id = self.env['account.payment'].sudo().create(vals)
                    payment_id.post()
                    payment_id.move_line_ids.filtered(lambda s: s.credit != 0).account_id = self.account_id.id
            if sum(self.bill_line_ids.mapped(
                    'amount_received')) <= 0 and not self.is_advance:
                raise ValidationError(_("Amount Paid is not given"))
            if self.unapplied_amount > 0 and self.is_ok_save:
                vals = {
                    'partner_id': self.partner_id.id,
                    'amount': self.unapplied_amount,
                    'journal_id': self.journal_id.id,
                    'payment_mode_id': self.payment_mode_id.id,
                    'account_id': self.account_id.id,
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'advance_payment': True,
                    'payment_method_id': payment_method_id.id,
                }
                payment_id = self.env['account.payment'].create(vals)
                payment_id.post()
        else:
            raise ValidationError(_("There is no Bills"))
        self.state = 'done'
        self.if_after_ok_save = False
        self.is_unapplied_amount = False
        for rec in self.bill_line_ids:
            if self.state == 'done':
                if self.payment_mode_id.type == 'advance' and rec.advance_amount == 0:
                    rec.unlink()
                elif self.payment_mode_id.type != 'advance' and rec.amount_received == 0:
                    rec.unlink()
        self._compute_vendor_advance_amount()


    def cancel(self):
        self.state = 'cancelled'

    def fetch_bill(self):
        move_ids = self.env['account.move'].search(
            [('partner_id', '=', self.partner_id.id),
             ('type', '=', 'in_invoice'), ('state', '=', 'posted'),
             ('invoice_payment_state', '!=', 'paid')])
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
            _logger.info('aaaaaaaaaaaaaaaaaaaaaaaa4556456456 %s', invoice_list)
            self.bill_line_ids = [(2, 0, 0)] + invoice_list
            # self._onchange_invoice_ids()
        else:
            raise ValidationError(_("There is no Pending Bill for this vendor"))

    def auto_apply(self):
        bill_ids = self.env['bill.payment.line'].search(
            [('bill_payment_id', '=', self.id)],
            order='bill_date_due ASC')
        total_amount = self.amount
        for bill_id in bill_ids:
            bill_id.amount_received = 0
            if bill_id.due_amount > total_amount:
                bill_id.amount_received = total_amount
                total_amount = 0
            else:
                bill_id.amount_received = bill_id.due_amount
                total_amount -= bill_id.amount_received

    @api.model
    def create(self, vals):
        res = super(BillPayment, self).create(vals)
        default_payable = self.env['default.payable'].search(
            [('operator_id', '=', self.env.company.id)], limit=1)
        if default_payable.payment_vendor_seq_id:
            res.name = default_payable.payment_vendor_seq_id.with_context(
                force_company=res.operator_id.id).next_by_id()
        else:
            raise UserError(
                _("You have to define a sequence for payment in your company."))
        return res

    def unlink(self):
        for rec in self:
            if rec.state == "done":
                raise UserError(
                    _("You cannot delete a payment if the state is 'Done'"))
        return super(BillPayment, self).unlink()

    # @api.depends('bill_line_ids')
    # def compute_bill_ids_len(self):
    #     for rec in self:
    #         rec.bill_ids_len = len(rec.bill_line_ids)

    # @api.depends('invoice_ids.advance_move_line_id')
    # def compute_filter_advance_ids(self):
    #     for rec in self:
    #         line_ids = rec.invoice_ids
    #         lst = []
    #         # for line in line_ids:
    #             # mult = -1 if line.advance_move_line_id._origin.amount_residual < 0 else 1
    #             # if mult * line.advance_move_line_id._origin.amount_residual <= line.advance_amount:
    #             # if line.advance_move_line_id:
    #             #     lst.append(line.advance_move_line_id._origin.id)
    #         rec.filter_advance_ids = lst

    # @api.depends('bill_line_ids.unapplied_amount', 'bill_line_ids.amount_received',
    #              'amount')
    # def compute_unapplied_amount(self):
    #     for rec in self:
    #         total_unapplied_amount = sum(
    #             rec.bill_line_ids.mapped('unapplied_amount'))
    #         total_received_amount = sum(rec.bill_line_ids.mapped('amount_received'))
    #         if total_received_amount < rec.amount:
    #             rec.unapplied_amount = rec.amount - total_received_amount
    #         else:
    #             rec.unapplied_amount = 0
    #         # rec.unapplied_amount = total_unapplied_amount

    @api.depends('partner_id')
    def _compute_vendor_advance_amount(self):
        for rec in self:
            rec.advance_move_line_ids = None
            domain = [('partner_id', '=', rec.partner_id.id),
                      ('reconciled', '=', False),
                      ('debit', '>', 0), ('parent_state', '=', 'posted'),
                      ('account_internal_type', '=', 'payable'),
                      ('company_id', '=', rec.operator_id.id)]
            advance_move_line = rec.env['account.move.line'].sudo().search(
                domain)
            rec.advance_move_line_ids = advance_move_line.ids
            mult = -1 if sum(
                advance_move_line.mapped('amount_residual')) < 0 else 1
            rec.vendor_advance_balance = mult * sum(
                advance_move_line.mapped('amount_residual'))

    @api.onchange('partner_id')
    def clear_lines(self):
        self.bill_line_ids = None
        self.bill_balance = None

    # @api.onchange('bill_line_ids')
    # def onchange_bill_ids(self):
    #     # bill_ids = self.bill_line_ids
    #     advance_lines = self.bill_line_ids.mapped('advance_move_line_id')
    #     for advance_line in advance_lines:
    #         same_advance_lines = self.bill_line_ids.filtered(
    #             lambda s: s.advance_move_line_id.id == advance_line.id)
    #         advance_amount = advance_line.amount_residual
    #         mult = -1 if advance_amount < 0 else 1
    #         if sum(same_advance_lines.mapped(
    #                 'advance_amount')) > mult * advance_amount:
    #             raise ValidationError(
    #                 _("Total advance amount distributed cannot be greater than the selected advance"))
    #     total_amount_received = sum(self.bill_line_ids.mapped('amount_received'))
    #     if total_amount_received > self.amount:
    #         raise ValidationError(
    #             _("Total Paid Amount cannot be greater than the given amount"))


class BillPaymentLines(models.Model):
    _name = "bill.payment.line"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Bill Payment Lines'
    """Bill Payment Lines"""

    bill_payment_id = fields.Many2one('bill.payment')
    bill_id = fields.Many2one('account.move')
    operator_id = fields.Many2one('res.company', related='bill_id.company_id')
    currency_id = fields.Many2one('res.currency', related='bill_id.currency_id')
    name = fields.Char('Bill #', related='bill_id.name')
    partner_id = fields.Many2one('res.partner', related='bill_id.partner_id')
    bill_date_due = fields.Date(related='bill_id.invoice_date_due')
    amount_total_view = fields.Float(related='bill_id.amount_total_view')
    amount_adjusted = fields.Float(compute='compute_amount_values')
    amount_residual = fields.Float()
    bill_amount_residual = fields.Monetary(related='bill_id.amount_residual')
    amount_residual_changed = fields.Boolean(
        compute='compute_amount_residual_changed')
    advance_amount = fields.Float()
    amount_received = fields.Float()
    due_amount = fields.Float(store=True, compute='compute_amount_values')
    advance_move_line_id = fields.Many2one('account.move.line',
                                           string='Advance',
                                           copy=False)
    have_advance_value = fields.Boolean()
    filter_advance_move_line_ids = fields.Many2many('account.move.line',
                                                    compute='_compute_filter_advance_move_line_ids')
    unapplied_amount = fields.Float(compute='compute_amount_values')

    @api.depends('bill_amount_residual', 'amount_residual')
    def compute_amount_residual_changed(self):
        for rec in self:
            if round(rec.amount_residual, rec.operator_id.decimal_precision) \
                    != round(rec.bill_amount_residual,
                             rec.operator_id.decimal_precision) \
                    and rec.bill_payment_id.state == 'draft':
                rec.amount_residual_changed = True
            else:
                rec.amount_residual_changed = False

    @api.depends('amount_total_view', 'amount_residual', 'advance_amount',
                 'amount_received')
    def compute_amount_values(self):
        for rec in self:
            rec.amount_adjusted = rec.amount_total_view - rec.amount_residual
            rec.due_amount = rec.amount_residual - rec.advance_amount - rec.amount_received
            rec.unapplied_amount = 0
            if rec.due_amount < 0:
                rec.unapplied_amount = -1 * rec.due_amount
                rec.due_amount = 0

    @api.depends('partner_id')
    def _compute_filter_advance_move_line_ids(self):
        for rec in self:
            advance_move_line = rec.bill_payment_id.advance_move_line_ids
            rec.filter_advance_move_line_ids = advance_move_line.ids

    @api.onchange('amount_received')
    def onchange_amount_received(self):
        if self.amount_residual_changed:
            raise ValidationError(
                _("Amount Balance is changed in the bill please update it here"))
        due_amount = self.amount_residual - self.advance_amount - self.amount_received
        if round(due_amount, 2) < 0:
            raise ValidationError(
                _("Amount Paid cannot be greater than the Balance"))

    @api.onchange('advance_amount')
    def onchange_advance_amount(self):
        if self.amount_residual_changed:
            raise ValidationError(
                _("Amount Balance is changed in the bill please update it here"))
        advance_amount = self.advance_move_line_id._origin.amount_residual
        mult = -1 if advance_amount < 0 else 1
        if self.advance_amount > mult * advance_amount or self.advance_amount > self.amount_residual:
            raise ValidationError(
                    _("Credit amount cannot be greater than the selected credit amount or balance amount"))
        # due_amount = self.amount_residual - self.advance_amount - self.amount_received
        # if due_amount < 0:
        #     raise ValidationError(
        #         _("Credit Amount cannot be greater than due amount"))

    @api.onchange('advance_move_line_id')
    def _onchange_advance_move_line_ids(self):
        if self.amount_residual_changed:
            raise ValidationError(
                _("Amount Balance is changed in the bill please update it here"))
        if self.advance_move_line_id:
            amount_used = 0
            for line in self.bill_payment_id.bill_line_ids:
                if line.advance_move_line_id == self.advance_move_line_id:
                    amount_used += line.advance_amount
            if amount_used == 0:
                self.have_advance_value = True
                advance_amount = self.advance_move_line_id._origin.amount_residual
                mult = -1 if advance_amount < 0 else 1
                if mult * advance_amount > self.amount_residual and mult * advance_amount > 0:
                    self.advance_amount = self.amount_residual - self.amount_received
                elif mult * advance_amount > 0:
                    self.advance_amount = mult * advance_amount
                else:
                    self.advance_amount = 0
            elif amount_used > 0:
                self.have_advance_value = True
                advance_amount = self.advance_move_line_id._origin.amount_residual
                mult = -1 if advance_amount < 0 else 1
                advance = (mult * advance_amount) - amount_used
                if advance > self.amount_residual and advance > 0:
                    self.advance_amount = self.amount_residual - self.amount_received
                elif advance > 0:
                    self.advance_amount = advance
                else:
                    self.advance_amount = 0
        else:
            self.have_advance_value = False
            self.advance_amount = 0

    def update_amount_residual(self):
        self.amount_residual = self.bill_amount_residual
