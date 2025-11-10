from odoo import fields, models, api, _
from odoo.exceptions import ValidationError,UserError


class MachineParts(models.Model):
    _inherit = "product.template"

    is_machine_part = fields.Boolean('Equipment Part', help="This is used to seperate Equipment part product")
    qty_available_parts = fields.Float('Quantity On Hand', compute='_compute_parts_quantities', compute_sudo=False,
                                       digits='Product Unit of Measure')
    averigo_reordering_rules = fields.Integer('Reordering Rules', compute='_compute_averigo_reordering_rules',
                                              compute_sudo=False)
    averigo_reordering_min_qty = fields.Float(compute='_compute_averigo_reordering_rules', compute_sudo=False)
    averigo_reordering_max_qty = fields.Float(compute='_compute_averigo_reordering_rules', compute_sudo=False)
    def unlink(self):
        """Searching the product is used for any Equipment as parts."""
        for rec in self:
            product_id = (
                self.env["product.product"]
                .sudo()
                .search([("product_tmpl_id", "=", rec.id)],limit=1)
            )
            parts_line_id = (
                self.env["parts.line"]
                .sudo()
                .search(
                    [
                        ("parts_id", "=", product_id.id),
                        ("company_id", "=", self.env.company.id),
                    ]
                )
            )
            if parts_line_id:
                raise UserError(
                    _("This product is associated with some equipments. You "
                      "cannot delete it.")
                ) 
        return super().unlink()

    def _compute_averigo_reordering_rules(self):
        res = {k: {'averigo_reordering_rules': 0, 'averigo_reordering_min_qty': 0, 'averigo_reordering_max_qty': 0} for
               k in self.ids}
        product_data = self.env['reordering.rule'].read_group(
            [('product_id.product_tmpl_id', 'in', self.ids)], ['product_id', 'product_min_qty', 'product_max_qty'],
            ['product_id'])
        for data in product_data:
            product = self.env['product.product'].browse([data['product_id'][0]])
            product_tmpl_id = product.product_tmpl_id.id
            res[product_tmpl_id]['averigo_reordering_rules'] += int(data['product_id_count'])
            res[product_tmpl_id]['averigo_reordering_min_qty'] = data['product_min_qty']
            res[product_tmpl_id]['averigo_reordering_max_qty'] = data['product_max_qty']
        for template in self:
            if not template.id:
                template.averigo_reordering_rules = 0
                template.averigo_reordering_min_qty = 0
                template.averigo_reordering_max_qty = 0
                continue
            template.averigo_reordering_rules = res[template.id]['averigo_reordering_rules']
            template.averigo_reordering_min_qty = res[template.id]['averigo_reordering_min_qty']
            template.averigo_reordering_max_qty = res[template.id]['averigo_reordering_max_qty']

    @api.depends('qty_available')
    def _compute_parts_quantities(self):
        print("_computee", self)
        for template in self:
            print("template", template)
            if template.is_machine_part:
                quantity_available = 0
                stock_quant = self.env['stock.quant'].search([('product_tmpl_id', '=', template.id)])
                print("stock qaunt", stock_quant)
                for stock in stock_quant:
                    print("stockk", stock.warehouse_id)
                    if stock.warehouse_id.is_parts_warehouse:
                        quantity_available += stock.quantity
                template.qty_available_parts = quantity_available
            else:
                template.qty_available_parts = 0

    def action_view_orderpoints_parts(self):
        products = self.mapped('product_variant_ids')
        action = self.env.ref('account_asset_management.product_open_reordering_rule_parts').read()[0]
        if products and len(products) == 1:
            action['context'] = {'default_product_id': products.ids[0], 'search_default_product_id': products.ids[0]}
            action['domain'] = [('product_id', '=', products.ids[0])]
        else:
            action['domain'] = [('product_id', 'in', products.ids)]
            action['context'] = {}
        return action

    @api.constrains('list_price')
    def _check_list_price(self):
        if self.list_price and self.list_price < 0:
            raise ValidationError(_("Sales price cannot be negative"))


class StockChangeStandardPrice(models.TransientModel):
    _inherit = "stock.change.standard.price"

    @api.constrains('new_price')
    def _check_new_price(self):
        if self.new_price and self.new_price < 0:
            raise ValidationError(_("Cost cannot be negative"))
