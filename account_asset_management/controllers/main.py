import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)
class MachineTransfer(http.Controller):

    @http.route('/machine_transfer_sequence', type='http', auth='none', method=['POST'], csrf=False)
    def create_machine_transfer_sequence(self, **kw):
        if request.httprequest.method == 'POST':
            operators = request.env['res.company'].sudo().with_context(active_test=False).search([])
            for operator in operators:
                transfer_seq = request.env['ir.sequence'].sudo().search(
                    [('code', '=', 'account.machine.transfer'), ('company_id', '=', operator.id)])
                if not transfer_seq:
                    transfer_seq_ctx = {
                        'name': 'Equipment Transfer Sequence',
                        'code': 'account.machine.transfer',
                        'prefix': 'TRANSFER/',
                        'padding': 5,
                        'company_id': operator.id
                    }
                    request.env['ir.sequence'].sudo().create(transfer_seq_ctx)
            return "Success"
        else:
            return "Failed"

    @http.route('/reordering_sequence', type='http', auth='none', method=['POST'], csrf=False)
    def create_reordering_sequence(self, **kw):
        if request.httprequest.method == 'POST':
            operators = request.env['res.company'].sudo().with_context(active_test=False).search([])
            for operator in operators:
                reordering_seq = request.env['ir.sequence'].sudo().search(
                    [('code', '=', 'reordering.rule'), ('company_id', '=', operator.id)])
                if not reordering_seq:
                    reordering_seq_ctx = {
                        'name': 'Reordering Rule Sequence',
                        'code': 'reordering.rule',
                        'prefix': 'RR/',
                        'padding': 5,
                        'company_id': operator.id
                    }
                    request.env['ir.sequence'].sudo().create(reordering_seq_ctx)
            return "Success"
        else:
            return "Failed"

    @http.route('/asset_transfer_type_data', type='http', auth='none',
                method=['POST'], csrf=False)
    def create_asset_transfer_type_data(self, **kw):
        if request.httprequest.method == 'POST':
            operators = request.env['res.company'].sudo().with_context(active_test=False).search([])
            for operator in operators:
                incoming_type = request.env['asset.transfer.type'].sudo().search(
                    [('code', '=', 'incoming'), ('company_id', '=', operator.id)])
                if not incoming_type:
                    incoming_type_ctx = {
                        'name': 'Receipts',
                        'code': 'incoming',
                        'sequence_code': 'IN',
                        'company_id': operator.id
                    }
                    request.env['asset.transfer.type'].sudo().create(incoming_type_ctx)
                outgoing_type = request.env['asset.transfer.type'].sudo().search(
                    [('code', '=', 'outgoing'), ('company_id', '=', operator.id)])
                if not outgoing_type:
                    outgoing_type_ctx = {
                        'name': 'Delivery',
                        'code': 'outgoing',
                        'sequence_code': 'OUT',
                        'company_id': operator.id
                    }
                    request.env['asset.transfer.type'].sudo().create(outgoing_type_ctx)
                internal_type = request.env['asset.transfer.type'].sudo().search(
                    [('code', '=', 'internal'), ('company_id', '=', operator.id)])
                if not internal_type:
                    internal_type_ctx = {
                        'name': 'Internal Transfer',
                        'code': 'internal',
                        'sequence_code': 'INT',
                        'company_id': operator.id
                    }
                    request.env['asset.transfer.type'].sudo().create(internal_type_ctx)
            return "Success"
        else:
            return "Failed"

    @http.route('/equipment_name_access', type='http', auth='none', csrf=False)
    def create_equipment_name(self, **kw):
        if request.httprequest.method == 'POST':
            operators = request.env['res.company'].sudo().with_context(active_test=False).search([])
            for operator in operators:
                machine_management_group = request.env['res.groups'].sudo().search(
                    [('name', 'in', ['Equipment Management', 'Machine Management']), ('operator_id', '=', operator.id)],
                    limit=1)
                if machine_management_group:
                    menu_list = []
                    if request.env.ref(
                            'account_asset_management.machine_name_menu').id not in machine_management_group.menu_access.ids:
                        menu_list.append((4, request.env.ref('account_asset_management.machine_name_menu').id))
                    if request.env.ref(
                            'account_asset_management.machine_model_menu').id not in machine_management_group.menu_access.ids:
                        menu_list.append((4, request.env.ref('account_asset_management.machine_model_menu').id))
                    if request.env.ref(
                            'account_asset_management.machine_model_number_menu').id not in machine_management_group.menu_access.ids:
                        menu_list.append((4, request.env.ref('account_asset_management.machine_model_number_menu').id))
                    machine_management_group.menu_access = menu_list
                    model_list = []
                    machine_group_models = machine_management_group.model_access.mapped(
                        'model_id').ids
                    model_name = request.env.ref(
                        'account_asset_management.model_equipment_name').id
                    if model_name not in machine_group_models:
                        model_list.append((0, 0, {
                            'name': 'Equipment Name',
                            'model_id': model_name,
                            'perm_write': True,
                            'perm_create': True,
                            'perm_unlink': False
                        }))
                    menu_model = request.env.ref(
                        'account_asset_management.model_equipment_model_name').id
                    if menu_model not in machine_group_models:
                        model_list.append((0, 0, {
                            'name': 'Equipment Model',
                            'model_id': menu_model,
                            'perm_write': True,
                            'perm_create': True,
                            'perm_unlink': False
                        }))
                    menu_numer = request.env.ref(
                        'account_asset_management.model_equipment_model_number').id
                    if menu_numer not in machine_group_models:
                        model_list.append((0, 0, {
                            'name': 'Equipment Model Number',
                            'model_id': menu_numer,
                            'perm_write': True,
                            'perm_create': True,
                            'perm_unlink': False
                        }))
                    machine_management_group.model_access = model_list
            return "Success"
        else:
            return "Failed"

    @http.route('/account_asset_security', type='http', auth='none', method=['POST'], csrf=False)
    def create_account_asset_security(self, **kw):
        if request.httprequest.method == 'POST':
            operators = request.env['res.company'].sudo().with_context(active_test=False).search([])
            for operator in operators:
                machine_management_group = request.env['res.groups'].sudo().search(
                    [('name', 'in', ['Equipment Management', 'Machine Management']), ('operator_id', '=', operator.id)],
                    limit=1)
                print("wrking", machine_management_group)
                if not machine_management_group:
                    machine_management_ctx = {
                        'name': 'Equipment Management',
                        'comment': 'Equipment Management Access rights',
                        'averigo_group_check': True,
                        'default_groups': True,
                        'menu_access': [
                            (6, 0, [request.env.ref('account_asset_management.equipment_management_menu').id,
                                    request.env.ref('account_asset_management.machine_management_menu').id,
                                    request.env.ref('account_asset_management.machine_bill_menu').id,
                                    request.env.ref('account_asset_management.menu_account_asset_transfer').id,
                                    request.env.ref('account_asset_management.service_configuration_menu').id,
                                    request.env.ref('account_asset_management.machine_type_menu').id,
                                    request.env.ref('account_asset_management.machine_location_menu').id,
                                    request.env.ref('account_asset_management.menu_account_asset_profile').id,
                                    request.env.ref('account_asset_management.menu_asset_transfer_type').id, ])],
                        'operator_id': operator.id,
                        'model_access': [
                            (0, 0, {
                                'name': 'Equipment Management',
                                'model_id': request.env.ref('account_asset_management.model_account_asset').id,
                                'perm_write': False,
                                'perm_create': False,
                                'perm_unlink': False
                            }),
                            (0, 0, {
                                'name': 'Equipment Bill',
                                'model_id': request.env.ref(
                                    'account_asset_management.model_account_move').id,
                                'perm_write': False,
                                'perm_create': False,
                                'perm_unlink': False
                            }),
                            (0, 0, {
                                'name': 'Equipment Transfer',
                                'model_id': request.env.ref('account_asset_management.model_account_asset_transfer').id,
                                'perm_write': False,
                                'perm_create': False,
                                'perm_unlink': False
                            }),
                            (0, 0, {
                                'name': 'Equipment Type',
                                'model_id': request.env.ref(
                                    'account_asset_management.model_account_asset_type').id,
                                'perm_write': False,
                                'perm_create': False,
                                'perm_unlink': False
                            }),
                            (0, 0, {
                                'name': 'Equipment Location',
                                'model_id': request.env.ref(
                                    'account_asset_management.model_account_asset_location').id,
                                'perm_write': False,
                                'perm_create': False,
                                'perm_unlink': False
                            }),
                            (0, 0, {
                                'name': 'Equipment Transfer Type',
                                'model_id': request.env.ref('account_asset_management.model_asset_transfer_type').id,
                                'perm_write': False,
                                'perm_create': False,
                                'perm_unlink': False
                            }),
                            (0, 0, {
                                'name': 'Case Management Type',
                                'model_id': request.env.ref('account_asset_management.model_case_management_type').id,
                                'perm_write': False,
                                'perm_create': False,
                                'perm_unlink': False
                            }),
                            (0, 0, {
                                'name': 'Equipment Profile',
                                'model_id': request.env.ref('account_asset_management.model_account_asset_profile').id,
                                'perm_write': False,
                                'perm_create': False,
                                'perm_unlink': False
                            }), (0, 0, {
                                'name': 'Equipment Note',
                                'model_id': request.env.ref('account_asset_management.model_machine_notes').id,
                                'perm_write': False,
                                'perm_create': False,
                                'perm_unlink': False
                            }),
                            (0, 0, {
                                'name': 'Equipment Note',
                                'model_id': request.env.ref('base.model_ir_attachment').id,
                                'perm_write': False,
                                'perm_create': False,
                                'perm_unlink': False
                            }),
                        ],
                    }
                    request.env['res.groups'].sudo().create(machine_management_ctx)
            return "Success"
        else:
            return "Failed"
