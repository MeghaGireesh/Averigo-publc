import json
import logging
from _operator import itemgetter
from datetime import datetime, timedelta

import requests
from odoo.exceptions import UserError
from pytz import timezone
from datetime import timedelta

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class FeaturedProducts(models.Model):
    _name = 'featured.products'
    _rec_name = 'market_id'
    _description = 'Featured Products'

    image = fields.Binary(string='Image', required=True, copy=False)
    image_notification = fields.Image(string='Notification Image', copy=False)
    product_id = fields.Many2one('product.product', string="Product", copy=False)
    product_ids = fields.Many2many('product.product', string="Product", copy=False)
    active = fields.Boolean(string="Active", default=True)
    operator_id = fields.Many2one(
        'res.company', 'Operator', required=True, index=True,
        default=lambda self: self.env.company)
    location = fields.Many2many('res.partner', 'featured_products_res_partner_rel', 'product_id', 'partner_id',
                                domain="[('id', 'in', customer_ids)]")
    customer_ids = fields.Many2many('res.partner', compute='compute_partner_ids')
    micro_market_id = fields.Many2many('stock.warehouse', 'featured_product_stock_warehouse_rel', 'product_id',
                                       'warehouse_id',
                                       domain=[('location_type', '=', 'micro_market')])
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="Stop Date")
    start_time = fields.Float(string="Start Time")
    end_time = fields.Float(string="Stop Time")
    # discount = fields.Float(string="Discount %", copy=False)
    mm_ids = fields.Many2many('stock.warehouse', 'featured_products_stock_warehouse_rel2', 'product_id2',
                              'warehouse_id2', copy=False)
    banner_text = fields.Char("Banner Text")
    product_line = fields.One2many('product.discount', 'special_id')
    market_id = fields.Many2one('stock.warehouse', string='Micro Market')
    categ_id = fields.Many2one('product.category', string='Category')
    categ_ids = fields.Many2many('product.category', compute='_compute_categ_id')
    market_ids = fields.Many2many('stock.warehouse', compute='_compute_market_id')
    discount_percentage = fields.Float('Discount %')
    send_notification = fields.Boolean(default=False)
    notification = fields.Boolean('Notification', default=False)
    send_title = fields.Text(string="Notification Title")
    update_date = fields.Date(string="Update Date")
    category_ids = fields.Many2many('product.category', string="Category", copy=False)
    avail_all_products = fields.Boolean('Apply to All Products in the Market', default=False)
    dynamic_product_ids = fields.Many2many('product.product', compute='_compute_micro_market_product')
    select_product_ids = fields.Many2many('product.product', 'product_ids', string="Product", copy=False)
    add_button = fields.Boolean()
    is_category = fields.Boolean(default=False)

    # AV-2932 EE Discount issue -- Updates
    avail_new_catg_products = fields.Boolean(default=True)
    offer_mm_products_ids = fields.Many2many('product.micro.market','offer_mm_products_ids' ,help="Used to store the products, to use while avail_new_catg_products boolean is disabled.")

    @api.onchange('category_ids', 'avail_new_catg_products')
    def onchange_category_ids(self):
        # AV-2932 EE Discount issue -- Updates
        if self.category_ids._origin:
            self.is_category = True
            product_micro_markets = self.env['product.micro.market'].search(
                [('micro_market_id', '=', self._origin.micro_market_id.id), ('categ_id', 'in', self.category_ids._origin.ids),
                 ('product_id.product_tmpl_id.categ_id.enable_front_desk', '=', False), ('is_discontinued', '=', False)])
            self.offer_mm_products_ids = product_micro_markets
        else:
            self.is_category = False
            self.offer_mm_products_ids = None

    @api.onchange('category_ids', 'avail_all_products')
    def _onchange_clear_lines(self):
        self.product_line = [(5, 0, 0)]
        if self.avail_all_products:
            self.category_ids = [(5, 0, 0)]


    @api.onchange('add_button')
    def onchange_add_button(self):
        if self.select_product_ids:
            product_micro = self.env['stock.warehouse'].search(
                [('id', '=', self.market_id.id)])
            product_micro_markets = product_micro.market_product_ids.search([('micro_market_id', '=', self.market_id.id),
                                                                             ('product_id', 'in', self.select_product_ids.ids)])
            lst = []
            for product_micro_market in product_micro_markets:
                if not product_micro_market.product_id.product_tmpl_id.categ_id.enable_front_desk:
                    vals = (0, 0, {
                        'product_id': product_micro_market.product_id.id,
                        'price': product_micro_market.list_price,
                        'discount_percentage': self.discount_percentage,
                        'categ_id': product_micro_market.categ_id.id,
                        'sale_price': product_micro_market.list_price - (
                                (product_micro_market.list_price * self.discount_percentage) / 100),
                        'mm_ids': product_micro_market.id
                    })
                    lst.append(vals)
            self.product_line = [(2, 0, 0)] + lst
        self.select_product_ids = None

    @api.depends('market_id', 'product_line', 'avail_all_products', 'category_ids')
    def _compute_micro_market_product(self):
        for rec in self:
            rec.dynamic_product_ids = None
            if rec.market_id:
                if not rec.avail_all_products:
                    # Get products from the partner excluding those in order lines
                    products = rec.market_id.market_product_ids.mapped('product_id') - rec.product_line.mapped(
                        'product_id')
                    rec.dynamic_product_ids = products
            else:
                rec.dynamic_product_ids = None

    # @api.constrains('discount_percentage')
    # def _check_discount(self):
    #     if self.discount_percentage < 0 or self.discount_percentage > 99:
    #         raise UserError(_("Percentage should be between 0% to 100%!"))

    @api.onchange('discount_percentage')
    def onchange_discount_id(self):
        if 0 < self.discount_percentage < 100:
            if self.product_line:
                for rec in self.product_line:
                    if rec.price > 0:
                        rec.discount_percentage = self.discount_percentage
                        rec.sale_price = rec.price - ((rec.price * self.discount_percentage) / 100)
        # if self.discount_percentage == 0:
        else:
            if self.product_line:
                for rec in self.product_line:
                    rec.discount_percentage = 0
                    rec.sale_price = rec.price
        # if self.discount_percentage > 0:
        #     if self.product_line:
        #             for rec in self.product_line:
        #                 if rec.price > 0:
        #                     rec.discount_percentage = self.discount_percentage
        #                     rec.sale_price = rec.price - ((rec.price * self.discount_percentage) / 100)

    def cron_notification_send(self):
        """automatically send notification"""
        headers = {"Content-Type": "application/json",
                   "Authorization": "key=AAAAT_-fquI:APA91bHbukzD8FLbtpxf7nUCQF6-30j3G1GihojIVsTU48CsGM1W56WjR1V01gclNbdOq9Iux8AJYCLhZG8wSR9qgciNDonjHa4vx6nKSkZ1svPIK3EuSNxXvWm-R34ya6GvYogwA_Sb"}
        utc = timezone("UTC")
        now = utc.localize(datetime.utcnow())
        # day = now
        utc = timezone("US/Pacific")
        date_format = '%m-%d-%Y %H:%M:%S'
        date_format_1 = '%Y-%m-%d %H:%M:%S'
        date = datetime.now(tz=utc)
        date = date.astimezone(timezone('US/Pacific'))
        day = date.strftime(date_format_1)
        today = date.today()
        yesterday = today - timedelta(days=1)
        day_before = today - timedelta(days=2)
        los_angeles_tz = timezone('America/Los_Angeles')
        los_angeles_time = now.astimezone(los_angeles_tz)
        hour = los_angeles_time.strftime("%H")
        mint = los_angeles_time.strftime("%M")
        time_now = hour + '.' + mint

        """************************ Special **********************"""

        schedule = self.env['notification.setup'].sudo().search([('notification_type', '=', 'special')])
        if len(schedule) > 0:
            # z = self.env['featured.products'].sudo().search(
            #     ['|', ('update_date', '=', day), '|', ('update_date', '=', day_before), ('update_date', '=', yesterday),
            #      ('send_notification', '=', True)])
            res = max(self.env['notification.setup'].sudo().search([('notification_type', '=', 'special')], limit=1,
                                                                   order='create_date desc'))
            time = '{0:02.0f}:{1:02.0f}'.format(*divmod(res.notification_time * 60, 60))
            cur_time = float(time.split(":")[0] + '.' + time.split(":")[1])
            x = self.env['featured.products'].sudo().search(
                ['|', ('start_date', '=', day), '|', ('start_date', '=', day_before), ('start_date', '=', yesterday),
                 ('send_notification', '=', True), ('notification', '=', False)])
            if x:
                if float(time_now) - .04 <= cur_time <= float(time_now) + .04:
                    for market in x:
                        product_available = market.market_id.market_product_ids.product_id & market.product_line.product_id
                        if product_available:
                            last_purchases = self.env['res.app.users'].sudo().search(
                                [('last_visted', '=', market.market_id.id),
                                 ('devicetype', '=', 'Android')])
                            last_purchase_devices = last_purchases.mapped('devicetoken')
                            send_list = list(dict.fromkeys(last_purchase_devices))
                            device_tokens = list(filter(None, send_list))
                            all_token = []
                            front_desk = self.env['front.desk'].sudo().search(
                                [('micro_market_ids', 'in', market.market_id.id), ('state', '=', 'done')])
                            if front_desk:
                                front_desk_tokens = front_desk.mapped('user_ids').mapped('devicetoken')
                                device_tokens_front = list(filter(None, front_desk_tokens))
                                send_list = list(dict.fromkeys(device_tokens_front))
                                for item in device_tokens:
                                    if item not in send_list:
                                        all_token.append(item)
                            else:
                                all_token = device_tokens
                            url = 'https://fcm.googleapis.com/fcm/send'
                            image = "http://api.averigo.com/web/image_get?model=featured.products&id=%d&field=image_notification" % (
                                market.id)
                            # image = "http://admin.averigo.com/web/image_get?model=product.product&id=3017&field=image_1920"
                            beacon = market.market_id.beacon_major + "-" + market.market_id.beacon_minor
                            body = {
                                "data": {
                                    "ContentType": "Special",
                                    "Title": market.send_title,
                                    "Content": market.banner_text,
                                    "ImageUrl": image,
                                    "webURL": "",
                                    "MicromarketId": str(beacon),
                                    "LocationId": str(market.market_id.id),
                                    "ServiceName": market.market_id.company_id.name,
                                    "CategoryId": "SPECIAL",
                                    "UserType": "N",
                                    "UserId": ""
                                },
                                "priority": "high",
                                "registration_ids": all_token
                            }
                            # headers = {"Content-Type": "application/json",
                            #            "Authorization": "key=AAAAT_-fquI:APA91bHbukzD8FLbtpxf7nUCQF6-30j3G1GihojIVsTU48CsGM1W56WjR1V01gclNbdOq9Iux8AJYCLhZG8wSR9qgciNDonjHa4vx6nKSkZ1svPIK3EuSNxXvWm-R34ya6GvYogwA_Sb"}
                            requests.post(url, data=json.dumps(body), headers=headers)

                    for market in x:
                        product_available = market.market_id.market_product_ids.product_id & market.product_line.product_id
                        if product_available:
                            last_purchases = self.env['res.app.users'].sudo().search(
                                [('last_visted', '=', market.market_id.id), ('devicetype', '=', 'iOS')])
                            last_purchase_devices = last_purchases.mapped('devicetoken')
                            send_list = list(dict.fromkeys(last_purchase_devices))
                            device_tokens = list(filter(None, send_list))
                            all_token = []
                            front_desk = self.env['front.desk'].sudo().search(
                                [('micro_market_ids', 'in', market.market_id.id), ('state', '=', 'done')])
                            if front_desk:
                                front_desk_tokens = front_desk.mapped('user_ids').mapped('devicetoken')
                                device_tokens_front = list(filter(None, front_desk_tokens))
                                send_list = list(dict.fromkeys(device_tokens_front))
                                for item in device_tokens:
                                    if item not in send_list:
                                        all_token.append(item)
                            else:
                                all_token = device_tokens
                            market.notification = True
                            url = 'https://fcm.googleapis.com/fcm/send'
                            image = "http://api.averigo.com/web/image_get?model=featured.products&id=%d&field=image_notification" % (
                                market.id)
                            # image = "http://admin.averigo.com/web/image_get?model=product.product&id=3017&field=image_1920"
                            beacon = market.market_id.beacon_major + "-" + market.market_id.beacon_minor
                            body = {
                                "priority": "high",
                                "click_action": "GRABS",
                                "mutable_content": True,
                                "content_available": True,
                                "notification": {
                                    "title": "Special",
                                    "body": market.banner_text,
                                },
                                "data": {
                                    "title": market.send_title,
                                    "body": market.banner_text,
                                    "ContentType": "Special",
                                    "Title": market.send_title,
                                    "Content": market.banner_text,
                                    "ImageUrl": image,
                                    "webURL": "",
                                    "MicromarketId": str(beacon),
                                    "LocationId": str(market.market_id.id),
                                    "ServiceName": market.market_id.company_id.name,
                                    "CategoryId": "SPECIAL",
                                    "UserType": "N",
                                    "UserId": ""
                                },
                                "registration_ids": all_token
                            }
                            # headers = {"Content-Type": "application/json",
                            #            "Authorization": "key=AAAAW6s_bAM:APA91bFh7oqSbRjPkAFNL0WG1cQwtNZQNaIjlIX8EL5iym-KntomBoKSKu5yPc4HQYyOsbDyf6hv5gLXNlYZhyQBBm_KOmdfABZ_8XsI3JrcFvwHdFZFlXOrK4cEZA9_aW_xtvHITRPj"}
                            requests.post(url, data=json.dumps(body), headers=headers)

        """************************ Featured **********************"""

        schedule = self.env['notification.setup'].sudo().search([('notification_type', '=', 'featured')])
        if len(schedule) > 0:
            res = max(self.env['notification.setup'].sudo().search([('notification_type', '=', 'featured')], limit=1,
                                                                   order='create_date desc'))
            time = '{0:02.0f}:{1:02.0f}'.format(*divmod(res.notification_time * 60, 60))
            cur_time = float(time.split(":")[0] + '.' + time.split(":")[1])
            x = self.env['admin.featured.products'].sudo().search(
                ['|', ('start_date', '=', day), '|', ('start_date', '=', day_before), ('start_date', '=', yesterday),
                 ('send_notification', '=', True), ('notification', '=', False)])
            if x:
                if float(time_now) - .04 <= cur_time <= float(time_now) + .04:
                    for y in x:
                        for market in y.micro_market_id:
                            prod_available = market.market_product_ids.product_id & y.product_ids
                            if prod_available:
                                users = self.env['res.app.users'].sudo().search(
                                    [('last_visted', '=', [market.id]), ('devicetype', '=', 'Android')])
                                # users = self.env['res.app.users'].sudo().search(
                                #     [('devicetype', '=', 'Android')
                                #      ])
                                last_purchase_devices = users.mapped('devicetoken')
                                send_list = list(dict.fromkeys(last_purchase_devices))
                                device_tokens = list(filter(None, send_list))
                                front_desk = self.env['front.desk'].sudo().search(
                                    [('micro_market_ids', 'in', [market.id]), ('state', '=', 'done')])
                                all_token = []
                                if front_desk:
                                    front_desk_tokens = front_desk.mapped('user_ids').mapped('devicetoken')
                                    device_tokens_front = list(filter(None, front_desk_tokens))
                                    send_list = list(dict.fromkeys(device_tokens_front))
                                    for item in device_tokens:
                                        if item not in send_list:
                                            all_token.append(item)
                                else:
                                    all_token = device_tokens
                                url = 'https://fcm.googleapis.com/fcm/send'
                                # image = "http://admin.averigo.com/web/image_get?model=product.product&id=3017&field=image_1920"
                                image = "http://api.averigo.com/web/image_get?model=admin.featured.products&id=%d&field=image_notification" % (
                                    y.id)
                                beacon = market.beacon_major + "-" + market.beacon_minor
                                body = {
                                    "data": {
                                        "ContentType": "Featured",
                                        "Title": y.send_title,
                                        "Content": y.banner_text,
                                        "ImageUrl": image,
                                        "webURL": "",
                                        "MicromarketId": str(beacon),
                                        "LocationId": str(market.id),
                                        "ServiceName": market.company_id.name,
                                        "CategoryId": "FEATURE",
                                        "UserType": "N",
                                        "UserId": ""
                                    },
                                    "priority": "high",
                                    "registration_ids": all_token
                                }
                                # headers = {"Content-Type": "application/json",
                                #            "Authorization": "key=AAAAW6s_bAM:APA91bFh7oqSbRjPkAFNL0WG1cQwtNZQNaIjlIX8EL5iym-KntomBoKSKu5yPc4HQYyOsbDyf6hv5gLXNlYZhyQBBm_KOmdfABZ_8XsI3JrcFvwHdFZFlXOrK4cEZA9_aW_xtvHITRPj"}
                                resp = requests.post(url, data=json.dumps(body), headers=headers)
                                _logger.error(resp)

                    for y in x:
                        for market in y.micro_market_id:
                            prod_available = market.market_product_ids.product_id & y.product_ids
                            if prod_available:
                                y.notification = True
                                users = self.env['res.app.users'].sudo().search(
                                    [('last_visted', '=', [market.id]), ('devicetype', '=', 'iOS')])
                                last_purchase_devices = users.mapped('devicetoken')
                                send_list = list(dict.fromkeys(last_purchase_devices))
                                device_tokens = list(filter(None, send_list))
                                front_desk = self.env['front.desk'].sudo().search(
                                    [('micro_market_ids', 'in', [market.id]), ('state', '=', 'done')])
                                all_token = []
                                if front_desk:
                                    front_desk_tokens = front_desk.mapped('user_ids').mapped('devicetoken')
                                    device_tokens_front = list(filter(None, front_desk_tokens))
                                    send_list = list(dict.fromkeys(device_tokens_front))
                                    for item in device_tokens:
                                        if item not in send_list:
                                            all_token.append(item)
                                else:
                                    all_token = device_tokens
                                url = 'https://fcm.googleapis.com/fcm/send'
                                # image = "http://admin.averigo.com/web/image_get?model=product.product&id=3017&field=image_1920"
                                image = "http://api.averigo.com/web/image_get?model=admin.featured.products&id=%d&field=image_notification" % (
                                    y.id)
                                beacon = market.beacon_major + "-" + market.beacon_minor
                                body = {
                                    "priority": "high",
                                    "click_action": "GRABS",
                                    "mutable_content": True,
                                    "content_available": True,
                                    "notification": {
                                        "title": "Featured",
                                        "body": y.banner_text
                                    },
                                    "data": {
                                        "ContentType": "Featured",
                                        "Title": y.send_title,
                                        "Content": y.banner_text,
                                        "ImageUrl": image,
                                        "webURL": "",
                                        "MicromarketId": str(beacon),
                                        "LocationId": str(market.id),
                                        "ServiceName": market.company_id.name,
                                        "CategoryId": "FEATURE",
                                        "UserType": "N",
                                        "UserId": ""
                                    },
                                    "registration_ids": all_token
                                }

                                requests.post(url, data=json.dumps(body), headers=headers)

    @api.depends('location')
    def compute_partner_ids(self):
        warehouse = self.env['stock.warehouse'].search(
            [('location_type', '=', 'micro_market'), ('company_id', '=', self.env.user.company_id.id)]).mapped(
            'partner_id')
        self.customer_ids = warehouse.ids

    @api.onchange('market_id')
    def market_id_changed(self):
        self.micro_market_id = self.market_id

    @api.depends('market_id')
    def _compute_categ_id(self):
        for rec in self:
            if rec.location:
                categ_id = self.env['product.category'].search(
                    [('id', 'in', rec.market_ids.market_product_ids.categ_id.ids),
                     ('operator_id', '=', self.env.user.company_id.id)])
                rec.categ_ids = categ_id
            else:
                categ_id = self.env['product.category'].search([('operator_id', '=', self.env.user.company_id.id)])
                rec.categ_ids = categ_id

    @api.depends('location')
    def _compute_market_id(self):
        for rec in self:
            if rec.location:
                market_id = self.env['stock.warehouse'].search(
                    [('location_type', '=', 'micro_market'), ('partner_id', 'in', rec.location.ids),
                     ('company_id', '=', self.env.user.company_id.id)])
                rec.market_ids = market_id
            else:
                market_id = self.env['stock.warehouse'].search(
                    [('location_type', '=', 'micro_market'), ('company_id', '=', self.env.user.company_id.id)])
                rec.market_ids = market_id

    def add_discount_line(self):
        micro_market_line = self.market_id.mapped('market_product_ids')
        # if self.categ_id:
        #     product_micro_markets = self.env['product.micro.market'].search(
        #         [('micro_market_id', '=', self.micro_market_id.id), ('categ_id', '=', self.categ_id.id)])
        if self.category_ids:
            product_micro_markets = self.env['product.micro.market'].search(
                [('micro_market_id', '=', self.micro_market_id.id), ('categ_id', 'in', self.category_ids.ids)])
            lst = []
            for product_micro_market in product_micro_markets:
                if not product_micro_market.product_id.product_tmpl_id.categ_id.enable_front_desk:
                    vals = (0, 0, {
                        'product_id': product_micro_market.product_id.id,
                        'price': product_micro_market.list_price,
                        'discount_percentage': self.discount_percentage,
                        'categ_id': product_micro_market.categ_id.id,
                        'sale_price': product_micro_market.list_price - (
                                (product_micro_market.list_price * self.discount_percentage) / 100),
                        'mm_ids': product_micro_market.id
                    })
                    lst.append(vals)
            self.product_line = [(5, 0, 0)] + lst
        else:
            product_micro = self.env['stock.warehouse'].search(
                [('id', '=', self.market_id.id)])
            product_micro_markets = product_micro.market_product_ids
            lst = []
            for product_micro_market in product_micro_markets:
                if not product_micro_market.product_id.product_tmpl_id.categ_id.enable_front_desk:
                    vals = (0, 0, {
                        'product_id': product_micro_market.product_id.id,
                        'price': product_micro_market.list_price,
                        'discount_percentage': self.discount_percentage,
                        'categ_id': product_micro_market.categ_id.id,
                        'sale_price': product_micro_market.list_price - (
                                (product_micro_market.list_price * self.discount_percentage) / 100),
                        'mm_ids': product_micro_market.id
                    })
                    lst.append(vals)
            self.product_line = [(5, 0, 0)] + lst

    def get_featured_product(self, args):
        try:
            time = args['time'].split(' ')[1]
            date = args['time'].split(' ')[0]
            hours = float(time.split(':')[0])
            minutes = float(time.split(':')[1]) / 60 * 100
            timed_images = self.env['featured.products'].search(
                [('start_time', '<=', hours + (minutes / 100)), ('end_time', '>=', hours + (minutes / 100))])
            dated_images = self.env['featured.products'].search(
                [('start_date', '<=', date), ('end_date', '>=', date)])
            ids = self.env['featured.products'].search([('start_time', '=', 0), ('end_time', '=', 0)]).ids
            ids += self.env['featured.products'].search(
                [('start_date', '=', False),
                 ('end_date', '=', False)]).ids
            feat = []
            if dated_images.ids and timed_images.ids:
                ids += list(set(timed_images.ids) & set(dated_images.ids))
                # elif timed_images.ids:
                #     ids += timed_images.ids
                # elif dated_images.ids:
                #     ids += dated_images.ids
                micro_market = args['micro_market']
                record_id = self.env['featured.products'].search(
                    [('micro_market_id', 'in', [micro_market]), ('id', 'in', ids)])
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                ids = list(set(ids) & set(record_id.ids))
                featured_products = []
                mm_product = self.env['stock.warehouse'].browse(micro_market).market_product_ids
                market = self.env['stock.warehouse'].search([('id', '=', micro_market)])
                tax_name = self.env['additional.tax'].sudo().search(
                    [('operator_id', '=', market.company_id.id)],
                    limit=1) if market.addl_tax else False
                ids = self.env['featured.products'].browse(ids)
                admin_featured = self.env['admin.featured.products'].sudo().get_admin_featured_product({
                    'time': args['time'],
                    'micro_market': micro_market,
                })
                admin_res = list(map(itemgetter('ITEM_NO'), admin_featured))
                for id_ in ids:
                    if id_.avail_all_products:
                        for product_ids in id_.market_id.market_product_ids:
                            if market.handled_externally and product_ids.tax_status == 'yes':
                                sale_tax = str(product_ids.vms_sales_tax)
                            elif product_ids.tax_status == 'yes':
                                sale_tax = str(market.sales_tax)
                            else:
                                sale_tax = "0.00"
                            if product_ids and product_ids.list_price != 0 and not product_ids.is_discontinued:
                                if id_.discount_percentage:
                                    sale_price = product_ids.list_price - ((product_ids.list_price * id_.discount_percentage) / 100)
                                elif id_.discount_amount > 0:
                                    sale_price = product_ids.list_price - id_.discount_amount
                                else:
                                    sale_price = product_ids.list_price
                                data = {
                                    "CATEGORY_ID": str(product_ids.categ_id.id),
                                    "ITEM_DESC_LONG": product_ids.name or "",
                                    "ORIGINAL_PRICE": str(format(round(product_ids.list_price, 2), '.2f')),
                                    "ITEM_IMAGE_URL": '%s/web/image_get?model=product.micro.market&id=%d&field=image' % (
                                        base_url, product_ids.id),
                                    "ITEM_NO": product_ids.product_code or '',
                                    "CRVTAX": str(
                                        product_ids.container_deposit_tax.amount) if product_ids.container_deposit_tax else '0.00',
                                    "SALESTAX": sale_tax,
                                    "DISCOUNT_PRICE": format(round(sale_price, 2), '.2f') or format(
                                        round(product_ids.price, 2), '.2f'),
                                    "TAXABLE": 'Y' if product_ids.tax_status == 'yes' else 'N',
                                    "ITEM_DESC": product_ids.name or "",
                                    "STOCK": "Y",
                                    "IsFeatured": "N",
                                    "IsSpecial": "Y",
                                    "BAR_CODE": str(product_ids.upc_ids.mapped('upc_code_id'))[1:-1].replace(" ",
                                                                                                                    '').replace(
                                        "'", ''),
                                    "ITEM_IMAGE": '%s/web/image_get?model=product.product&id=%d&field=image_1920' % (
                                        base_url, product_ids.product_id.id),
                                    "DISCOUNT_APPLICABLE": "Y" if sale_price > 0.0 and sale_price != product_ids.list_price else "N",
                                    "CRV_ENABLE": "Y" if product_ids.is_container_tax else "N",
                                    "ITEM_PRICE": format(round(sale_price, 2), '.2f') or format(
                                        round(product_ids.price, 2), '.2f'),
                                    "ID": str(id_.id),
                                    "PRODUCT_INFO": product_ids.info or "",
                                    "OUTSIDE_MARKET_CATEGORY": "Y" if product_ids.categ_id.available_outside else "N",
                                    "ADDL_TAX1_NAME": tax_name.additional_tax_label_1 if tax_name and product_ids.tax_rate_percentage_1 > 0 and market.show_tax_rate_1 and product_ids.enable_tax_rate_1 == 'yes' else "",
                                    "ADDL_TAX1_VALUE": str(
                                        product_ids.tax_rate_percentage_1) if tax_name and product_ids.tax_rate_percentage_1 > 0 and market.show_tax_rate_1 and product_ids.enable_tax_rate_1 == 'yes' else "",
                                    "ADDL_TAX2_NAME": tax_name.additional_tax_label_2 if tax_name and product_ids.tax_rate_percentage_2 > 0 and market.show_tax_rate_2 and product_ids.enable_tax_rate_2 == 'yes' else "",
                                    "ADDL_TAX2_VALUE": str(
                                        product_ids.tax_rate_percentage_2) if tax_name and product_ids.tax_rate_percentage_2 > 0 and market.show_tax_rate_2 and product_ids.enable_tax_rate_2 == 'yes' else "",
                                    "ADDL_TAX3_NAME": tax_name.additional_tax_label_3 if tax_name and product_ids.tax_rate_percentage_3 > 0 and market.show_tax_rate_3 and product_ids.enable_tax_rate_3 == 'yes' else "",
                                    "ADDL_TAX3_VALUE": str(
                                        product_ids.tax_rate_percentage_3) if tax_name and product_ids.tax_rate_percentage_3 > 0 and market.show_tax_rate_3 and product_ids.enable_tax_rate_3 == 'yes' else "",

                                }
                                if admin_res:
                                    res = list(map(itemgetter('ITEM_NO'), feat)) + admin_res
                                    if data['ITEM_NO'] not in res:
                                        feat = [i for i in feat if not (i['ITEM_NO'] == data['ITEM_NO'])]
                                        feat.append(data)
                                else:
                                    feat.append(data)
                    else:
                        # AV-2932 EE Discount issue -- Updates

                        if id_.category_ids and id_.avail_new_catg_products:
                            pro_ids = id_.market_id.market_product_ids.search([('categ_id', 'in', id_.category_ids.ids),
                                                                               ('micro_market_id', '=', id_.market_id.id),
                                                                               ('product_id', 'not in', id_.product_line.mapped('product_id').ids)])
                            for pro_id in pro_ids:
                                if market.handled_externally and pro_id.tax_status == 'yes':
                                    sale_tax = str(pro_id.vms_sales_tax)
                                elif pro_id.tax_status == 'yes':
                                    sale_tax = str(market.sales_tax)
                                else:
                                    sale_tax = "0.00"
                                if pro_id and pro_id.list_price != 0 and not pro_id.is_discontinued:
                                    if id_.discount_percentage:
                                        sale_price = pro_id.list_price - (
                                                    (pro_id.list_price * id_.discount_percentage) / 100)
                                    elif id_.discount_amount > 0:
                                        sale_price = pro_id.list_price - id_.discount_amount
                                    else:
                                        sale_price = pro_id.list_price
                                    data = {
                                        "CATEGORY_ID": str(pro_id.categ_id.id),
                                        "ITEM_DESC_LONG": pro_id.name or "",
                                        "ORIGINAL_PRICE": str(format(round(pro_id.list_price, 2), '.2f')),
                                        "ITEM_IMAGE_URL": '%s/web/image_get?model=product.micro.market&id=%d&field=image' % (
                                            base_url, pro_id.id),
                                        "ITEM_NO": pro_id.product_code or '',
                                        "CRVTAX": str(
                                            pro_id.container_deposit_tax.amount) if pro_id.container_deposit_tax else '0.00',
                                        "SALESTAX": sale_tax,
                                        "DISCOUNT_PRICE": format(round(sale_price, 2), '.2f') or format(
                                            round(pro_id.price, 2), '.2f'),
                                        "TAXABLE": 'Y' if pro_id.tax_status == 'yes' else 'N',
                                        "ITEM_DESC": pro_id.name or "",
                                        "STOCK": "Y",
                                        "IsFeatured": "N",
                                        "IsSpecial": "Y",
                                        "BAR_CODE": str(pro_id.upc_ids.mapped('upc_code_id'))[1:-1].replace(" ",
                                                                                                                 '').replace(
                                            "'", ''),
                                        "ITEM_IMAGE": '%s/web/image_get?model=product.product&id=%d&field=image_1920' % (
                                            base_url, pro_id.product_id.id),
                                        "DISCOUNT_APPLICABLE": "Y" if sale_price > 0.0 and sale_price != pro_id.list_price else "N",
                                        "CRV_ENABLE": "Y" if pro_id.is_container_tax else "N",
                                        "ITEM_PRICE": format(round(sale_price, 2), '.2f') or format(
                                            round(pro_id.price, 2), '.2f'),
                                        "ID": str(id_.id),
                                        "PRODUCT_INFO": pro_id.info or "",
                                        "OUTSIDE_MARKET_CATEGORY": "Y" if pro_id.categ_id.available_outside else "N",
                                        "ADDL_TAX1_NAME": tax_name.additional_tax_label_1 if tax_name and pro_id.tax_rate_percentage_1 > 0 and market.show_tax_rate_1 and pro_id.enable_tax_rate_1 == 'yes' else "",
                                        "ADDL_TAX1_VALUE": str(
                                            pro_id.tax_rate_percentage_1) if tax_name and pro_id.tax_rate_percentage_1 > 0 and market.show_tax_rate_1 and pro_id.enable_tax_rate_1 == 'yes' else "",
                                        "ADDL_TAX2_NAME": tax_name.additional_tax_label_2 if tax_name and pro_id.tax_rate_percentage_2 > 0 and market.show_tax_rate_2 and pro_id.enable_tax_rate_2 == 'yes' else "",
                                        "ADDL_TAX2_VALUE": str(
                                            pro_id.tax_rate_percentage_2) if tax_name and pro_id.tax_rate_percentage_2 > 0 and market.show_tax_rate_2 and pro_id.enable_tax_rate_2 == 'yes' else "",
                                        "ADDL_TAX3_NAME": tax_name.additional_tax_label_3 if tax_name and pro_id.tax_rate_percentage_3 > 0 and market.show_tax_rate_3 and pro_id.enable_tax_rate_3 == 'yes' else "",
                                        "ADDL_TAX3_VALUE": str(
                                            pro_id.tax_rate_percentage_3) if tax_name and pro_id.tax_rate_percentage_3 > 0 and market.show_tax_rate_3 and pro_id.enable_tax_rate_3 == 'yes' else "",

                                    }
                                    if admin_res:
                                        res = list(map(itemgetter('ITEM_NO'), feat)) + admin_res
                                        if data['ITEM_NO'] not in res:
                                            feat = [i for i in feat if not (i['ITEM_NO'] == data['ITEM_NO'])]
                                            feat.append(data)
                                    else:
                                        feat.append(data)
                        elif id_.category_ids and not id_.avail_new_catg_products:
                            for pro_id in id_.offer_mm_products_ids:
                                if market.handled_externally and pro_id.tax_status == 'yes':
                                    sale_tax = str(pro_id.vms_sales_tax)
                                elif pro_id.tax_status == 'yes':
                                    sale_tax = str(market.sales_tax)
                                else:
                                    sale_tax = "0.00"
                                if pro_id and pro_id.list_price != 0 and not pro_id.is_discontinued:
                                    if id_.discount_percentage:
                                        sale_price = pro_id.list_price - (
                                                    (pro_id.list_price * id_.discount_percentage) / 100)
                                    elif id_.discount_amount > 0:
                                        sale_price = pro_id.list_price - id_.discount_amount
                                    else:
                                        sale_price = pro_id.list_price
                                    data = {
                                        "CATEGORY_ID": str(pro_id.categ_id.id),
                                        "ITEM_DESC_LONG": pro_id.name or "",
                                        "ORIGINAL_PRICE": str(format(round(pro_id.list_price, 2), '.2f')),
                                        "ITEM_IMAGE_URL": '%s/web/image_get?model=product.micro.market&id=%d&field=image' % (
                                            base_url, pro_id.id),
                                        "ITEM_NO": pro_id.product_code or '',
                                        "CRVTAX": str(
                                            pro_id.container_deposit_tax.amount) if pro_id.container_deposit_tax else '0.00',
                                        "SALESTAX": sale_tax,
                                        "DISCOUNT_PRICE": format(round(sale_price, 2), '.2f') or format(
                                            round(pro_id.price, 2), '.2f'),
                                        "TAXABLE": 'Y' if pro_id.tax_status == 'yes' else 'N',
                                        "ITEM_DESC": pro_id.name or "",
                                        "STOCK": "Y",
                                        "IsFeatured": "N",
                                        "IsSpecial": "Y",
                                        "BAR_CODE": str(pro_id.upc_ids.mapped('upc_code_id'))[1:-1].replace(" ",
                                                                                                                 '').replace(
                                            "'", ''),
                                        "ITEM_IMAGE": '%s/web/image_get?model=product.product&id=%d&field=image_1920' % (
                                            base_url, pro_id.product_id.id),
                                        "DISCOUNT_APPLICABLE": "Y" if sale_price > 0.0 and sale_price != pro_id.list_price else "N",
                                        "CRV_ENABLE": "Y" if pro_id.is_container_tax else "N",
                                        "ITEM_PRICE": format(round(sale_price, 2), '.2f') or format(
                                            round(pro_id.price, 2), '.2f'),
                                        "ID": str(id_.id),
                                        "PRODUCT_INFO": pro_id.info or "",
                                        "OUTSIDE_MARKET_CATEGORY": "Y" if pro_id.categ_id.available_outside else "N",
                                        "ADDL_TAX1_NAME": tax_name.additional_tax_label_1 if tax_name and pro_id.tax_rate_percentage_1 > 0 and market.show_tax_rate_1 and pro_id.enable_tax_rate_1 == 'yes' else "",
                                        "ADDL_TAX1_VALUE": str(
                                            pro_id.tax_rate_percentage_1) if tax_name and pro_id.tax_rate_percentage_1 > 0 and market.show_tax_rate_1 and pro_id.enable_tax_rate_1 == 'yes' else "",
                                        "ADDL_TAX2_NAME": tax_name.additional_tax_label_2 if tax_name and pro_id.tax_rate_percentage_2 > 0 and market.show_tax_rate_2 and pro_id.enable_tax_rate_2 == 'yes' else "",
                                        "ADDL_TAX2_VALUE": str(
                                            pro_id.tax_rate_percentage_2) if tax_name and pro_id.tax_rate_percentage_2 > 0 and market.show_tax_rate_2 and pro_id.enable_tax_rate_2 == 'yes' else "",
                                        "ADDL_TAX3_NAME": tax_name.additional_tax_label_3 if tax_name and pro_id.tax_rate_percentage_3 > 0 and market.show_tax_rate_3 and pro_id.enable_tax_rate_3 == 'yes' else "",
                                        "ADDL_TAX3_VALUE": str(
                                            pro_id.tax_rate_percentage_3) if tax_name and pro_id.tax_rate_percentage_3 > 0 and market.show_tax_rate_3 and pro_id.enable_tax_rate_3 == 'yes' else "",

                                    }
                                    if admin_res:
                                        res = list(map(itemgetter('ITEM_NO'), feat)) + admin_res
                                        if data['ITEM_NO'] not in res:
                                            feat = [i for i in feat if not (i['ITEM_NO'] == data['ITEM_NO'])]
                                            feat.append(data)
                                    else:
                                        feat.append(data)
                        for product_ids in id_.product_line:
                            # product_lines = self.env['product.micro.market'].search(
                            #     [('product_id', '=', product_ids.product_id.id),
                            #      ('micro_market_id', '=', id_.market_id.id)], limit=1)

                            # Updated the function for Vendsys sales tax

                            if market.handled_externally and product_ids.mm_ids.tax_status == 'yes':
                                sale_tax = str(product_ids.mm_ids.vms_sales_tax)
                            elif product_ids.mm_ids.tax_status == 'yes':
                                sale_tax = str(market.sales_tax)
                            else:
                                sale_tax = "0.00"
                            product_micro_markets = product_ids.mm_ids
                            if not product_ids.mm_ids:
                                product_micro_markets = self.env['product.micro.market'].search(
                                    [('micro_market_id', '=', id_.micro_market_id.id),
                                     ('product_id', '=', product_ids.product_id.id)], limit=1)
                                if not product_micro_markets:
                                    _logger.info(f"Product {product_ids.product_id.name} not fount in the market {id_.micro_market_id.name}.###########################")
                            if product_micro_markets and product_ids.mm_ids.list_price != 0 and not product_ids.mm_ids.is_discontinued:
                                data = {
                                    "CATEGORY_ID": str(product_ids.mm_ids.categ_id.id),
                                    "ITEM_DESC_LONG": product_ids.mm_ids.name or "",
                                    "ORIGINAL_PRICE": str(format(round(product_ids.mm_ids.list_price, 2), '.2f')),
                                    "ITEM_IMAGE_URL": '%s/web/image_get?model=product.micro.market&id=%d&field=image' % (
                                        base_url, product_ids.mm_ids.id),
                                    "ITEM_NO": product_ids.mm_ids.product_code or '',
                                    "CRVTAX": str(
                                        product_ids.mm_ids.container_deposit_tax.amount) if product_ids.mm_ids.container_deposit_tax else '0.00',
                                    "SALESTAX": sale_tax,
                                    "DISCOUNT_PRICE": format(round(product_ids.sale_price, 2), '.2f') or format(
                                        round(product_ids.price, 2), '.2f'),
                                    "TAXABLE": 'Y' if product_ids.mm_ids.tax_status == 'yes' else 'N',
                                    "ITEM_DESC": product_ids.mm_ids.name or "",
                                    "STOCK": "Y",
                                    "IsFeatured": "N",
                                    "IsSpecial": "Y",
                                    "BAR_CODE": str(product_ids.mm_ids.upc_ids.mapped('upc_code_id'))[1:-1].replace(" ",
                                                                                                                    '').replace(
                                        "'", ''),
                                    "ITEM_IMAGE": '%s/web/image_get?model=product.product&id=%d&field=image_1920' % (
                                        base_url, product_ids.product_id.id),
                                    "DISCOUNT_APPLICABLE": "Y" if product_ids.sale_price > 0.0 and product_ids.sale_price != product_ids.mm_ids.list_price else "N",
                                    "CRV_ENABLE": "Y" if product_ids.mm_ids.is_container_tax else "N",
                                    "ITEM_PRICE": format(round(product_ids.sale_price, 2), '.2f') or format(
                                        round(product_ids.price, 2), '.2f'),
                                    "ID": str(id_.id),
                                    "PRODUCT_INFO": product_ids.mm_ids.info or "",
                                    "OUTSIDE_MARKET_CATEGORY": "Y" if product_ids.mm_ids.categ_id.available_outside else "N",
                                    "ADDL_TAX1_NAME": tax_name.additional_tax_label_1 if tax_name and product_ids.mm_ids.tax_rate_percentage_1 > 0 and market.show_tax_rate_1 and product_ids.mm_ids.enable_tax_rate_1 == 'yes' else "",
                                    "ADDL_TAX1_VALUE": str(
                                        product_ids.mm_ids.tax_rate_percentage_1) if tax_name and product_ids.mm_ids.tax_rate_percentage_1 > 0 and market.show_tax_rate_1 and product_ids.mm_ids.enable_tax_rate_1 == 'yes' else "",
                                    "ADDL_TAX2_NAME": tax_name.additional_tax_label_2 if tax_name and product_ids.mm_ids.tax_rate_percentage_2 > 0 and market.show_tax_rate_2 and product_ids.mm_ids.enable_tax_rate_2 == 'yes' else "",
                                    "ADDL_TAX2_VALUE": str(
                                        product_ids.mm_ids.tax_rate_percentage_2) if tax_name and product_ids.mm_ids.tax_rate_percentage_2 > 0 and market.show_tax_rate_2 and product_ids.mm_ids.enable_tax_rate_2 == 'yes' else "",
                                    "ADDL_TAX3_NAME": tax_name.additional_tax_label_3 if tax_name and product_ids.mm_ids.tax_rate_percentage_3 > 0 and market.show_tax_rate_3 and product_ids.mm_ids.enable_tax_rate_3 == 'yes' else "",
                                    "ADDL_TAX3_VALUE": str(
                                        product_ids.mm_ids.tax_rate_percentage_3) if tax_name and product_ids.mm_ids.tax_rate_percentage_3 > 0 and market.show_tax_rate_3 and product_ids.mm_ids.enable_tax_rate_3 == 'yes' else "",

                                }
                                if admin_res:
                                    res = list(map(itemgetter('ITEM_NO'), feat)) + admin_res
                                    if data['ITEM_NO'] not in res:
                                        feat = [i for i in feat if not (i['ITEM_NO'] == data['ITEM_NO'])]
                                        feat.append(data)
                                else:
                                    feat.append(data)
            return (feat)
        except Exception as e:
            _logger.error(str(e))
            return []

    @api.model
    def create(self, vals_list):
        if 'end_date' in vals_list and 'start_date' in vals_list \
                and vals_list['end_date'] < vals_list['start_date']:
            raise UserError(_("Inconsistent start and end dates! \n"
                              "Stop date should be above the start date. "
                              "Please check the date fields and try again."))
        if 'start_time' in vals_list and 'end_time' in vals_list \
                and vals_list['end_time'] < vals_list['start_time']:
            raise UserError(_("Inconsistent start and end time! \n"
                              "Stop time should be above the start time. "
                              "Please check the time fields and try again."))
        if vals_list['start_time'] < 0 or vals_list['end_time'] < 0 or vals_list['start_time'] > 24.0 or vals_list[
            'end_time'] > 24.0:
            raise UserError(_("Inconsistent start and end time! \n"
                              "Time should be 0 to 24.0! "
                              "Please check the time fields and try again."))
        if vals_list['start_time'] == vals_list['end_time']:
            raise UserError(_("Start and End Time Can not be the same."))
        if 'micro_market_id' in vals_list:
            vals_list['mm_ids'] = vals_list['micro_market_id']
        elif 'location' in vals_list:
            location = vals_list['location'][0][2]
            location = self.env['stock.warehouse'].search([('partner_id', 'in', location)]).ids
            vals_list['mm_ids'] = [[6, False, location]]
        else:
            operator_id = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)]).ids
            vals_list['mm_ids'] = [[6, False, operator_id]]
        # vals_list['operator_id'] = self.env.user.company_id.id
        res = super(FeaturedProducts, self).create(vals_list)
        return res

    @api.constrains('end_date', 'start_date', 'market_id')
    def _check_dates(self):
        promo_exist = self.env['featured.products'].search(
            [('start_date', '<=', self.start_date), ('end_date', '>=', self.end_date),
             ('market_id', '=', self.market_id.id)])
        spl_mrk_exist = self.env['featured.products'].search([
             ('market_id', '=', self.market_id.id)])
        if len(spl_mrk_exist) > 1:
            raise UserError(_("A Special has already been set up for this market. Please archive or delete it before setting up a new one."))
        if len(promo_exist) > 1:
            raise UserError(_("There is an existing Specials promotion during this date/time"))

    def write(self, vals_list):
        utc = timezone("US/Pacific")
        date_format = '%Y-%m-%d'
        date = datetime.now(tz=utc)
        date = date.astimezone(timezone('US/Pacific'))
        day = date.strftime(date_format)
        vals_list['update_date'] = day
        if 'start_date' in vals_list:
            vals_list['notification'] = False
        start_date = vals_list['start_date'] if 'start_date' in vals_list else self.start_date
        end_date = vals_list['end_date'] if 'end_date' in vals_list else self.end_date
        if str(end_date) < str(start_date):
            raise UserError(_("Inconsistent start and end dates! \n"
                              "Stop date should be above the start date. "
                              "Please check the date fields and try again."))
        start_time = vals_list['start_time'] if 'start_time' in vals_list else self.start_time
        end_time = vals_list['end_time'] if 'end_time' in vals_list else self.end_time
        if end_time < start_time:
            raise UserError(_("Inconsistent start and end time! \n"
                              "Stop time should be above the start time. "
                              "Please check the time fields and try again."))
        if start_time < 0 or end_time < 0 or start_time > 24.0 or end_time > 24.0:
            raise UserError(_("Inconsistent start and end time! \n"
                              "Time should be 0 to 24.0! "
                              "Please check the time fields and try again."))
        if start_time == end_time:
            raise UserError(_("Start and End Time Can not be the same."))
        if 'micro_market_id' in vals_list:
            vals_list['mm_ids'] = vals_list['micro_market_id']
        elif 'location' in vals_list:
            location = vals_list['location'][0][2]
            location = self.env['stock.warehouse'].search([('partner_id', 'in', location)]).ids
            vals_list['mm_ids'] = [[6, False, location]]
        else:
            operator_id = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)]).ids
            vals_list['mm_ids'] = [[6, False, operator_id]]
        # vals_list['operator_id'] = self.env.user.company_id.id
        res = super(FeaturedProducts, self).write(vals_list)
        return res


