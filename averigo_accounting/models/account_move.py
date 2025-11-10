from odoo import models, fields, api, _
from datetime import date
from odoo.exceptions import UserError
from lxml import etree

import logging
_logger = logging.getLogger(__name__)


class AverigoAccountMove(models.Model):
    _inherit = 'account.move'
    _description = "Invoice/BIll"

    bill_ids = fields.Many2many('account.move', 'account_move_bill_ids_rel',
                                'move_ids', 'bill_id')

    def _get_payment_mode_id(self):
        payment_mode_id = self.env['account.payment.mode'].search(
            [('type', '=', 'check')], limit=1)
        return payment_mode_id

    @api.model
    def _get_default_journal(self):
        ''' Get the default journal.
        It could either be passed through the context using the 'default_journal_id' key containing its id,
        either be determined by the default type.
        '''
        if self._context.get('default_is_misc_receipt'):
            print("test")
            domain = [('type', 'in', ('cash', 'bank'))]
            journal = self.env['account.journal'].search(domain, limit=1)
            if self._context.get('default_currency_id'):
                currency_domain = domain + [
                    ('currency_id', '=', self._context['default_currency_id'])]
                journal = self.env['account.journal'].search(currency_domain,
                                                             limit=1)
            return journal

        else:
            move_type = self._context.get('default_type', 'entry')
            journal_type = 'general'
            if move_type in self.get_sale_types(include_receipts=True):
                journal_type = 'sale'
            elif move_type in self.get_purchase_types(include_receipts=True):
                journal_type = 'purchase'

            if self._context.get('default_journal_id'):
                journal = self.env['account.journal'].browse(
                    self._context['default_journal_id'])

                '''The if condition (added extra condition) changed due to an 
                error while posting the Direct Bill and Direct Invoice '''
                if move_type != 'entry' and journal.type != journal_type and \
                        self._context.get('default_type') not in ['in_invoice',
                                                                  'out_invoice']:
                    raise UserError(
                        _("Cannot create an invoice of type %s with a journal "
                          "having %s as type.") % (
                            move_type, journal.type))
            else:
                company_id = self._context.get('force_company',
                                               self._context.get(
                                                   'default_company_id',
                                                   self.env.company.id))
                domain = [('company_id', '=', company_id),
                          ('type', '=', journal_type)]

                journal = None
                if self._context.get('default_currency_id'):
                    currency_domain = domain + [('currency_id', '=',
                                                 self._context[
                                                     'default_currency_id'])]
                    journal = self.env['account.journal'].search(
                        currency_domain, limit=1)

                if not journal:
                    journal = self.env['account.journal'].search(domain,
                                                                 limit=1)

                if not journal:
                    error_msg = _(
                        'Please define an accounting miscellaneous journal in your company')
                    if journal_type == 'sale':
                        error_msg = _(
                            'Please define an accounting sale journal in your company')
                    elif journal_type == 'purchase':
                        error_msg = _(
                            'Please define an accounting purchase journal in your company')
                    raise UserError(error_msg)
            return journal

    is_misc_receipt = fields.Boolean()
    receipt_type = fields.Selection([
        ('vendors', 'Vendors'),
        ('others', 'Others'),
    ], default='others', required=True, )
    payment_amount = fields.Float()
    vendor_adv_balance = fields.Float()
    bank_name = fields.Char()
    authorisation_code = fields.Char()
    transaction_ref = fields.Char()
    check_ref = fields.Char()
    credit_card_ref = fields.Char()
    name_on_card = fields.Char()
    payer_name = fields.Char()
    payment_date = fields.Date()
    card_expiry_date = fields.Date()
    receipt_distribution_lines = fields.One2many('receipt.credit.distribution',
                                                 'move_id',
                                                 String="Order Line")
    account_id = fields.Many2one('account.account')
    journal_id = fields.Many2one('account.journal', string='Journal',
                                 required=True, default=_get_default_journal,
                                 domain=[('type', '=', 'general')])
    payment_mode_id = fields.Many2one('account.payment.mode',
                                      string="Mode Of Payment",
                                      default=_get_payment_mode_id)
    payment_mode = fields.Char()
    check_id = fields.Many2one('res.partner.check', string="Check",
                               domain="[('id', 'not in', compute_check_ids), ('is_vendor', '=', True), ('is_advance', '=', True)]")
    compute_check_ids = fields.Many2many('res.partner.check',
                                         compute='_compute_suitable_check_ids')
    total_container_deposit_view = fields.Float(compute='compute_total_tax')
    total_sales_tax_amount_view = fields.Float(compute='compute_total_tax')
    vendor_advance = fields.Boolean(default=False,
                                    help="Used to get the vendor advance payment entry")
    customer_advance = fields.Boolean(default=False,
                                      help="Used to get the customer advance payment entry")
    #
    # def add_invoice_products(self):
    #     products = self.product_ids
    #     customer_products = self.partner_id.customer_product_ids
    #     customer_product_ids = customer_products.mapped('product_id').ids
    #     for product in products:
    #         if product.id in customer_product_ids:
    #             customer_product = customer_products.filtered(
    #                 lambda s: s.product_id.id == product.id)
    #             self.write({
    #                 'invoice_line_ids': [(0, 0, {
    #                     'name': customer_product.product_id.name,
    #                     'quantity': 1,
    #                     'price_unit': customer_product.list_price,
    #                     'product_id': customer_product.product_id.id,
    #                     'product_uom_id': customer_product.uom_id.id,
    #                 })]
    #             })
    #         else:
    #             self.write({
    #                 'invoice_line_ids': [(0, 0, {
    #                     'name': product.name,
    #                     'quantity': 1,
    #                     'price_unit': product.list_price,
    #                     'product_id': product.id,
    #                     'product_uom_id': product.uom_id.id,
    #                 })]
    #             })
    #     discount_amount_line = self.line_ids.filtered(
    #         lambda s: s.discount_amount_line is True)
    #     if not discount_amount_line:
    #         discount_amount_line = {
    #             'name': 'Discount',
    #             'quantity': 1,
    #             'partner_id': self.partner_id.id,
    #             'price_unit': - self.total_discount,
    #             'exclude_from_invoice_tab': True,
    #             'discount_amount_line': True,
    #         }
    #         self.write({'invoice_line_ids': [(0, 0, discount_amount_line)]})
    #     insurance_amount_line = self.line_ids.filtered(
    #         lambda s: s.insurance_amount_line is True)
    #     if not insurance_amount_line:
    #         insurance_amount_line = {
    #             'name': 'Insurance',
    #             'quantity': 1,
    #             'partner_id': self.partner_id.id,
    #             'price_unit': self.insurance,
    #             'exclude_from_invoice_tab': True,
    #             'insurance_amount_line': True,
    #         }
    #         self.write({'invoice_line_ids': [(0, 0, insurance_amount_line)]})
    #     shipping_handling_amount_line = self.line_ids.filtered(
    #         lambda s: s.shipping_handling_amount_line is True)
    #     if not shipping_handling_amount_line:
    #         shipping_handling_amount_line = {
    #             'name': 'S & H',
    #             'quantity': 1,
    #             'partner_id': self.partner_id.id,
    #             'price_unit': self.shipping_handling,
    #             'exclude_from_invoice_tab': True,
    #             'shipping_handling_amount_line': True,
    #         }
    #         self.write(
    #             {'invoice_line_ids': [(0, 0, shipping_handling_amount_line)]})
    #     container_deposit_line = self.line_ids.filtered(
    #         lambda s: s.container_deposit_line is True)
    #     if not container_deposit_line:
    #         container_deposit_line = {
    #             'name': 'Container Deposit amount',
    #             'quantity': 1,
    #             'partner_id': self.partner_id.id,
    #             'price_unit': self.total_container_deposit,
    #             'exclude_from_invoice_tab': True,
    #             'container_deposit_line': True,
    #         }
    #         self.write({'invoice_line_ids': [(0, 0, container_deposit_line)]})
    #     tax_line = self._origin.line_ids.filtered(
    #         lambda s: s.tax_amount_line is True)
    #     _logger.info('ddddddddddddddddd_jaan_14_27')
    #     _logger.info(self.tax_amount_view)
    #     if not tax_line:
    #         tax_line = {
    #             'name': 'Tax',
    #             'quantity': 1,
    #             'partner_id': self.partner_id.id,
    #             'price_unit': self.tax_amount_view,
    #             'exclude_from_invoice_tab': True,
    #             'tax_amount_line': True,
    #         }
    #         self.write({'invoice_line_ids': [(0, 0, tax_line)]})
    #     self.product_ids = None

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
                        submenu=False):
        res = super(AverigoAccountMove, self).fields_view_get(view_id=view_id,
                                                              view_type=view_type,
                                                              toolbar=toolbar,
                                                              submenu=submenu)
        doc = etree.XML(res['arch'])
        if self._context.get('default_direct_invoice'):
            if res.get('toolbar', False) and res.get('toolbar').get('print',
                                                                    False):
                vendor_bill = list(
                    filter(lambda x: x[
                                         'report_file'] == 'averigo_purchase.report_bill_document',
                           res['toolbar'].get('print')))
                if vendor_bill:
                    res['toolbar']['print'].remove(vendor_bill[0])
        if self._context.get('default_direct_bill'):
            if res.get('toolbar', False) and res.get('toolbar').get('print',
                                                                    False):
                reports = res.get('toolbar').get('print')
                actions = res.get('toolbar').get('action')
                credit_action = list(filter(
                    lambda x: x['name'] == 'Switch into Refund/Credit note',
                    actions))
                if credit_action:
                    credit_action[0]['name'] = 'Switch into Void/Debit Note'
                invoices = list(
                    filter(lambda x: x[
                                         'report_file'] == 'averigo_sales_order.report_invoice_document',
                           reports))
                if invoices:
                    invoices[0]['name'] = 'Bills'
                invoices_without_label = list(
                    filter(
                        lambda x: x['report_file'] == 'account.report_invoice',
                        reports))
                if invoices_without_label:
                    invoices_without_label[0]['name'] = 'Bills Without Payment'
                invoice_print = list(
                    filter(lambda x: x[
                                         'report_file'] == 'averigo_sales_order.report_invoice_document',
                           res['toolbar'].get('print')))
                if invoice_print:
                    res['toolbar']['print'].remove(invoice_print[0])
                invoices_without_payment = list(
                    filter(
                        lambda x: x['report_file'] == 'account.report_invoice',
                        res['toolbar'].get('print')))
                if invoices_without_payment:
                    res['toolbar']['print'].remove(invoices_without_payment[0])
                original_vendor_bill = list(
                    filter(lambda x: x[
                                         'report_file'] == 'account.report_original_vendor_bill',
                           res['toolbar'].get('print')))
                if original_vendor_bill:
                    res['toolbar']['print'].remove(original_vendor_bill[0])
        return res

    @api.depends('invoice_line_ids.container_deposit_amount',
                 'invoice_line_ids.discount_amount',
                 'invoice_line_ids.sales_tax_amount',
                 'invoice_line_ids.price_subtotal')
    def compute_total_tax(self):
        for rec in self:
            total_container_deposit = 0.0
            total_tax = 0.0

            for line in rec.invoice_line_ids:
                tot_container_deposit_amount = line.quantity * line.container_deposit_amount
                tot_tax = line.quantity * line.sales_tax_amount
                total_container_deposit += tot_container_deposit_amount
                total_tax += tot_tax

            rec.update({
                'total_container_deposit_view': rec.currency_id.round(
                    total_container_deposit),
                'total_sales_tax_amount_view': rec.currency_id.round(
                    total_tax),
            })

    def action_invoice_register_payment(self):
        quick_pay = bool(self.env.context.get('quick_pay'))
        if quick_pay:
            company = self.env.company
            bank_journal = self.env['account.journal'].search(
                [('type', '=', 'bank'), ('code', '=', 'WRT1'),
                 ('company_id', '=', company.id)])
            self.env['account.payment'].create({
                'payment_method_id': self.env.ref(
                    "account.account_payment_method_manual_in").id,
                'partner_id': self.partner_id.id,
                'payment_type': 'inbound',
                'invoice_ids': [(6, False, self.ids)],
                'amount': self.amount_residual,
                'currency_id': company.currency_id.id,
                'payment_date': date.today(),
                'journal_id': bank_journal.id,
                'partner_type': 'customer',
            }).post()
        else:
            return self.env['account.payment'] \
                .with_context(active_ids=self.ids, active_model='account.move',
                              active_id=self.id) \
                .action_register_payment()

    @api.depends('partner_id')
    def _compute_suitable_check_ids(self):
        for rec in self:
            journal_id = rec.env['account.payment'].search(
                [('invoice_ids', 'in', rec.ids)]).journal_id.ids
            domain = [('advance', '=', True), ('journal_id', 'in', journal_id),
                      ('account_id.internal_type', '=', 'payable'),
                      ('reconciled', '=', True),
                      ('partner_id', '=', rec.partner_id.id)]
            check_ids = self.env['account.move.line'].search(domain).mapped(
                'check_id')
            rec.compute_check_ids = check_ids

    @api.onchange('payment_mode_id')
    def _onchange_payment_mode_id(self):
        self.payment_mode = self.payment_mode_id.name
        self.is_advance = True if self.payment_mode_id.type == 'advance' else False
        self.is_check = True if self.payment_mode_id.type == 'check' else False
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
        self.account_id = self.journal_id.default_debit_account_id.id

    @api.onchange('receipt_type')
    def change_receipt_type(self):
        self.receipt_distribution_lines = None
        self.line_ids = None
        self.invoice_line_ids = None
        if self.receipt_type == 'vendors':
            active_vendors = self.env['account.payment'].search(
                [('company_id', '=', self.env.user.company_id.id),
                 ('payment_type', '=', 'outbound'),
                 ('state', '=', 'posted')]).mapped('partner_id')
            return {
                'domain': {'partner_id': [('id', "=", active_vendors.ids)]}}

    @api.onchange('card_expiry_date')
    def change_card_expiry_date(self):
        if self.card_expiry_date:
            if self.card_expiry_date < date.today():
                raise UserError(_('Card Expired'))

    @api.onchange('payment_amount', 'account_id', 'receipt_distribution_lines')
    def invoice_line_ids_onchange(self):
        credit_line = []
        if self.is_misc_receipt:
            if self.account_id and self.payment_amount and self.receipt_type == 'vendors':

                invoice_move_line = {

                    'account_id': self.account_id.id,
                    'price_unit': self.payment_amount,
                    'debit': self.payment_amount,

                }
                self.invoice_line_ids = [(0, 0, invoice_move_line), ]
                self._onchange_invoice_line_ids()
            elif self.receipt_type == 'others':
                # self.invoice_line_ids = None

                self.line_ids = None
                for line in self.receipt_distribution_lines:
                    amount_line = (0, 0, {
                        'credit': line.amount,
                        'account_id': line.account_id.id,
                        'exclude_from_invoice_tab': True,
                        'extra_amount_line': False,
                    })
                    credit_line.append(amount_line)

                debit_line = {
                    'account_id': self.account_id.id,
                    'price_unit': self.payment_amount,
                    'debit': self.payment_amount,

                }

                self.line_ids = [(0, 0, debit_line), ] + credit_line

    def action_post(self):
        rec = super(AverigoAccountMove, self).action_post()
        # if self.is_misc_receipt:
        # print("rec",rec)
        # rec._compute_payments_widget_to_reconcile_info()
        if not self.is_misc_receipt:
            if self.mapped('line_ids.payment_id') and any(
                    post_at == 'bank_rec' for post_at in
                    self.mapped('journal_id.post_at')):
                raise UserError(_(
                    "A payment journal entry generated in a journal configured to post entries only when payments are reconciled with a bank statement cannot be manually posted. Those will be posted automatically after performing the bank reconciliation."))
            # return self.post()
        return rec

    def action_invoice_register_payment(self):
        quick_pay = bool(self.env.context.get('quick_pay'))
        if quick_pay:
            company = self.env.company
            bank_journal = self.env['account.journal'].search(
                [('type', '=', 'bank'), ('code', '=', 'WRT1'),
                 ('company_id', '=', company.id)])
            self.env['account.payment'].create({
                'payment_method_id': self.env.ref(
                    "account.account_payment_method_manual_in").id,
                'partner_id': self.partner_id.id,
                'payment_type': 'inbound',
                'invoice_ids': [(6, False, self.ids)],
                'amount': self.amount_residual,
                'currency_id': company.currency_id.id,
                'payment_date': date.today(),
                'journal_id': bank_journal.id,
                'partner_type': 'customer',
            }).post()
        else:
            return self.env['account.payment'] \
                .with_context(active_ids=self.ids, active_model='account.move',
                              active_id=self.id) \
                .action_register_payment()


class AverigoAccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    advance = fields.Boolean('Advance Payment Journal',
                             help="Used to identify the advance payment journal")
    check_id = fields.Many2one('res.partner.check', string="Check")
    payment_mode_id = fields.Many2one('account.payment.mode',
                                      string="Mode Of Payment")

    @api.depends('ref', 'move_id')
    def name_get(self):
        result = []
        for line in self:
            name = line.move_id.name or ''
            if line.ref:
                name += " (%s)" % line.ref
            if line.amount_residual and self._context.get('advance_payment'):
                name += " %s" % '(' + _("Amount : ") + str(
                    line.amount_residual) + ')'
            name += (line.name or line.product_id.display_name) and (
                    ' ' + (line.name or line.product_id.display_name)) or ''
            result.append((line.id, name))
        return result


class ReceiptCreditDistribution(models.Model):
    _name = 'receipt.credit.distribution'

    account_id = fields.Many2one('account.account',
                                 domain="[('internal_type', '=', 'other'),('deprecated', '=', False)]")
    amount = fields.Float()
    notes = fields.Text()
    move_id = fields.Many2one('account.move')
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id')
