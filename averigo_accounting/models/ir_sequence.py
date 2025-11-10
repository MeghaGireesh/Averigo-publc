from odoo import fields, models, api, _


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    inv_seq = fields.Boolean(default=False, help="This is used to give domain for invoice sequence")
    inv_refund_seq = fields.Boolean(default=False, help="This is used to give domain for invoice credit note sequence")
    bill_seq = fields.Boolean(default=False, help="This is used to give domain for bill sequence")
    bill_refund_seq = fields.Boolean(default=False, help="This is used to give domain for bill credit note sequence")
    adv_payment_customer_seq = fields.Boolean(default=False,
                                              help="This is used to give domain for customer advance payment sequence")
    adv_payment_vendor_seq = fields.Boolean(default=False,
                                            help="This is used to give domain for vendor advance payment sequence")
    payment_vendor_seq = fields.Boolean(default=False, help="This is used to give domain for vendor payment sequence")
    invoice_receipt_seq = fields.Boolean(default=False, help="This is used to give domain for invoice receipt")
