import json

from odoo.http import Controller, request, route, _logger
from odoo import http
from odoo.exceptions import UserError

from odoo.tools import datetime

import requests


class AccessRightsAdd(Controller):
    # @route('/get_access_from_sheet', type='http', auth='public', csrf=False)
    # def get_access(self):
    #     # print("11111111111")
    #     loc = ("/home/dino/Music/Averigo_Group_User_7_11_2022 _ Adding_Access.xlsx")
    #     wb = xlrd.open_workbook(loc)
    #     sheet = wb.sheet_by_index(0)
    #     # print("sheet cell(0,0)", sheet.cell_value(0, 0))
    #     result_dict = {}
    #     item_key = ""
    #     for row in range(1, 1629):
    #         if sheet.cell_value(row, 0):
    #             # print("sheet.cell_value(row,0)", sheet.cell_value(row, 0))
    #             result_dict[sheet.cell_value(row, 0)] = []
    #             item_key = sheet.cell_value(row, 0)
    #         if sheet.cell_value(row, 1):
    #             model_id = request.env['ir.model'].sudo().search([('model', '=', sheet.cell_value(row, 1).lower())],
    #                                                              limit=1)
    #
    #             result_dict[item_key].append(model_id.get_metadata()[0].get('xmlid'))
    #             if sheet.cell_value(row, 2):
    #                 model_id = request.env['ir.model'].sudo().search([('model', '=', sheet.cell_value(row, 2).lower())],
    #                                                                  limit=1)
    #
    #                 result_dict[item_key].append(model_id.get_metadata()[0].get('xmlid'))
    #         elif sheet.cell_value(row, 2):
    #             model_id = request.env['ir.model'].sudo().search([('model', '=', sheet.cell_value(row, 2).lower())],
    #                                                              limit=1)
    #
    #             result_dict[item_key].append(model_id.get_metadata()[0].get('xmlid'))
    #     print("--------------------------ALL Access------------------------------------------")
    #     print(result_dict)
    #     print("-----------------------------End----------------------------------------------")

    @route('/add_access', type='json', auth='public', csrf=False)
    def add_access(self):
        items = request.jsonrequest['access_dict']
        operators = request.env['res.company'].sudo().search([])
        for operator in operators:
            for rec in items.keys():
                group = request.env['res.groups'].sudo().search([('name', '=', rec), ('operator_id', '=', operator.id)],
                                                                limit=1)
                if group:
                    models = items.get(rec)
                    group_models = group.model_access.mapped(
                        'model_id').ids
                    model_list = []
                    item_set = set()
                    for each_model in models:
                        if not request.env.ref(each_model).id in group_models and not request.env.ref(
                                each_model).id in item_set:
                            # print("request.env.ref(each_model).id,",request.env.ref(each_model).sudo().name)
                            model_list.append((0, 0, {
                                'name': request.env.ref(each_model).sudo().name,
                                'model_id': request.env.ref(each_model).id,
                                'perm_read': True,
                                'perm_write': True,
                                'perm_create': True,
                                'perm_unlink': False
                            }))
                        elif request.env.ref(each_model).id in group_models and not request.env.ref(
                                each_model).id in item_set:
                            group.model_access.filtered(
                                lambda l: l.model_id.id == request.env.ref(each_model).id).write({
                                'perm_read': True,
                                'perm_write': True,
                                'perm_create': True,
                                'perm_unlink': False
                            })
                        item_set.add(request.env.ref(each_model).id)

                    group.sudo().write({'model_access': model_list})
                else:
                    models = items.get(rec)
                    model_list = []
                    item_set = set()

                    for each_model in models:
                        print(":- -:", each_model)
                        if not request.env.ref(each_model).id in item_set:
                            model_list.append((0, 0, {
                                'name': request.env.ref(each_model).sudo().name,
                                'model_id': request.env.ref(each_model).id,
                                'perm_read': True,
                                'perm_write': True,
                                'perm_create': True,
                                'perm_unlink': False
                            }))
                            item_set.add(request.env.ref(each_model).id)

                    request.env['res.groups'].sudo().create({
                        'name': rec,
                        'operator_id': operator.id,
                        'averigo_group_check': True,
                        'default_groups': True,
                        'model_access': model_list
                    })

    @http.route('/add_tax_calc', type='json', auth='public', csrf=False, methods=['POST'])
    def update_tax_calc_partner(self):
        data = request.jsonrequest  # Get JSON data
        param1 = data.get('param1')
        param2 = data.get('param2')
        param_1 = str(tuple(param1))
        # print('paassaadd', param2, param1)
        # Step 1: Fetch partners
        query = """
            SELECT DISTINCT p1.street, p1.city, p1.zip, rcs.code as state_code, p1.state_id
            FROM res_partner p1
            LEFT JOIN res_country_state rcs ON rcs.id = p1.state_id
            WHERE p1.active = True AND p1.zip IS NOT NULL AND p1.city IS NOT NULL AND p1.type in ('delivery', 'contact')
              AND p1.state_id IS NOT NULL AND p1.operator_id = %s AND p1.id in %s
        """ % (param2, param_1)
        _logger.info('query_update_partner %s', query)
        # query = """
        #             SELECT DISTINCT p1.street, p1.city, p1.zip, rcs.code as state_code, p1.state_id
        #             FROM res_partner p1
        #             LEFT JOIN res_country_state rcs ON rcs.id = p1.state_id
        #             WHERE p1.active = True AND p1.zip IS NOT NULL AND p1.city IS NOT NULL AND p1.type in ('delivery', 'contact')
        #               AND p1.state_id IS NOT NULL AND p1.zip = '85224' """
        request.env.cr.execute(query)
        partners_data = request.env.cr.dictfetchall()
        _logger.error("taaaax_jan_7")
        _logger.error(partners_data)

        if not partners_data:
            return {"status": "No partners found for tax calculation"}

        # Step 2: Configuration parameters
        config_param = request.env['ir.config_parameter'].sudo()
        tax_cloud_id = config_param.get_param('tax_cloud_id')
        tax_cloud_key = config_param.get_param('tax_cloud_key')
        if not tax_cloud_id or not tax_cloud_key:
            raise UserError("Tax Cloud credentials are not configured")

        # Step 3: Process each partner
        for data in partners_data:
            partner = request.env.user.partner_id
            cart_items = [{"Qty": 1, "Price": 100, "TIC": "", "ItemID": "mm"}]

            lookup_data = {
                "apiLoginID": tax_cloud_id,
                "apiKey": tax_cloud_key,
                "customerID": partner.name,
                "deliveredBySeller": True,
                "cartID": "",
                "destination": {
                    "Address1": data['street'],
                    "City": data['city'],
                    "State": data['state_code'],
                    "Zip5": data['zip'],
                    "Zip4": ""
                },
                "origin": {
                    "Address1": data['street'],
                    "City": data['city'],
                    "State": data['state_code'],
                    "Zip5": data['zip'],
                    "Zip4": ""
                },
                "cartItems": cart_items
            }

            # Step 4: API call
            _logger.info('callingggg')
            _logger.info(
                f"_____________TaxCloudShippingAddress{request.env.uid, request.env.user.id, request.env.company.id}")
            try:
                request.env.cr.execute(
                    "INSERT INTO tax_api_calls(user_id, operator_id, function_name, screen_name,in_date)"
                    "VALUES (%s, %s, 'update_tax_calc_partner', 'Shipping Address Script',NOW() at time zone 'UTC')",
                    (request.env.uid, request.env.company.id))
            except Exception as e:
                _logger.error("%s" % str(e))
            response = requests.post("https://api.taxcloud.com/1.0/TaxCloud/Lookup", json=lookup_data)
            response.raise_for_status()
            lookup_info = response.json()
            _logger.info('mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm')
            _logger.info(lookup_info['ResponseType'])
            if lookup_info['ResponseType'] != 0:
                tax_resp = lookup_info.get('CartItemsResponse', [])
                if tax_resp:
                    tax_calc = tax_resp[0].get('TaxAmount', 0)
                    _logger.info('tax_calc_value')
                    _logger.info(tax_calc)

                    # Step 5: Update partner records
                    if tax_calc > 0:
                        partner_domain = [
                            ('zip', '=', data['zip']),
                            ('city', '=', data['city']),
                            ('state_id', '=', data['state_id']),
                            ('street', '=', data['street'])
                        ]
                        partners_to_update = request.env['res.partner'].sudo().search(partner_domain)
                        # print('deccc_1777', partners_to_update)
                        # partners_to_update.sudo().write({'tax_calc': tax_calc})
                        for partner in partners_to_update:
                            _logger.info(f"Updating partner {partner.id}: {partner.tax_calc} → {tax_calc}")
                            partner.tax_calc = tax_calc
                        # partners_to_update.sudo().write({'tax_calc': tax_calc})

        return {"status": "Tax calculation updated successfully"}

    @http.route('/add_tax_calc2', type='json', auth='public', csrf=False, methods=['POST'])
    def update_tax_calc_stock_warehouse(self):
        try:
            data = request.jsonrequest  # Get JSON data
            param1 = data.get('param1')
            param2 = str(tuple(param1))
            _logger.info('Received param1: %s %s', param1, param2)

            # Fetch warehouse records
            query = """SELECT DISTINCT sw.street, sw.city, sw.zip, rcs.code as code, sw.state_id as state
                    FROM stock_warehouse sw
                    LEFT JOIN res_country_state rcs ON rcs.id = sw.state_id
                    WHERE (sw.zip IS NOT NULL OR sw.city IS NOT NULL OR sw.state_id IS NOT NULL OR sw.street IS NOT NULL)
                    AND sw.location_type IN ('micro_market', 'view') 
                    AND sw.active = True 
                    AND sw.id in %s""" % (param2)

            request.env.cr.execute(query)
            records = request._cr.dictfetchall()

            _logger.info("Fetched records: %s", records)
            _logger.info("Fetched records count: %s", len(records))

            tax_calc = 0
            count = 0

            if not records:
                return {"status": "error", "message": "No records found"}

            # Loop through warehouse records
            for data in records:
                count += 1
                _logger.info(f"Processing warehouse {count}: {data}")

                partner = request.env.user.partner_id
                config_parm = request.env['ir.config_parameter'].sudo()

                cart_items = [{"Qty": 1, "Price": 100, "TIC": '', "ItemID": 'mm'}]

                lookup_data = {
                    "apiLoginID": config_parm.get_param('tax_cloud_id'),
                    "apiKey": config_parm.get_param('tax_cloud_key'),
                    "customerID": partner.name,
                    "deliveredBySeller": True,
                    "cartID": "",
                    "destination": {
                        "Address1": data['street'],
                        "City": data['city'],
                        "State": data['code'],
                        "Zip5": data['zip'],
                        "Zip4": ''
                    },
                    "origin": {
                        "Address1": data['street'],
                        "City": data['city'],
                        "State": data['code'],
                        "Zip5": data['zip'],
                        "Zip4": ''
                    },
                    "cartItems": cart_items
                }

                try:
                    request.env.cr.execute(
                        "INSERT INTO tax_api_calls(user_id, operator_id, function_name, screen_name, in_date) "
                        "VALUES (%s, %s, 'update_tax_calc_stock_warehouse', 'MicroMarket/Warehouse Script', NOW() AT TIME ZONE 'UTC')",
                        (request.env.uid, request.env.company.id)
                    )
                    request.env.cr.commit()
                except Exception as e:
                    _logger.error("Database error: %s", str(e))
                    continue

                try:
                    resp_lookup = requests.post(
                        "https://api.taxcloud.com/1.0/TaxCloud/Lookup",
                        json=lookup_data,
                        timeout=10  # Prevents hanging
                    )
                    lookup_info = resp_lookup.json()
                except requests.exceptions.RequestException as e:
                    _logger.error("API request failed: %s", str(e))
                    continue

                _logger.info("API Response: %s", lookup_info)

                if lookup_info.get('ResponseType') != 0:
                    tax_resp = lookup_info.get('CartItemsResponse', [])
                    if tax_resp:
                        tax_calc = tax_resp[0].get('TaxAmount', 0)
                        _logger.info(f"Tax Calculated: {tax_calc}")

                # Update warehouse records
                if tax_calc:
                    partners = request.env['stock.warehouse'].sudo().search([
                        ('zip', '=', data['zip']),
                        ('city', '=', data['city']),
                        ('state_id', '=', data['state']),
                        ('street', '=', data['street'])
                    ])
                    for partner in partners:
                        _logger.info(f"Updating warehouse {partner.id}: {partner.sales_tax} → {tax_calc}")
                        partner.sales_tax = tax_calc

                    request.env.cr.commit()

            _logger.info("Processing complete. Total records processed: %s", count)

            return {
                "status": "success",
                "records_processed": count
            }

        except Exception as e:
            _logger.error("Unexpected errorrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr: %s", str(e))
            return {"status": "error", "message": str(e)}



