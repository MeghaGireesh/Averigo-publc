# -*- coding: utf-8 -*-
######################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>))
#
#    This program is under the terms of the Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the Software
#    or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#    IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#    DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
#    ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
########################################################################################

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AddProductWizard(models.TransientModel):
    _name = 'add.product.wizard'

    product_ids = fields.Many2many('product.product', string='Products')
    micro_market_ids = fields.Many2many('stock.warehouse', string='Locations')
    customer_ids = fields.Many2many('res.partner', string='Customers')
    market_filter_ids = fields.Many2many('stock.warehouse', 'location_id', store=True,
                                         compute='_compute_market_filter_ids')
    mm_dom_ids = fields.Many2many('stock.warehouse', 'market_ids', compute='_compute_market_filter_ids')
    location_line_ids = fields.One2many('add.product.wizard.line', 'product_wizard_id', string='Location Lines')
    customer_line_ids = fields.One2many('customer.product.wizard.line', 'customer_wizard_id', string='Location Lines')
    location_boolean = fields.Boolean(string='Add')
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company)
    update_type = fields.Selection([
        ('locations', 'Locations'),
        ('customers', 'Customers'),
    ], default='locations', string='Type')


    @api.onchange('update_type')
    def onchange_update_type(self):
        self.customer_line_ids.unlink()
        self.location_line_ids.unlink()
        self.micro_market_ids = None

    @api.onchange('customer_ids','update_type')
    def onchange_customer_ids(self):
        if self.update_type == 'customers':
            m = self.env['customer.product'].search([('product_id', 'in', self.product_ids.ids)])
            return {'domain': {'customer_ids': [('id', 'in', m.customer_product_id.ids)]}}


    @api.onchange('location_boolean')
    def onchange_location_boolean(self):
        """Add Button"""
        """Function to Add the Product and Locations to the lines"""
        if self.update_type == 'locations':
            items = []
            if self.micro_market_ids._origin:
                for product_id in self.product_ids._origin:
                    self.location_boolean = False
                    for micro_market_id in self.micro_market_ids._origin:

                        exist_product = self.env['product.micro.market'].search(
                            [('micro_market_id', '=', micro_market_id.id), ('product_id', '=', product_id.id)])
                        if not exist_product:
                            data = (0, 0, {
                                    'product_wizard_id': self.id,
                                    'product_id': product_id.id,
                                    'micro_market_id': micro_market_id.id,
                                    'price': product_id.list_price_1,
                                    'exist_boolean': False,
                                })
                            items.append(data)
                        if exist_product:
                            data = (0, 0, {
                                'product_wizard_id': self.id,
                                'product_id': product_id.id,
                                'micro_market_id': micro_market_id.id,
                                'price': exist_product.list_price,
                                'existing_price': exist_product.list_price,
                                'exist_boolean': True,
                            })
                            items.append(data)
            elif self.location_boolean:
                for product_id in self.product_ids._origin:
                    self.location_boolean = False
                    markets = self.location_line_ids.mapped('micro_market_id')
                    micro_markets = self.env['stock.warehouse'].search([('id', 'in', self.mm_dom_ids.ids), ('id', 'not in', markets.ids)])
                    for micro_market_id in micro_markets:
                        exist_product = self.env['product.micro.market'].search(
                            [('micro_market_id', '=', micro_market_id.id), ('product_id', '=', product_id.id)])
                        if not exist_product:
                            data = (0, 0, {
                                'product_wizard_id': self.id,
                                'product_id': product_id.id,
                                'micro_market_id': micro_market_id.id,
                                'price': product_id.list_price_1,
                                'exist_boolean': False,
                            })
                            items.append(data)
                        if exist_product:
                            data = (0, 0, {
                                'product_wizard_id': self.id,
                                'product_id': product_id.id,
                                'micro_market_id': micro_market_id.id,
                                'price': exist_product.list_price,
                                'existing_price': exist_product.list_price,
                                'exist_boolean': True,
                            })
                            items.append(data)
            self.location_line_ids = [(2, 0, 0)] + items
            self.micro_market_ids = None
        elif self.update_type == 'customers':
            if not self.customer_ids:
                raise ValidationError(("Select any customer"))
            items = []
            if self.customer_ids._origin:
                for product_id in self.product_ids._origin:
                    self.location_boolean = False
                    for customer_id in self.customer_ids._origin.filtered(lambda l: l.operator_id == self.env.company):
                        exist_products = self.env['customer.product'].search(
                            [('customer_product_id', '=', customer_id.id),
                             ('product_id', '=', product_id.id)])
                        # if customer_id.
                        if exist_products:
                            for exist_product in exist_products:
                                data = (0, 0, {
                                    'customer_wizard_id': self.id,
                                    'product_id': product_id.id,
                                    'customer_id': customer_id.id,
                                    'price': exist_product.list_price,
                                    'existing_price': exist_product.list_price,
                                    'exist_boolean': True,
                                    'uom_id': exist_product.uom_id.id,
                                })
                                items.append(data)
            self.customer_line_ids = [(5, 0, 0)] + items
            self.customer_ids = None

    def add_product(self):
        """Add products to the Micro Markets or Update the price of existing Products"""
        if self.update_type == 'locations':
            for line_id in self.location_line_ids:
                product = line_id.product_id
                exist_product = self.env['product.micro.market'].search([('micro_market_id', '=', line_id.micro_market_id.id),('product_id', '=', product.id)])
                if not exist_product:
                    store_orders = self.env['stock.picking'].search(
                        [('micro_market_id', '=', line_id.micro_market_id.id), ('store_order', '=', True),
                         ('state', '=', 'draft')])
                    vals = {
                        'product_id': product.id,
                        'name': product.name,
                        'product_code': product.default_code,
                        'image': product.image_128,
                        # 'catalog_id': product.catalog_id.id,
                        'tax_status': product.tax_status,
                        'categ_id': product.categ_id.id,
                        'list_price': line_id.price,
                        'catalog_price': product.list_price,
                        'uom_category': product.uom_id.category_id.id,
                        'uom_id': product.uom_id.id,
                        'upc_ids': product.upc_ids.ids,
                        'description': product.description_sale,
                        'container_deposit_tax': product.crv_tax.id,
                        'container_deposit_amount': product.crv_tax.amount,
                        'min_qty': product.reorder_point,
                        'max_qty': product.reorder_qty,
                        'micro_market_id': line_id.micro_market_id.id,
                    }
                    line_id.micro_market_id.market_product_ids.create(vals)
                    for store_order in store_orders:
                        store_order.extra_mm_products += product
                        store_order.dom_extra_mm_products += product
                if exist_product:
                    if exist_product.list_price != line_id.price:
                        """Add log in customer AV-3096"""
                        line_id.micro_market_id.message_post(
                            body=_(
                                f'''Product Price Updated: Product Master <br/>
                                Changed By:{self.env.user.name}<br/>
                                Product name: {line_id.product_id.name}<br/>
                                Old Selling Price: {exist_product.list_price}<br/>
                                Latest Selling Price: {line_id.price}'''
                            )
                        )
                    exist_product.list_price = line_id.price
        elif self.update_type == 'customers':
            for customer in self.customer_line_ids.filtered(lambda l: l.exist_boolean):
                customer_products = self.env['customer.product'].search(
                    [('customer_product_id', '=', customer.customer_id.id),
                     ('product_id', '=', customer.product_id.id), ('uom_id', '=', customer.uom_id.id)])
                for customer_product in customer_products:
                    if customer.price != customer_product.list_price:
                        """Add log in customer AV-3050"""
                        customer.customer_id.message_post(
                            body=_(
                                f'''Product Price Updated: Product Master <br/>
                                Changed By:{self.env.user.name}<br/>
                                Product name: {customer.product_id.name} ({customer.uom_id.name})<br/>
                                Old Selling Price: {customer_product.list_price}<br/>
                                Latest Selling Price: {customer.price}'''
                            )
                        )
                    customer_product.write({
                        'list_price': customer.price
                    })


    @api.depends('location_line_ids')
    def _compute_market_filter_ids(self):
        """Added to remove micro market already having the product"""
        for rec in self:
            rec.market_filter_ids = None
            warehouse = self.env['stock.warehouse'].search(
                [('location_type', '=', 'micro_market'),
                 ('company_id', '=', rec.company_id.id)])
            product_micro_market = self.env['product.micro.market'].search(
                [('product_id', 'in', self.product_ids._origin.ids),
                 ('is_discontinued', '=', False)]).mapped('micro_market_id')
            markets = self.location_line_ids.mapped('micro_market_id')
            rec.market_filter_ids = markets
            rec.mm_dom_ids = product_micro_market.ids


class AddProductWizardLine(models.TransientModel):
    _name = 'add.product.wizard.line'
    _order = 'product_id'

    product_wizard_id = fields.Many2one('add.product.wizard')
    product_id = fields.Many2one('product.product', string='Product')
    micro_market_id = fields.Many2one('stock.warehouse', string='Locations')
    price = fields.Float(string='New Price', default='0.00')
    existing_price = fields.Float(string='Existing Price', default='0.00')
    exist_boolean = fields.Boolean(string="Exist")



class CustomerWizardLine(models.TransientModel):
    _name = 'customer.product.wizard.line'
    _order = 'product_id'

    customer_wizard_id = fields.Many2one('add.product.wizard')
    product_id = fields.Many2one('product.product', string='Product')
    price = fields.Float(string='New Price', default='0.00')
    existing_price = fields.Float(string='Existing Price', default='0.00')
    exist_boolean = fields.Boolean(string="Exist")
    customer_id = fields.Many2one('res.partner', string='Customers',domain=[('is_customer', '=', True)])
    uom_id = fields.Many2one(
        'uom.uom', string='Product UOMs', domain=[('is_customer', '=', True)])









