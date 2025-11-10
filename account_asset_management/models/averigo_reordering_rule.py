from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError


class ReorderingRule(models.Model):
    _name = "reordering.rule"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Reordering Rule"
    _check_company_auto = True

    @api.model
    def default_get(self, fields):
        res = super(ReorderingRule, self).default_get(fields)
        warehouse = None
        if 'warehouse_id' not in res and res.get('company_id'):
            if self._context.get('machine_parts'):
                warehouse = self.env['stock.warehouse'].search(
                    [('company_id', '=', res['company_id']), ('is_parts_warehouse', '=', True)], limit=1)
            else:
                warehouse = self.env['stock.warehouse'].search([('company_id', '=', res['company_id'])], limit=1)
        if warehouse:
            res['warehouse_id'] = warehouse.id
            res['location_id'] = warehouse.lot_stock_id.id
        return res

    name = fields.Char('Name', copy=False, required=True, readonly=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('reordering.rule'))
    active = fields.Boolean('Active', default=True,
                            help="If the active field is set to False, it will allow you to hide the orderpoint without removing it.")
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', check_company=True, ondelete="cascade",
                                   required=True)
    location_id = fields.Many2one('stock.location', 'Location', ondelete="cascade", required=True, check_company=True)
    product_id = fields.Many2one('product.product', 'Product', ondelete='cascade', required=True, check_company=True,
                                 domain="[('type', '=', 'product'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure', related='product_id.uom_id',
                                  readonly=True, required=True,
                                  default=lambda self: self._context.get('product_uom', False))
    product_uom_name = fields.Char(string='Product unit of measure label', related='product_uom.name', readonly=True)

    product_min_qty = fields.Float('Minimum Quantity', digits='Product Unit of Measure', required=True,
                                   help="When the virtual stock equals to or goes below the Min Quantity specified for this field, Odoo generates "
                                        "a procurement to bring the forecasted quantity to the Max Quantity.")
    product_max_qty = fields.Float('Maximum Quantity', digits='Product Unit of Measure', required=True,
                                   help="When the virtual stock goes below the Min Quantity, Odoo generates "
                                        "a procurement to bring the forecasted quantity to the Quantity specified as Max Quantity.")
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company)
    allowed_location_ids = fields.One2many(comodel_name='stock.location', compute='_compute_allowed_location_ids')
    is_parts_reorder = fields.Boolean('Equipment Parts Reorder')

    @api.constrains('product_min_qty', 'product_max_qty')
    def _check_min_max(self):
        for rule in self:
            if rule.product_max_qty < rule.product_min_qty:
                raise UserError(_('Maximum quantity cannot be less than minimum quantity'))

    @api.depends('warehouse_id')
    def _compute_allowed_location_ids(self):
        loc_domain = [('usage', '=', 'internal')]
        # We want to keep only the locations
        #  - strictly belonging to our warehouse
        #  - not belonging to any warehouses
        for orderpoint in self:
            other_warehouses = self.env['stock.warehouse'].search([('id', '=', orderpoint.warehouse_id.id)])
            for lot_stock_id in other_warehouses.mapped('lot_stock_id'):
                loc_domain = expression.AND(
                    [loc_domain, ['|', ('location_id', '=', lot_stock_id.id), ('id', '=', lot_stock_id.id)]])
                loc_domain = expression.AND([loc_domain, [('company_id', '=', orderpoint.company_id.id)]])
            orderpoint.allowed_location_ids = self.env['stock.location'].search(loc_domain)

    @api.constrains('product_id')
    def _check_product_uom(self):
        ''' Check if the UoM has the same category as the product standard UoM '''
        if any(orderpoint.product_id.uom_id.category_id != orderpoint.product_uom.category_id for orderpoint in self):
            raise ValidationError(_(
                'You have to select a product unit of measure that is in the same category than the default unit of measure of the product'))

    @api.onchange('warehouse_id')
    def onchange_warehouse_id(self):
        """ Finds location id for changed warehouse. """
        if self.warehouse_id:
            self.location_id = self.warehouse_id.lot_stock_id.id

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_id.id
            return {'domain': {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}}
        return {'domain': {'product_uom': []}}

    def write(self, vals):
        if 'company_id' in vals:
            for orderpoint in self:
                if orderpoint.company_id.id != vals['company_id']:
                    raise UserError(_(
                        "Changing the company of this record is forbidden at this point, you should rather archive it and create a new one."))
        return super(ReorderingRule, self).write(vals)

    def create_purchase_order(self, res_id, act_id):
        reordering_rule_id = self.browse(res_id)
        activity_id = self.env['mail.activity'].browse(act_id)
        partner_id = reordering_rule_id.product_id.res_partner
        if partner_id:
            warehouse_qty_available = reordering_rule_id.product_id.with_context(
                warehouse=reordering_rule_id.warehouse_id.id).qty_available
            order_qty = reordering_rule_id.product_max_qty - warehouse_qty_available
            existing_order = self.env['purchase.order'].search(
                [('partner_id', '=', partner_id.id), ('state', '=', 'draft'),
                 ('warehouse_id', '=', reordering_rule_id.warehouse_id.id), ('averigo_parts_purchase', '=', True)],
                limit=1)
            if existing_order:
                existing_order.write({
                    'origin': existing_order.origin if existing_order.origin else '' + ',' + reordering_rule_id.name,
                })
                lst = [(0, 0, {
                    'name': reordering_rule_id.product_id.name,
                    'product_id': reordering_rule_id.product_id.id,
                    'product_qty': order_qty,
                    'product_uom': reordering_rule_id.product_uom.id,
                    'price_unit': reordering_rule_id.product_id.list_price,
                    'date_planned': fields.Datetime.now(),
                })]
                existing_order.order_line = [(2, 0, 0)] + lst
                activity_id.sudo().unlink()
            else:
                purchase_order = self.env['purchase.order'].create({
                    'partner_id': partner_id.id,
                    'warehouse_id': reordering_rule_id.warehouse_id.id,
                    'date_order': fields.Datetime.now(),
                    'origin': reordering_rule_id.name,
                    'averigo_parts_purchase': True,
                    'vendor_street': reordering_rule_id.product_id.res_partner.street,
                    'vendor_street2': reordering_rule_id.product_id.res_partner.street2,
                    'vendor_city': reordering_rule_id.product_id.res_partner.city,
                    'vendor_state_id': reordering_rule_id.product_id.res_partner.state_id.id,
                    'vendor_zip': reordering_rule_id.product_id.res_partner.zip,
                    'vendor_county': reordering_rule_id.product_id.res_partner.county,
                    'order_line': [
                        (0, 0, {
                            'name': reordering_rule_id.product_id.name,
                            'product_id': reordering_rule_id.product_id.id,
                            'product_qty': order_qty,
                            'product_uom': reordering_rule_id.product_uom.id,
                            'price_unit': reordering_rule_id.product_id.list_price,
                            'date_planned': fields.Datetime.now(),
                        })]
                })
                if purchase_order:
                    activity_id.sudo().unlink()
        return reordering_rule_id
