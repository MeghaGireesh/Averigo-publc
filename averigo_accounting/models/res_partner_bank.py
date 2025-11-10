from odoo import models, fields


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    is_vendor = fields.Boolean('Is Vendor')
    is_customer = fields.Boolean('Is Customer')
