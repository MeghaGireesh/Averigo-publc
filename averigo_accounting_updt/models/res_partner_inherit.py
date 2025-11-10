from odoo import models, fields, api, _


class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    invoice_balance = fields.Float(compute='_compute_invoice_balance',
                                   string="Balance", default=0.0)

    bill_balance = fields.Float(compute='_compute_bill_balance',
                                string="Bill Balance", default=0.0)

    advance_balance = fields.Float(compute='_compute_advance_balance',
                                   string="Advance Balance", default=0.0)

    credit_balance = fields.Float(compute='_compute_bill_balance',
                                  string="Credit Balance", default=0.0)
    zip = fields.Char('Zip', size=5, required=True)
    street = fields.Char('Street', required=True)

    def _compute_invoice_balance(self):
        for rec in self:
            move_ids = self.env['account.move'].search(
                [('partner_id', '=', rec.id),
                 ('type', '=', 'out_invoice'), ('state', '=', 'posted'),
                 ('invoice_payment_state', '!=', 'paid')])
            if move_ids:
                rec.invoice_balance = sum(move_ids.mapped('amount_residual'))
            else:
                rec.invoice_balance = 0

    def _compute_advance_balance(self):
        for rec in self:
            domain = [('partner_id', '=', rec.id),
                      ('reconciled', '=', False),
                      ('credit', '>', 0), ('parent_state', '=', 'posted'),
                      ('account_internal_type', '=', 'receivable'),
                      ('company_id', '=', rec.operator_id.id)]
            advance_move_line = self.env['account.move.line'].sudo().search(
                domain)
            mult = -1 if sum(
                advance_move_line.mapped('amount_residual')) < 0 else 1
            rec.advance_balance = mult * sum(
                advance_move_line.mapped('amount_residual'))

    def _compute_bill_balance(self):
        for rec in self:
            move_ids = self.env['account.move'].search(
                [('partner_id', '=', rec.id),
                 ('type', '=', 'in_invoice'), ('state', '=', 'posted'),
                 ('invoice_payment_state', '!=', 'paid')])
            if move_ids:
                rec.bill_balance = sum(move_ids.mapped('amount_residual'))
            else:
                rec.bill_balance = 0
            domain = [('partner_id', '=', rec.id),
                      ('reconciled', '=', False),
                      ('debit', '>', 0), ('parent_state', '=', 'posted'),
                      ('account_internal_type', '=', 'payable'),
                      ('company_id', '=', rec.operator_id.id)]
            advance_move_line = self.env['account.move.line'].sudo().search(
                domain)
            mult = -1 if sum(
                advance_move_line.mapped('amount_residual')) < 0 else 1
            rec.credit_balance = mult * sum(
                advance_move_line.mapped('amount_residual'))
