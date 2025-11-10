from odoo import fields, models


class MachinePartsPurchase(models.Model):
    _inherit = "purchase.order"

    averigo_parts_purchase = fields.Boolean('Equipment Part', help="This is used to seperate Equipment part purchase")
