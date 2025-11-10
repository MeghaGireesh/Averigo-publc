from odoo import models, api, fields, _


class AverigoAccountPaymentInherit(models.Model):
    _inherit = 'account.payment'

    partner_id = fields.Many2one('res.partner', string="Vendor/Customer",
                                 tracking=True,
                                 readonly=True,
                                 states={'draft': [('readonly', False)]},
                                 domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    check_id = fields.Many2one('res.partner.check', string='Check Number',
                               states={'draft': [('readonly', False)]})
    balance_advance = fields.Float('Advance Balance',
                                   compute="_compute_balance_advance")

    @api.onchange('partner_id')
    def _compute_customer_debit(self):
        for rec in self:
            rec.customer_debit = 0
            rec.vendor_debit = 0
            if rec.partner_id:
                move_ids = self.env['account.move'].search(
                    [('partner_id', '=', rec.partner_id.id),
                     ('type', '=', 'in_invoice'), ('state', '=', 'posted'),
                     ('invoice_payment_state', '!=', 'paid')],
                    order='invoice_date_due asc')
                move_out_ids = self.env['account.move'].search(
                    [('partner_id', '=', rec.partner_id.id),
                     ('type', '=', 'out_invoice'), ('state', '=', 'posted'),
                     ('invoice_payment_state', '!=', 'paid')],
                    order='invoice_date_due asc')
                # rec.customer_debit = -(
                #     rec.partner_id.credit) if rec.partner_id.credit else 0
                # rec.vendor_debit = -(
                #     self.partner_id.credit) if self.partner_id.credit else 0

                rec.customer_debit = str(format(round(sum(move_out_ids.mapped('amount_residual')), 2), '.2f'))
                rec.vendor_debit = str(format(round(sum(move_ids.mapped('amount_residual')), 2),'.2f'))

    def _compute_balance_advance(self):
        for rec in self:
            rec.balance_advance = 0
            if rec.move_name:
                move = self.env['account.move'].search([('name', 'ilike', rec.move_name)])
                move_lines = self.env['account.move.line'].search([('move_id', '=', move.id)])
                balance_advance = 0
                for move_line in move_lines:
                    lines = move_line._reconciled_lines()
                    applied_amount = 0
                    credit_amount = 0
                    for line in lines:
                        record = self.env['account.move.line'].search(
                            [('id', '=', line), (
                                'display_type', 'not in',
                                ('line_section', 'line_note'))])
                        applied_amount += record.debit
                        credit_amount += record.credit
                    balance_advance += credit_amount - applied_amount
                rec.balance_advance = balance_advance


class PartnerCheckInherit(models.Model):
    _inherit = 'res.partner.check'

    check_number = fields.Char('Check No', default="New")

    @api.model
    def create(self, vals):
        res = super(PartnerCheckInherit, self).create(vals)
        sequence = self.env.ref('averigo_accounting_updt.check_sequence')
        seq = sequence.with_context(
            force_company=res.company_id.id).next_by_code(
            "res.partner.check") or _('New')
        res.check_number = seq
        return res
