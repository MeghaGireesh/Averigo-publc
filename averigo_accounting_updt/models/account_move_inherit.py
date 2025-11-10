import json
import logging
from odoo import models, fields, api, _
from odoo.tools import float_is_zero
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AverigoAccountMoveInherit(models.Model):
    _inherit = 'account.move'

    validation_check = fields.Boolean(string="Has price zero or not",
                                      compute="_compute_price")
    invoice_payment_state = fields.Selection(selection=[
        ('not_paid', 'Unpaid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid')],
        string='Payment', store=True, readonly=True, copy=False, tracking=True,
        compute='_compute_amount')
    po_no = fields.Char('PO #')
    check_quantity = fields.Boolean(compute="_compute_price")
    tax_rate_is = fields.Boolean(default = True)

    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(AverigoAccountMoveInherit, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        try:
            invoice_action_id = self.env.ref('account.action_account_invoice_from_list').id
            bill_action_id = self.env.ref('averigo_accounting_updt.action_account_bill_from_list').id
            move_type = self._context.get('default_type', False)
            for button in res.get('toolbar', {}).get('action', []):
                if move_type == 'in_invoice' and button['id'] == invoice_action_id:
                    res['toolbar']['action'].remove(button)
                elif move_type == 'out_invoice' and button['id'] == bill_action_id:
                    res['toolbar']['action'].remove(button)
        except ValueError:
            pass
        return res

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        res = super(AverigoAccountMoveInherit, self)._onchange_partner_id()
        if self.partner_id and self.partner_id.po_check:
            self.po_no = self.partner_id.po_no
        else:
            self.po_no = False
        return res

    def _move_autocomplete_invoice_lines_values(self):
        """AV-3174"""
        # '''Overwrite exiting function for description on the line and set it as non-changeable AV-3174
        '''This method recomputes dynamic lines on the current journal entry that include taxes, cash rounding
        and payment terms lines.
        '''
        self.ensure_one()

        line_currency = self.currency_id if self.currency_id != self.company_id.currency_id else False
        for line in self.line_ids.filtered(lambda l: not l.display_type):
            # Do something only on invoice lines.
            if line.exclude_from_invoice_tab:
                continue

            # Shortcut to load the demo data.
            # Doing line.account_id triggers a default_get(['account_id']) that could returns a result.
            # A section / note must not have an account_id set.
            if not line._cache.get('account_id') and not line._origin:
                line.account_id = line._get_computed_account()
                if not line.account_id:
                    if self.is_sale_document(include_receipts=True):
                        line.account_id = self.journal_id.default_credit_account_id
                    elif self.is_purchase_document(include_receipts=True):
                        line.account_id = self.journal_id.default_debit_account_id
            if line.product_id and not line._cache.get('name'):
                # line.name = line.name if line and line.name else line._get_computed_name()
                """updated function for showing description on the invoice line from sale order line AV-3174"""
                if line and line.name:
                    line.name = line.name
                elif line.sale_line_id:
                    line.name = line.sale_line_id.desc
                else:
                    line._get_computed_name()
                # line.name = line._get_computed_name()

            # Compute the account before the partner_id
            # In case account_followup is installed
            # Setting the partner will get the account_id in cache
            # If the account_id is not in cache, it will trigger the default value
            # Which is wrong in some case
            # It's better to set the account_id before the partner_id
            # Ensure related fields are well copied.
            line.partner_id = self.partner_id.commercial_partner_id
            line.date = self.date
            line.recompute_tax_line = True
            line.currency_id = line_currency


        self.line_ids._onchange_price_subtotal()
        self._recompute_dynamic_lines(recompute_all_taxes=True)

        values = self._convert_to_write(self._cache)
        values.pop('invoice_line_ids', None)
        return values


    def action_post(self):
        if len(self.invoice_line_ids) == 0:
            raise UserError('There is no product added')
        elif all(line.quantity == 0 for line in self.invoice_line_ids):
            raise UserError('The entered product quantity is zero')
        rec = super(AverigoAccountMoveInherit, self).action_post()
        if not self.is_misc_receipt:
            if self.mapped('line_ids.payment_id') and any(
                    post_at == 'bank_rec' for post_at in
                    self.mapped('journal_id.post_at')):
                raise UserError(_(
                    "A payment journal entry generated in a journal configured"
                    " to post entries only when payments are reconciled with a "
                    "bank statement cannot be manually posted. Those will be "
                    "posted automatically after performing the bank "
                    "reconciliation."))
            # return self.post()
        return rec

    # AV-2192
    @api.depends('invoice_line_ids')
    def _compute_price(self):
        for rec in self:
            rec.validation_check = False
            rec.check_quantity = False
            for record in rec.invoice_line_ids:
                _logger.info(f'check price_unitttttttt {record.price_unit}')
                if record.price_unit == 0 and record.product_id.product_type != 'service':
                    rec.validation_check = True
                """AV-2974"""
                if record.quantity <= 0 and record.product_id and record.product_id.product_type != 'service':
                    rec.check_quantity = True


    def _compute_payments_widget_to_reconcile_info(self):
        for move in self:
            move.invoice_outstanding_credits_debits_widget = json.dumps(False)
            move.invoice_has_outstanding = False

            if move.state != 'posted' or move.invoice_payment_state != 'not_paid' or not move.is_invoice(
                    include_receipts=True):
                continue
            pay_term_line_ids = move.line_ids.filtered(
                lambda line: line.account_id.user_type_id.type in (
                    'receivable', 'payable'))

            domain = [('account_id', 'in',
                       pay_term_line_ids.mapped('account_id').ids),
                      '|', ('move_id.state', '=', 'posted'), '&',
                      ('move_id.state', '=', 'draft'),
                      ('journal_id.post_at', '=', 'bank_rec'),
                      ('partner_id', '=', move.commercial_partner_id.id),
                      ('reconciled', '=', False), '|',
                      ('amount_residual', '!=', 0.0),
                      ('amount_residual_currency', '!=', 0.0)]

            if move.is_inbound():
                domain.extend([('credit', '>', 0), ('debit', '=', 0)])
                type_payment = _('Outstanding Credits')
            else:
                domain.extend([('credit', '=', 0), ('debit', '>', 0)])
                type_payment = _('Outstanding Debits')
            info = {'title': '', 'outstanding': True, 'content': [],
                    'move_id': move.id}
            lines = self.env['account.move.line'].search(domain)
            currency_id = move.currency_id
            if len(lines) != 0:
                for line in lines:
                    # get the outstanding residual value in invoice currency
                    if line.currency_id and line.currency_id == move.currency_id:
                        amount_to_show = abs(line.amount_residual_currency)
                    else:
                        currency = line.company_id.currency_id
                        amount_to_show = currency._convert(
                            abs(line.amount_residual), move.currency_id,
                            move.company_id,
                            line.date or fields.Date.today())
                    if float_is_zero(amount_to_show,
                                     precision_rounding=move.currency_id.rounding):
                        continue
                    info['content'].append({
                        'journal_name': line.ref or line.move_id.name,
                        'amount': amount_to_show,
                        'currency': currency_id.symbol,
                        'id': line.id,
                        'position': currency_id.position,
                        'digits': [69, move.currency_id.decimal_places],
                        'payment_date': fields.Date.to_string(line.date),
                    })
                info['title'] = type_payment
                move.invoice_outstanding_credits_debits_widget = json.dumps(
                    info)
                move.invoice_has_outstanding = True

    def action_payment_receipt(self, selected_ids):
        active_ids = self.env.context.get('active_ids')
        selected_invoices = self.env['account.move'].browse(active_ids)
        draft_invoices = selected_invoices.filtered(
            lambda l: l.state == 'draft')
        zero_invoices = selected_invoices.filtered(
            lambda l: l.amount_residual == 0)
        partner = selected_invoices.mapped("partner_id")
        if not len(selected_invoices):
            raise UserError(_("No Invoice Selected."))
        if len(draft_invoices):
            raise UserError(
                _("We can't create the Payment Receipt for a draft invoice."))
        if len(zero_invoices):
            raise UserError(
                _("We can't create the Payment Receipt for fully paid invoice."))
        if len(partner.ids) > 1:
            raise UserError(
                _("You can't do the payment receipt for different customers."))

        return self.create_receipt_records(partner, selected_invoices.filtered(
            lambda l: l.state == 'posted' and l.amount_residual > 0), True)

    def action_bill_payment(self, selected_ids):
        active_ids = self.env.context.get('active_ids')
        selected_bills = self.env['account.move'].browse(active_ids)
        draft_invoices = selected_bills.filtered(
            lambda l: l.state == 'draft')
        zero_invoices = selected_bills.filtered(
            lambda l: l.invoice_payment_state == 'paid')
        partner = selected_bills.mapped("partner_id")
        if not len(selected_bills):
            raise UserError(_("No Bill Selected."))
        if len(draft_invoices):
            raise UserError(
                _("We can't create the Payment Receipt for a draft Bills."))
        if len(zero_invoices):
            raise UserError(
                _("We can't create the Payment Receipt for fully paid Bills."))
        if len(partner.ids) > 1:
            raise UserError(
                _("You can't do the Bill Payment for different Vendors."))
        return self.create_bill_payment(partner, selected_bills.filtered(
            lambda l: l.state == 'posted' and l.amount_residual > 0), True)

    def create_bill_payment(self,partner,bills,add_select_all=False):
        move_ids = bills
        domain = [('partner_id', '=', partner.id),
                  ('reconciled', '=', False),
                  ('debit', '>', 0), ('parent_state', '=', 'posted'),
                  ('account_internal_type', '=', 'payable'),
                  ('company_id', '=', self.company_id.id)]
        advance_move_line = self.env['account.move.line'].sudo().search(
            domain)
        advance_list = []
        if advance_move_line:
            for record in advance_move_line:
                adv_vals = (0, 0, {
                    # 'invoice_payment_id': self.id,
                    'advance_id': record._origin.id,
                    'partner_id': record._origin.partner_id.id,
                    'total_amount': record._origin.debit,
                    'applied_amount': record._origin.credit_value,
                    'balance_amount': record._origin.bal_val
                })
                advance_list.append(adv_vals)
        mult = -1 if sum(
            advance_move_line.mapped('amount_residual')) < 0 else 1
        vendor_advance_balance = mult * sum(
            advance_move_line.mapped('amount_residual'))
        bill_balance = sum(move_ids.mapped('amount_residual'))
        bill_list = []
        length = len(move_ids)
        amount = 0
        if move_ids:
            for move_id in move_ids:
                if move_id.id == self.id:
                    amount = move_id.amount_residual
                    vals = (0, 0, {
                        'bill_id': move_id.id,
                        'name': move_id.name,
                        'amount_total_view': move_id.amount_total_view,
                        'bill_date_due': move_id.invoice_date_due,
                        'amount_adjusted': move_id.amount_total_view - move_id.amount_residual,
                        'amount_residual': move_id.amount_residual,
                        'due_amount': 0,
                        'partner_id': move_id.partner_id.id,
                        'filter_advance_move_line_ids': advance_move_line.ids,
                        'is_checked': True,
                        'amount_received': move_id.amount_residual
                    })
                    bill_list.append(vals)
                else:
                    vals = (0, 0, {
                        'bill_id': move_id.id,
                        'name': move_id.name,
                        'amount_total_view': move_id.amount_total_view,
                        'bill_date_due': move_id.invoice_date_due,
                        'amount_residual': move_id.amount_residual,
                        'is_checked': add_select_all,
                        'amount_received': 0,
                        'amount_adjusted': move_id.amount_total_view - move_id.amount_residual,
                        'filter_advance_move_line_ids': advance_move_line.ids,
                        'due_amount': move_id.amount_residual,
                        'partner_id': move_id.partner_id.id
                    })
                    bill_list.append(vals)
        bank_type_id = self.env.ref(
            'account.data_account_type_liquidity').id
        account_ids = self.env['account.account'].search(
            [('user_type_id', '=', bank_type_id)])
        account_dom_ids = account_ids.ids
        journal_id = self.env['account.journal'].search(
            [('type', '=', 'bank')], limit=1)
        account_id = journal_id.default_credit_account_id.id
        context = {'default_partner_id': partner.id,
                        'default_bill_balance': bill_balance,
                        'default_vendor_advance_balance': vendor_advance_balance,
                        'default_bill_line_ids': [(2, 0, 0)] + bill_list,
                        'default_is_check': True,
                        'default_account_dom_ids': account_dom_ids,
                        'default_state': 'draft',
                        'default_amount': amount,
                        'default_advance_move_line_ids': advance_move_line.ids,
                        'default_bill_ids_len': length,
                                'default_is_direct_bill': True,
                        'default_journal_id': journal_id.id,
                        'default_account_id': account_id,
                        'default_bill_no': self.id,
                        'default_advance_payment_ids': [(2, 0, 0)] + advance_list,
                        }
        if add_select_all:
            context['default_add_select_all'] = add_select_all
        return {
            'name': _('Register Payment'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'bill.payment',
            'target': 'current',
            'context': context,
        }

    def action_register_payment(self):
        move_ids = self.env['account.move'].search(
            [('partner_id', '=', self.partner_id.id),
             ('type', '=', 'out_invoice'), ('state', '=', 'posted'),
             ('invoice_payment_state', '!=', 'paid')],
            order='invoice_date_due asc')
        return self.create_receipt_records(self.partner_id, move_ids)

    def create_receipt_records(self, partner_id, move_ids,
                               add_select_all=False):
        domain = ['|', ('advance', '=', True), ('credit', '>', 0),
                  ('partner_id', '=', partner_id.id),
                  ('reconciled', '=', False),
                  ('account_internal_type', '=', 'receivable'),
                  ('parent_state', '=', 'posted'),
                  ('company_id', '=', self.company_id.id)]
        advance_move_line = self.env['account.move.line'].sudo().search(
            domain)
        advance_list = []
        if advance_move_line:
            for record in advance_move_line:
                adv_vals = (0, 0, {
                    # 'invoice_payment_id': self.id,
                    'advance_id': record._origin.id,
                    'partner_id': record._origin.partner_id.id,
                    'total_amount': record._origin.credit,
                    'applied_amount': record._origin.advance_value,
                    'balance_amount': record._origin.balance_vale
                })
                advance_list.append(adv_vals)
        mult = -1 if sum(
            advance_move_line.mapped('amount_residual')) < 0 else 1
        cust_advance_balance = mult * sum(
            advance_move_line.mapped('amount_residual'))
        moves_ids = self.env['account.move'].search(
            [('partner_id', '=', self.partner_id.id),
             ('type', '=', 'out_invoice'), ('state', '=', 'posted'),
             ('invoice_payment_state', '!=', 'paid')])
        invoice_balance = sum(moves_ids.mapped('amount_residual'))
        journal_id = self.env['account.journal'].search(
            [('type', '=', 'bank')], limit=1)
        invoice_list = []
        length = len(move_ids)
        amount = 0
        if move_ids:
            for move_id in move_ids:
                if move_id.id == self.id:
                    amount = move_id.amount_residual
                    vals = (0, 0, {
                        'invoice_id': move_id.id,
                        'name': move_id.name,
                        'amount_total_view': move_id.amount_total_view,
                        'invoice_date_due': move_id.invoice_date_due,
                        'amount_adjusted': move_id.amount_total_view - move_id.amount_residual,
                        'amount_residual': move_id.amount_residual,
                        'due_amount': 0,
                        'partner_id': move_id.partner_id.id,
                        'filter_advance_move_line_ids': advance_move_line.ids,
                        'is_checked': True,
                        'amount_received': move_id.amount_residual
                    })
                    invoice_list.append(vals)
                else:
                    vals = (0, 0, {
                        'invoice_id': move_id.id,
                        'name': move_id.name,
                        'amount_total_view': move_id.amount_total_view,
                        'invoice_date_due': move_id.invoice_date_due,
                        'amount_residual': move_id.amount_residual,
                        'is_checked': add_select_all,
                        'amount_received': 0,
                        'amount_adjusted': move_id.amount_total_view - move_id.amount_residual,
                        'due_amount': move_id.amount_residual,
                        'partner_id': move_id.partner_id.id,
                        'filter_advance_move_line_ids': advance_move_line.ids
                    })

                    invoice_list.append(vals)

        bank_type_id = self.env.ref(
            'account.data_account_type_liquidity').id
        account_ids = self.env['account.account'].search(
            [('user_type_id', '=', bank_type_id)])
        account_dom_ids = account_ids.ids
        context = {'default_partner_id': partner_id.id,
                   'default_is_direct_invoice': True,
                   'default_invoice_balance': invoice_balance,
                   'default_cust_advance_balance': cust_advance_balance,
                   'default_invoice_ids': [(2, 0, 0)] + invoice_list,
                   'default_is_check': True,
                   'default_account_dom_ids': account_dom_ids,
                   'default_amount': amount,
                   'default_advance_move_line_ids': advance_move_line.ids,
                   'default_state': 'draft',
                   'default_journal_id': journal_id.id,
                   'default_invoice_ids_len': length,
                   'default_advance_payment_ids': [(2, 0, 0)] + advance_list,
                   }

        if add_select_all:
            context['default_add_select_all'] = add_select_all
        return {
            'name': _('Register Payment'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': self.env.ref(
                'averigo_accounting.view_invoice_receipt_form').id,
            'res_model': 'invoice.receipt',
            'target': 'current',
            'context': context
        }

    def action_bill_register_payment(self):
        move_ids = self.env['account.move'].search(
            [('partner_id', '=', self.partner_id.id),
             ('type', '=', 'in_invoice'), ('state', '=', 'posted'),
             ('invoice_payment_state', '!=', 'paid')],
            order='invoice_date_due asc')
        domain = [('partner_id', '=', self.partner_id.id),
                  ('reconciled', '=', False),
                  ('debit', '>', 0), ('parent_state', '=', 'posted'),
                  ('account_internal_type', '=', 'payable'),
                  ('company_id', '=', self.company_id.id)]
        advance_move_line = self.env['account.move.line'].sudo().search(
            domain)
        advance_list = []
        if advance_move_line:
            for record in advance_move_line:
                adv_vals = (0, 0, {
                    # 'invoice_payment_id': self.id,
                    'advance_id': record._origin.id,
                    'partner_id': record._origin.partner_id.id,
                    'total_amount': record._origin.debit,
                    'applied_amount': record._origin.credit_value,
                    'balance_amount': record._origin.bal_val
                })
                advance_list.append(adv_vals)
        mult = -1 if sum(
            advance_move_line.mapped('amount_residual')) < 0 else 1
        vendor_advance_balance = mult * sum(
            advance_move_line.mapped('amount_residual'))
        bill_balance = sum(move_ids.mapped('amount_residual'))
        bill_list = []
        length = len(move_ids)
        amount = 0
        if move_ids:
            for move_id in move_ids:
                if move_id.id == self.id:
                    amount = move_id.amount_residual
                    vals = (0, 0, {
                        'bill_id': move_id.id,
                        'name': move_id.name,
                        'amount_total_view': move_id.amount_total_view,
                        'bill_date_due': move_id.invoice_date_due,
                        'amount_adjusted': move_id.amount_total_view - move_id.amount_residual,
                        'amount_residual': move_id.amount_residual,
                        'due_amount': 0,
                        'partner_id': move_id.partner_id.id,
                        'filter_advance_move_line_ids': advance_move_line.ids,
                        'is_checked': True,
                        'amount_received': move_id.amount_residual
                    })
                    bill_list.append(vals)
                else:
                    vals = (0, 0, {
                        'bill_id': move_id.id,
                        'name': move_id.name,
                        'amount_total_view': move_id.amount_total_view,
                        'bill_date_due': move_id.invoice_date_due,
                        'amount_residual': move_id.amount_residual,
                        'is_checked': False,
                        'amount_received': 0,
                        'amount_adjusted': move_id.amount_total_view - move_id.amount_residual,
                        'filter_advance_move_line_ids': advance_move_line.ids,
                        'due_amount': move_id.amount_residual,
                        'partner_id': move_id.partner_id.id
                    })
                    bill_list.append(vals)
        bank_type_id = self.env.ref(
            'account.data_account_type_liquidity').id
        account_ids = self.env['account.account'].search(
            [('user_type_id', '=', bank_type_id)])
        account_dom_ids = account_ids.ids
        journal_id = self.env['account.journal'].search(
            [('type', '=', 'bank')], limit=1)
        account_id = journal_id.default_credit_account_id.id
        return {
            'name': _('Register Payment'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'bill.payment',
            'target': 'current',
            'context': {'default_partner_id': self.partner_id.id,
                        'default_bill_balance': bill_balance,
                        'default_vendor_advance_balance': vendor_advance_balance,
                        'default_bill_line_ids': [(2, 0, 0)] + bill_list,
                        'default_is_check': True,
                        'default_account_dom_ids': account_dom_ids,
                        'default_state': 'draft',
                        'default_amount': amount,
                        'default_advance_move_line_ids': advance_move_line.ids,
                        'default_bill_ids_len': length,
                        'default_is_direct_bill': True,
                        'default_journal_id': journal_id.id,
                        'default_account_id': account_id,
                        'default_bill_no': self.id,
                        'default_advance_payment_ids': [(2, 0, 0)] + advance_list,
                        },
        }


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    advance_value = fields.Float('Advance Payment Journal',
                                 compute="compute_advance_used",
                                 help="Used to identify the advance payment journal")
    balance_vale = fields.Float('Advance Payment Journal',
                                compute="compute_advance_used",
                                help="Used to identify the advance payment journal")

    credit_value = fields.Float('Credit Payment Journal',
                                compute="compute_credit_used",
                                help="The credit payment journal")
    bal_val = fields.Float('Balance Credit',
                           compute="compute_credit_used",
                           help="Balance")
    product_code = fields.Char('Product code', compute="compute_product_code")

    @api.depends('product_id')
    def compute_product_code(self):
        for rec in self:
            if rec.product_id and rec.product_id.default_code:
                rec.product_code = rec.product_id.default_code
            else:
                rec.product_code = ''
    #

    def compute_advance_used(self):
        for rec in self:
            amount_residual = 0
            if rec.amount_residual < 0:
                amount_residual = abs(rec.amount_residual)
            # rec.advance_value = 0
            # lines = rec._reconciled_lines()
            # applied_amount = 0
            # credit_amount = 0
            # for line in lines:
            #     record = self.env['account.move.line'].search(
            #         [('id', '=', line), (
            #             'display_type', 'not in',
            #             ('line_section', 'line_note'))])
            #     applied_amount += record.debit
            #     credit_amount += record.credit

            rec.advance_value = rec.credit - amount_residual
            rec.balance_vale = amount_residual

    def compute_credit_used(self):
        for rec in self:
            rec.credit_value = rec.debit - rec.amount_residual
            rec.bal_val = rec.amount_residual
