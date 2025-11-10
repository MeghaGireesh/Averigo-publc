from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class PaymentBillLine(models.Model):
    _name = 'payment.bill.line'

    payment_id = fields.Many2one('account.payment')
    invoice_id = fields.Many2one('account.move')
    company_id = fields.Many2one('res.company', related='invoice_id.company_id')
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id')
    name = fields.Char('Invoice #', related='invoice_id.name')
    partner_id = fields.Many2one('res.partner', related='invoice_id.partner_id')
    invoice_date_due = fields.Date(related='invoice_id.invoice_date_due')
    amount_total_view = fields.Float(related='invoice_id.amount_total_view')
    amount_adjusted = fields.Float(compute='compute_amount_values')
    amount_residual = fields.Float()
    invoice_amount_residual = fields.Monetary(related='invoice_id.amount_residual')
    amount_residual_changed = fields.Boolean(compute='compute_amount_residual_changed')
    advance_amount = fields.Float()
    amount_received = fields.Float()
    due_amount = fields.Float(store=True, compute='compute_amount_values')
    advance_move_line_id = fields.Many2one('account.move.line', string='Advance',
                                           copy=False)
    have_advance_value = fields.Boolean()
    filter_advance_move_line_ids = fields.Many2many('account.move.line',
                                                    compute='_compute_filter_advance_move_line_ids')
    unapplied_amount = fields.Float(compute='compute_amount_values')

    @api.depends('invoice_amount_residual', 'amount_residual')
    def compute_amount_residual_changed(self):
        for rec in self:
            if round(rec.amount_residual, rec.company_id.decimal_precision) \
                    != round(rec.invoice_amount_residual, rec.company_id.decimal_precision) \
                    and rec.payment_id.state == 'draft':
                rec.amount_residual_changed = True
            else:
                rec.amount_residual_changed = False

    @api.depends('amount_total_view', 'amount_residual', 'advance_amount', 'amount_received')
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
            advance_move_line = rec.payment_id.advance_move_line_ids
            rec.filter_advance_move_line_ids = advance_move_line.ids

    @api.onchange('amount_received')
    def onchange_amount_received(self):
        if self.amount_residual_changed:
            raise ValidationError(_("Amount Balance is changed in the invoice please update it here"))
        due_amount = self.amount_residual - self.advance_amount - self.amount_received
        if round(due_amount, 2) < 0:
            raise ValidationError(_("Amount received cannot be greater than due amount"))

    @api.onchange('advance_amount')
    def onchange_advance_amount(self):
        if self.amount_residual_changed:
            raise ValidationError(_("Amount Balance is changed in the invoice please update it here"))
        advance_amount = self.advance_move_line_id._origin.amount_residual
        mult = -1 if advance_amount < 0 else 1
        if self.advance_amount > mult * advance_amount or self.advance_amount > self.amount_residual:
            raise ValidationError(
                _("Advance amount cannot be greater than the selected advance amount or balance amount"))
        due_amount = self.amount_residual - self.advance_amount - self.amount_received
        if due_amount < 0:
            raise ValidationError(_("Advance Amount cannot be greater than due amount"))

    @api.onchange('advance_move_line_id')
    def _onchange_advance_move_line_ids(self):
        if self.amount_residual_changed:
            raise ValidationError(_("Amount Balance is changed in the invoice please update it here"))
        if self.advance_move_line_id:
            self.have_advance_value = True
            advance_amount = self.advance_move_line_id._origin.amount_residual
            mult = -1 if advance_amount < 0 else 1
        else:
            self.have_advance_value = False
            self.advance_amount = 0

    def update_amount_residual(self):
        self.amount_residual = self.invoice_amount_residual