class ProductFeatured(models.Model):
    _name = 'product.discount'

    special_id = fields.Many2one('featured.products', 'product_line', index=True)
    product_id = fields.Many2one('product.product', 'Product', required=True)
    price = fields.Float('Price', compute='_compute_list_price')
    discount_percentage = fields.Float('Discount %')
    discount_amount = fields.Float('Discount Amount')
    sale_price = fields.Float('Discounted Price', compute='_compute_list_price')
    categ_id = fields.Many2one('product.category', string='Category', related='product_id.categ_id')
    mm_ids = fields.Many2one('product.micro.market')

    @api.constrains('discount_percentage')
    def _check_discount(self):
        print("test")
        # if self.discount_percentage < 0 or self.discount_percentage > 99:
        #     raise UserError(_("Percentage should be between 0% to 100%!"))

    @api.model
    def init(self):
        recs = self.env['product.discount'].search([])
        print(recs)
        for rec in recs:
            if (rec.discount_percentage <= 0 or not rec.discount_percentage) and (
                    rec.discount_amount <= 0 or not rec.discount_amount) \
                    and (rec.special_id.discount_percentage <= 0 or not rec.special_id.discount_percentage):
                print(rec.special_id)
                print(rec.product_id.name)
                print(rec.price)
                rec.sale_price = rec.price
                print(rec.sale_price)
                print(rec.price)

    @api.onchange('product_id')
    def onchange_pro_id(self):
        if self.product_id:
            product_micro_markets = self.env['product.micro.market'].search(
                [('micro_market_id', '=', self.special_id.market_id.id), ('product_id', '=', self.product_id.id)],
                limit=1)
            self.mm_ids = product_micro_markets
            self.price = product_micro_markets.list_price
            if self.special_id.discount_percentage == 0:
                self.sale_price = self.price
            if self.special_id.discount_percentage > 0:
                self.discount_percentage = self.special_id.discount_percentage
                self.sale_price = self.price - ((self.price * self.special_id.discount_percentage) / 100)

    @api.onchange('discount_amount')
    def product_discount_amount(self):
        if self.discount_percentage:
            raise UserError(_("You can not add two discount method for a product!"))
        if self.discount_amount > 0:
            if self.discount_amount < 0 or self.discount_amount >= self.price:
                raise UserError(_("Discount Amount should be between 0% to " + str(self.price)))
            else:
                self.sale_price = self.price - self.discount_amount

    @api.onchange('discount_percentage')
    def product_discount_percentage(self):
        if self.discount_amount:
            raise UserError(_("You can not add two discount method for a product!"))
        if self.discount_percentage == 0:
            self.sale_price = self.price
        if self.discount_percentage:
            if self.discount_percentage <= 0 or self.discount_percentage >= 100:
                raise UserError(_("Discount Percentage should be between 0% to 100%!"))
            else:
                self.sale_price = self.price - ((self.price * self.discount_percentage) / 100)

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.special_id.categ_id.id:
            return {'domain': {'product_id': [('id', "=", self.special_id.market_id.market_product_ids.product_id.ids),
                                              ('id', "!=", self.special_id.product_line.product_id.ids),
                                              ('categ_id', "=", self.special_id.categ_id.id)]}}
        else:
            return {'domain': {'product_id': [('id', "=", self.special_id.market_id.market_product_ids.product_id.ids),
                                              ('id', "!=", self.special_id.product_line.product_id.ids)]}}

    @api.depends('mm_ids.list_price', 'special_id.discount_percentage', 'discount_percentage', 'discount_amount')
    def _compute_list_price(self):
        for rec in self:
            product_micro_markets = self.env['product.micro.market'].search(
                [('micro_market_id', '=', rec.special_id.market_id.id), ('product_id', '=', rec.product_id.id)],
                limit=1)
            if product_micro_markets and rec.product_id:
                rec.price = product_micro_markets.list_price
                rec.sale_price = product_micro_markets.list_price
                rec.price = product_micro_markets.list_price
                if rec.discount_percentage > 0:
                    rec.sale_price = product_micro_markets.list_price - (
                            (product_micro_markets.list_price * rec.discount_percentage) / 100)
                elif rec.discount_amount > 0:
                    rec.sale_price = product_micro_markets.list_price - rec.discount_amount
                elif rec.special_id.discount_percentage > 0:
                    rec.sale_price = product_micro_markets.list_price - (
                            (product_micro_markets.list_price * rec.special_id.discount_percentage) / 100)

            else:
                rec.price = product_micro_markets.list_price
                rec.sale_price = product_micro_markets.list_price
