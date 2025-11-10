from odoo import fields, models


# from odoo.addons.stock.models.stock_warehouse import Orderpoint


class StockWarehouseMachine(models.Model):
    _inherit = "stock.warehouse"

    machine_ids = fields.One2many('account.asset', 'micro_market_id', string="Equipment")
    is_parts_warehouse = fields.Boolean('Is Parts Warehouse', help="This is used to separate parts warehouse")

    def name_get(self):
        """Micro-market name showing double issue fixe"""
        result = []
        for market in self:
            result.append((market.id, market.name))
        return result


class StockLocation(models.Model):
    _inherit = "stock.location"
    """This field is used to check or to create a relation b/w the area location and partner.The area location is 
    used in the Equipment management to transfer equipment."""
    area_partner_id = fields.Many2one('res.partner', string="Partner_id", help="The related partner id")
    area_or_pos = fields.Boolean("Area or Pos")

#     @api.model
#     def default_get(self, fields):
#         res = super(Orderpoint, self).default_get(fields)
#         warehouse = None
#         if 'warehouse_id' not in res and res.get('company_id'):
#             if self._context.get('machine_parts'):
#                 warehouse = self.env['stock.warehouse'].search(
#                     [('company_id', '=', res['company_id']), ('is_parts_warehouse', '=', True)], limit=1)
#             else:
#                 warehouse = self.env['stock.warehouse'].search([('company_id', '=', res['company_id'])], limit=1)
#         if warehouse:
#             res['warehouse_id'] = warehouse.id
#             res['location_id'] = warehouse.lot_stock_id.id
#         return res
#
#     Orderpoint.default_get = default_get
#
#     is_parts_reorder = fields.Boolean('Machine Parts Reorder')
#
#     @api.onchange('company_id')
#     def _onchange_company_id(self):
#         pass