class Pppp(http.Controller):

    @http.route('/add_terminal_cancel', type='json', auth='public', method=['POST'], csrf=False)
    def add_terminal_cancel(self):
        for list in request.jsonrequest.get('list'):
            try:
                operator = request.env['res.company'].sudo().search(
                    [('name', '=', list['Operator'])])
                if not operator:
                    _logger.error("Invalid Operator")
                    return {"Status": 'Error',
                            "Message": "Invalid Operator"}
                micro_market = request.env['stock.warehouse'].sudo().search(
                    [('location_type', '=', 'micro_market'),
                     ('name', '=', list.get('Market'))])
                if not micro_market:
                    _logger.error("The Micromarket is not associated "
                                  "with the Operator")
                    return {"Status": 'Error',
                            "Message": "The Micromarket is not associated "
                                       "with the Operator"}
                terminal_type = list['Terminal Type']
                date_str = datetime.strptime(list['Time'], "%m-%d-%Y").strftime("%Y-%m-%d")
                print('date_strdate_str', date_str, list['Time'])
                create_datetime_str = (f"{date_str} "
                                       f"{list['Date']}")

                uniqueidentifier = list['Id']
                terminal_status = request.env['terminal.cancel'].sudo().create({
                    'operator_id': operator.id,
                    'micro_market_id': micro_market.id,
                    'type': 'timeout' if list.get('Type') ==
                                         'timeout' else 'cancel',
                    'terminal_type': 'fd' if list.get(
                        'Terminal Type') == 'FD' else 'main',
                    'session_date': create_datetime_str,
                    'uniqueidentifier': uniqueidentifier,
                    'data': {
                        'CreateDate': list.get('Time'),
                        'CreateTime': list.get('Date'),
                        'Operator': list.get('Operator'),
                        'Type': list.get('Type'),
                        'TerminalType': list.get('Terminal Type'),
                        'Version': '',
                        'BeaconMajor': '0',
                        'BeaconMinor': micro_market.beacon_minor,
                        'UniqueIdentifier': list.get('Id')
                    },
                })
                if terminal_status:
                    _logger.error("Cancel Request Success")
                    # return {"Status": 'Success'}
                else:
                    _logger.error(
                        "Cancel Request Failed for uniqueidentifier %s"
                        % uniqueidentifier)
                    # return {"Status": 'Failed'}





            except Exception as e:
                _logger.error("%s" % str(e))
                _logger.error(
                    "Failed to create record with uniqueidentifier %s"
                    % uniqueidentifier)
                # return {
                #     "Status": 'Failed',
                #     "Message": "Failed to create record with uniqueidentifier %s"
                #                % uniqueidentifier
                # }

        #     print('ddffffff', market_id.name)
        #     cancel_list.append({
        #         'CreateDate': list.get('Time'),
        #         'CreateTime': list.get('Date'),
        #         'Operator': list.get('Operator'),
        #         'Type': list.get('Type'),
        #         'TerminalType': list.get('Terminal Type'),
        #         'Version': '',
        #         'BeaconMajor': '0',
        #         'BeaconMinor': market_id.beacon_minor,
        #         'UniqueIdentifier': list.get('Id')
        #     })
        #     request.env["inventory.reconcile.line"].with_user(
        #         user.id).reconcile_inventory(request.jsonrequest, reconcile_data.id)
        # print('cancel_list', cancel_list)
