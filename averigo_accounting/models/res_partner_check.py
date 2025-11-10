from odoo import api, fields, models, _


class PartnerCheck(models.Model):
    _name = 'res.partner.check'
    _rec_name = 'check_number'
    _description = 'Check Accounts'

    check_bank_id = fields.Many2one('res.bank', string='Check Bank')
    check_bank_account_id = fields.Many2one('res.partner.bank', string='Check Bank Account')
    check_number = fields.Char('Check No', required=True)
    check_date = fields.Date(required=True, default=fields.Date.context_today)
    check_amount = fields.Float('Check Amount', digits="Account")
    sequence = fields.Integer(default=10)
    # advance_id = fields.Many2one('account.payment', 'Advance Payment', ondelete='cascade', index=True, required=True)
    partner_id = fields.Many2one('res.partner', 'Check Holder', ondelete='cascade', index=True,
                                 domain=['|', ('is_company', '=', True), ('parent_id', '=', False)])
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, ondelete='cascade')
    is_vendor = fields.Boolean('Is Vendor')
    is_customer = fields.Boolean('Is Customer')
    is_advance = fields.Boolean('Is Advance Payment', help="This is an advance payment check")

    _sql_constraints = [
        ('unique_number', 'unique(check_number, company_id, check_bank_id)', 'Check Number must be unique'),
    ]

    # @api.model
    # def create(self, values):
    #     if 'advance_id' in values and values['advance_id']:
    #         advance_payment_id = self.env['account.payment'].browse(values['advance_id'])
    #         values['partner_id'] = advance_payment_id.partner_id.id
    #     res = super(PartnerCreditCard, self).create(values)
    #     res.advance_id.amount = res.advance_id.total_check_amount
    #     return res
