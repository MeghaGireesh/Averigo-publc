from odoo import models, api, fields


class ResUsersGroup(models.Model):
    _inherit = 'res.users'

    @api.model
    def create(self, vals_list):
        """This create function is used to add the access-rights"""
        res = super().create(vals_list)
        if 'create_company' in self._context and self._context[
            'create_company']:
            # res_groups = self.env['res.groups']
            res.partner_id.operator_id = res.company_id.id
            # creating service management access for new operator
            service_management_ctx = {
                'name': 'Service Management',
                'comment': 'Service Management Access rights',
                'averigo_group_check': True,
                'default_groups': True,
                'is_case_techperson': False,
                'is_case_manager': True,
                'menu_access': [
                    (6, 0, [self.env.ref(
                        'averigo_service_management.service_management_main_menu').id,
                            self.env.ref(
                                'averigo_service_management.case_management_menu').id,
                            self.env.ref(
                                'averigo_service_management.case_management_config_main_menu').id,
                            self.env.ref(
                                'averigo_service_management.case_management_channel_menu').id,
                            self.env.ref(
                                'averigo_service_management.case_management_category_menu').id,
                            self.env.ref(
                                'averigo_service_management.case_management_stage_menu').id,
                            self.env.ref(
                                'averigo_service_management.issue_type_menu').id,
                            self.env.ref(
                                'averigo_service_management.case_management_tag_menu').id,
                            # self.env.ref('averigo_service_management.case_management_subject_menu').id,
                            self.env.ref(
                                'averigo_case_management.machine_management_menu_service').id,
                            self.env.ref(
                                'averigo_case_management.schedule_tech_person_wizard_menu').id,
                            ])],
                'operator_id': vals_list['company_id'],
                'users': [(6, 0, [res.id])],
                'model_access': [
                    (0, 0, {
                        'name': 'Case Management',
                        'model_id': self.env.ref(
                            'averigo_service_management.model_case_management').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    }),
                    (0, 0, {
                        'name': 'Case Management Category',
                        'model_id': self.env.ref(
                            'averigo_service_management.model_case_management_category').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    }),
                    (0, 0, {
                        'name': 'Case Management Channel',
                        'model_id': self.env.ref(
                            'averigo_service_management.model_case_management_channel').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    }),
                    (0, 0, {
                        'name': 'Case Management Stage',
                        'model_id': self.env.ref(
                            'averigo_service_management.model_case_management_stage').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    }),
                    (0, 0, {
                        'name': 'Case Management Tag',
                        'model_id': self.env.ref(
                            'averigo_service_management.model_case_management_tag').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    }),
                    (0, 0, {
                        'name': 'Issue Type',
                        'model_id': self.env.ref(
                            'averigo_service_management.model_issue_type').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    }),
                    (0, 0, {
                        'name': 'Subject Type',
                        'model_id': self.env.ref(
                            'averigo_service_management.model_case_subject').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    }),
                    (0, 0, {
                        'name': 'Case Notes',
                        'model_id': self.env.ref(
                            'averigo_case_management.model_casemanagement_notes').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    }),
                    (0, 0, {
                        'name': 'Case Attachments',
                        'model_id': self.env.ref('base.model_ir_attachment').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    }),
                    (0, 0, {
                        'name': 'Tech Person Schedule',
                        'model_id': self.env.ref(
                            'averigo_case_management.model_schedule_tech_person').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    })
                ],
            }
            service = self.env['res.groups'].sudo().create(
                service_management_ctx)
            service_management_tech_person_ctx = {
                'name': 'Service Management Tech Person	',
                'comment': 'Service Management Tech Person Access rights',
                'averigo_group_check': True,
                'default_groups': True,
                'is_case_techperson': True,
                'is_case_manager': False,
                'menu_access': [
                    (6, 0, [self.env.ref(
                        'averigo_service_management.service_management_main_menu').id,
                            self.env.ref(
                                'averigo_service_management.case_management_menu').id,
                            self.env.ref(
                                'averigo_service_management.case_management_config_main_menu').id,
                            self.env.ref(
                                'averigo_service_management.case_management_channel_menu').id,
                            self.env.ref(
                                'averigo_service_management.case_management_category_menu').id,
                            self.env.ref(
                                'averigo_service_management.case_management_stage_menu').id,
                            self.env.ref(
                                'averigo_service_management.issue_type_menu').id,
                            self.env.ref(
                                'averigo_service_management.case_management_tag_menu').id,
                            # self.env.ref('averigo_service_management.case_management_subject_menu').id,
                            self.env.ref(
                                'averigo_case_management.machine_management_menu_service').id,
                            ])],
                'operator_id': vals_list['company_id'],
                'users': [(6, 0, [res.id])],
                'model_access': [
                    (0, 0, {
                        'name': 'Case Management',
                        'model_id': self.env.ref(
                            'averigo_service_management.model_case_management').id,
                        'perm_write': True,
                        'perm_read': True,
                        'perm_create': False,
                        'perm_unlink': False
                    }),
                    (0, 0, {
                        'name': 'Case Management Category',
                        'model_id': self.env.ref(
                            'averigo_service_management.model_case_management_category').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': False
                    }),
                    (0, 0, {
                        'name': 'Case Management Channel',
                        'model_id': self.env.ref(
                            'averigo_service_management.model_case_management_channel').id,
                        'perm_write': False,
                        'perm_create': False,
                        'perm_read': True,
                        'perm_unlink': False
                    }),
                    (0, 0, {
                        'name': 'Case Management Stage',
                        'model_id': self.env.ref(
                            'averigo_service_management.model_case_management_stage').id,
                        'perm_write': False,
                        'perm_read': True,
                        'perm_create': False,
                        'perm_unlink': False
                    }),
                    (0, 0, {
                        'name': 'Case Management Tag',
                        'model_id': self.env.ref(
                            'averigo_service_management.model_case_management_tag').id,
                        'perm_write': False,
                        'perm_read': True,
                        'perm_create': False,
                        'perm_unlink': False
                    }),
                    (0, 0, {
                        'name': 'Issue Type',
                        'model_id': self.env.ref(
                            'averigo_service_management.model_issue_type').id,
                        'perm_write': False,
                        'perm_read': True,
                        'perm_create': False,
                        'perm_unlink': False
                    }),
                    (0, 0, {
                        'name': 'Subject Type',
                        'model_id': self.env.ref(
                            'averigo_service_management.model_case_subject').id,
                        'perm_write': False,
                        'perm_read': True,
                        'perm_create': False,
                        'perm_unlink': False
                    }),
                    (0, 0, {
                        'name': 'Case Notes',
                        'model_id': self.env.ref(
                            'averigo_case_management.model_casemanagement_notes').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': False
                    }),
                    (0, 0, {
                        'name': 'Case Attachments',
                        'model_id': self.env.ref('base.model_ir_attachment').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': False
                    })
                ],
            }
            service = self.env['res.groups'].sudo().create(
                service_management_tech_person_ctx)
            service_management_stage_new = self.env[
                'case.management.stage'].sudo().search(
                [('name', '=', 'Open'),
                 ('company_id', '=', vals_list['company_id'])])
            if not service_management_stage_new:
                # creating new  stage open
                service_management_new_ctx = {
                    'sequence': 1,
                    'name': 'Open',
                    'unattended': True,
                    'closed': False,
                    'default': True,
                    # 'mail_template_id': self.env.ref(
                    # 'averigo_service_management.assignment_email_template').id,
                    'company_id': vals_list['company_id'],
                }
                self.env['case.management.stage'].sudo().create(
                    service_management_new_ctx)
            service_management_stage_progess = self.env[
                'case.management.stage'].sudo().search(
                [('name', '=', 'In Progress'),
                 ('company_id', '=', vals_list['company_id'])])
            if not service_management_stage_progess:
                # creating new stage in progress
                service_management_progess_ctx = {
                    'sequence': 2,
                    'name': 'In Progress',
                    'unattended': False,
                    'closed': False,
                    'default': True,
                    'company_id': vals_list['company_id'],
                }
                self.env['case.management.stage'].sudo().create(
                    service_management_progess_ctx)
            service_management_stage_done = self.env[
                'case.management.stage'].sudo().search(
                [('name', '=', 'Closed'),
                 ('company_id', '=', vals_list['company_id'])])
            if not service_management_stage_done:
                # create new stage done
                service_management_done_ctx = {
                    'sequence': 3,
                    'name': 'Closed',
                    'unattended': False,
                    'closed': True,
                    'default': True,
                    'company_id': vals_list['company_id'],
                }
                self.env['case.management.stage'].sudo().create(
                    service_management_done_ctx)
            service_management_stage_cancel = self.env[
                'case.management.stage'].sudo().search(
                [('name', '=', 'Cancelled'),
                 ('company_id', '=', vals_list['company_id'])])
            if not service_management_stage_cancel:
                # create new stage cancel
                service_management_cancel_ctx = {
                    'sequence': 4,
                    'name': 'Cancelled',
                    'unattended': False,
                    'closed': True,
                    'fold': True,
                    'default': True,
                    'company_id': vals_list['company_id'],
                }
                self.env['case.management.stage'].sudo().create(
                    service_management_cancel_ctx)
            # create type alarm
            case_type_alarm = self.env['case.management.type'].sudo().search(
                [('name', '=', 'Alarm'),
                 ('company_id', '=', vals_list['company_id'])])
            if not case_type_alarm:
                case_type_alarm_ctx = {
                    'name': 'Alarm',
                    'company_id': vals_list['company_id']
                }
                self.env['case.management.type'].sudo().create(
                    case_type_alarm_ctx)
            # create new type Equipment Move
            case_type_equipment_move = self.env[
                'case.management.type'].sudo().search(
                [('name', '=', 'Equipment Move'),
                 ('company_id', '=', vals_list['company_id'])])
            if not case_type_equipment_move:
                case_type_equipment_move_ctx = {
                    'name': 'Equipment Move',
                    'company_id': vals_list['company_id']
                }
                self.env['case.management.type'].sudo().create(
                    case_type_equipment_move_ctx)
            # create new  type EquipmentSwap
            case_type_equipment_swap = self.env[
                'case.management.type'].sudo().search(
                [('name', '=', 'Equipment Swap'),
                 ('company_id', '=', vals_list['company_id'])])
            if not case_type_equipment_swap:
                case_type_equipment_swap_ctx = {
                    'name': 'Equipment Swap',
                    'company_id': vals_list['company_id']
                }
                self.env['case.management.type'].sudo().create(
                    case_type_equipment_swap_ctx)
            # create new type Filter Replacement
            case_type_filter = self.env['case.management.type'].sudo().search(
                [('name', '=', 'Filter Replacement'),
                 ('company_id', '=', vals_list['company_id'])])
            if not case_type_filter:
                case_type_filter_ctx = {
                    'name': 'Filter Replacement',
                    'company_id': vals_list['company_id']
                }
                self.env['case.management.type'].sudo().create(
                    case_type_filter_ctx)
            # create new type install
            case_type_install = self.env['case.management.type'].sudo().search(
                [('name', '=', 'Install'),
                 ('company_id', '=', vals_list['company_id'])])
            if not case_type_install:
                case_type_install_ctx = {
                    'name': 'Install',
                    'company_id': vals_list['company_id']
                }
                self.env['case.management.type'].sudo().create(
                    case_type_install_ctx)
            # create new type issue
            case_type_issue = self.env['case.management.type'].sudo().search(
                [('name', '=', 'Issue'),
                 ('company_id', '=', vals_list['company_id'])])
            if not case_type_issue:
                case_type_issue_ctx = {
                    'name': 'Issue',
                    'company_id': vals_list['company_id']
                }
                self.env['case.management.type'].sudo().create(
                    case_type_issue_ctx)
            # create new type Machine issue
            case_type_machine_issue = self.env[
                'case.management.type'].sudo().search(
                [('name', '=', 'Machine Issue'),
                 ('company_id', '=', vals_list['company_id'])])
            if not case_type_machine_issue:
                case_type_machine_issue_ctx = {
                    'name': 'Machine Issue',
                    'company_id': vals_list['company_id']
                }
                self.env['case.management.type'].sudo().create(
                    case_type_machine_issue_ctx)
            # Create new type Preventive Maintenance
            case_type_preventive = self.env[
                'case.management.type'].sudo().search(
                [('name', '=', 'Preventive Maintenance'),
                 ('company_id', '=', vals_list['company_id'])])
            if not case_type_preventive:
                case_type_preventive_ctx = {
                    'name': 'Preventive Maintenance',
                    'company_id': vals_list['company_id']
                }
                self.env['case.management.type'].sudo().create(
                    case_type_preventive_ctx)
            # create new type sales inquiry
            case_type_sales_inquiry = self.env[
                'case.management.type'].sudo().search(
                [('name', '=', 'Sales Inquiry'),
                 ('company_id', '=', vals_list['company_id'])])
            if not case_type_sales_inquiry:
                case_type_sales_inquiry_ctx = {
                    'name': 'Sales Inquiry',
                    'company_id': vals_list['company_id']
                }
                self.env['case.management.type'].sudo().create(
                    case_type_sales_inquiry_ctx)
            # create new type sales issue
            case_type_sales_issue = self.env[
                'case.management.type'].sudo().search(
                [('name', '=', 'Sales Issue'),
                 ('company_id', '=', vals_list['company_id'])])
            if not case_type_sales_issue:
                case_type_sales_issue_ctx = {
                    'name': 'Sales Issue',
                    'company_id': vals_list['company_id']
                }
                self.env['case.management.type'].sudo().create(
                    case_type_sales_issue_ctx)
            # create new type service inquiry
            case_type_service_inquiry = self.env[
                'case.management.type'].sudo().search(
                [('name', '=', 'Service Inquiry'),
                 ('company_id', '=', vals_list['company_id'])])
            if not case_type_service_inquiry:
                case_type_service_inquiry_ctx = {
                    'name': 'Service Inquiry',
                    'company_id': vals_list['company_id']
                }
                self.env['case.management.type'].sudo().create(
                    case_type_service_inquiry_ctx)
            # create new channel web
            case_channel_web = self.env[
                'case.management.channel'].sudo().search(
                [('name', '=', 'Web'),
                 ('company_id', '=', vals_list['company_id'])])
            if not case_channel_web:
                case_channel_web_ctx = {
                    'name': 'Web',
                    'company_id': vals_list['company_id']
                }
                self.env['case.management.channel'].sudo().create(
                    case_channel_web_ctx)
            # create new channel email
            case_channel_email = self.env[
                'case.management.channel'].sudo().search(
                [('name', '=', 'Email'),
                 ('company_id', '=', vals_list['company_id'])])
            if not case_channel_email:
                case_channel_email_ctx = {
                    'name': 'Email',
                    'company_id': vals_list['company_id']
                }
                self.env['case.management.channel'].sudo().create(
                    case_channel_email_ctx)
            # create new channel phone
            case_channel_phone = self.env[
                'case.management.channel'].sudo().search(
                [('name', '=', 'Phone'),
                 ('company_id', '=', vals_list['company_id'])])
            if not case_channel_phone:
                case_channel_phone_ctx = {
                    'name': 'Phone',
                    'company_id': vals_list['company_id']
                }
                self.env['case.management.channel'].sudo().create(
                    case_channel_phone_ctx)
            # create new channel Other
            case_channel_other = self.env[
                'case.management.channel'].sudo().search(
                [('name', '=', 'Other'),
                 ('company_id', '=', vals_list['company_id'])])
            if not case_channel_other:
                case_channel_other_ctx = {
                    'name': 'Other',
                    'company_id': vals_list['company_id']
                }
                self.env['case.management.channel'].sudo().create(
                    case_channel_other_ctx)
            # create new Case Sequence
            case_sequence = self.env['ir.sequence'].sudo().search(
                [('code', '=', 'case.management.sequence'),
                 ('company_id', '=', vals_list['company_id'])])
            if not case_sequence:
                case_sequence_ctx = {
                    'name': 'Case Management Sequence',
                    'code': 'case.management.sequence',
                    'prefix': 'CM',
                    'padding': 5,
                    'company_id': vals_list['company_id']
                }
                self.env['ir.sequence'].sudo().create(case_sequence_ctx)
            case_subject_other = self.env['case.subject'].sudo().search(
                [('name', '=', 'Other'),
                 ('company_id', '=', vals_list['company_id'])])
            if not case_subject_other:
                case_subject_other_ctx = {
                    'name': 'Other',
                    'company_id': vals_list['company_id']
                }
                self.env['case.subject'].sudo().create(case_subject_other_ctx)
            # Machine Access and datas ----------
            machine_management_ctx = {
                'name': 'Machine Management',
                'comment': 'Machine Management Access rights',
                'averigo_group_check': True,
                'default_groups': True,
                'menu_access': [
                    (6, 0, [self.env.ref(
                        'account_asset_management.equipment_management_menu').id,
                            self.env.ref(
                                'account_asset_management.machine_management_menu').id,
                            self.env.ref(
                                'account_asset_management.machine_bill_menu').id,
                            self.env.ref(
                                'account_asset_management.menu_account_asset_transfer').id,
                            self.env.ref(
                                'account_asset_management.service_configuration_menu').id,
                            self.env.ref(
                                'account_asset_management.machine_type_menu').id,
                            self.env.ref(
                                'account_asset_management.machine_location_menu').id,
                            self.env.ref(
                                'account_asset_management.menu_account_asset_profile').id,
                            self.env.ref(
                                'account_asset_management.menu_asset_transfer_type').id,
                            self.env.ref(
                                'account_asset_management.machine_name_menu').id,
                            self.env.ref(
                                'account_asset_management.machine_model_menu').id,
                            self.env.ref(
                                'account_asset_management.machine_model_number_menu').id, ])],
                'operator_id': vals_list['company_id'],
                'users': [(6, 0, [res.id])],
                'model_access': [
                    (0, 0, {
                        'name': 'Machine Management',
                        'model_id': self.env.ref(
                            'account_asset_management.model_account_asset').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    }),
                    (0, 0, {
                        'name': 'Machine Bill',
                        'model_id': self.env.ref(
                            'account_asset_management.model_account_move').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    }),
                    (0, 0, {
                        'name': 'Machine Transfer',
                        'model_id': self.env.ref(
                            'account_asset_management.model_account_asset_transfer').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    }),
                    (0, 0, {
                        'name': 'Machine Type',
                        'model_id': self.env.ref(
                            'account_asset_management.model_account_asset_type').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    }),
                    (0, 0, {
                        'name': 'Machine Location',
                        'model_id': self.env.ref(
                            'account_asset_management.model_account_asset_location').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    }),
                    (0, 0, {
                        'name': 'Machine Transfer Type',
                        'model_id': self.env.ref(
                            'account_asset_management.model_asset_transfer_type').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    }),
                    (0, 0, {
                        'name': 'Case Management Type',
                        'model_id': self.env.ref(
                            'account_asset_management.model_case_management_type').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    }),
                    (0, 0, {
                        'name': 'Machine Profile',
                        'model_id': self.env.ref(
                            'account_asset_management.model_account_asset_profile').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    }), (0, 0, {
                        'name': 'Machine Note',
                        'model_id': self.env.ref(
                            'account_asset_management.model_machine_notes').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    }),
                    (0, 0, {
                        'name': 'Machine Note',
                        'model_id': self.env.ref('base.model_ir_attachment').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    }),
                    (0, 0, {
                        'name': 'Equipment Name',
                        'model_id': self.env.ref(
                            'account_asset_management.model_equipment_name').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    }),
                    (0, 0, {
                        'name': 'Equipment Model',
                        'model_id': self.env.ref(
                            'account_asset_management.model_equipment_model_name').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    }),
                    (0, 0, {
                        'name': 'Equipment Model Number',
                        'model_id': self.env.ref(
                            'account_asset_management.model_equipment_model_number').id,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True
                    })
                ],
            }
            self.env['res.groups'].sudo().create(machine_management_ctx)
            # type Receipt
            incoming_type = self.env['asset.transfer.type'].sudo().search(
                [('code', '=', 'incoming'),
                 ('company_id', '=', vals_list['company_id'])])
            if not incoming_type:
                incoming_type_ctx = {
                    'name': 'Receipts',
                    'code': 'incoming',
                    'sequence_code': 'IN',
                    'company_id': vals_list['company_id']
                }
                self.env['asset.transfer.type'].sudo().create(incoming_type_ctx)
            # type delivery
            outgoing_type = self.env['asset.transfer.type'].sudo().search(
                [('code', '=', 'outgoing'),
                 ('company_id', '=', vals_list['company_id'])])
            if not outgoing_type:
                outgoing_type_ctx = {
                    'name': 'Delivery',
                    'code': 'outgoing',
                    'sequence_code': 'OUT',
                    'company_id': vals_list['company_id']
                }
                self.env['asset.transfer.type'].sudo().create(outgoing_type_ctx)
            # internal transfer
            internal_type = self.env['asset.transfer.type'].sudo().search(
                [('code', '=', 'internal'),
                 ('company_id', '=', vals_list['company_id'])])
            if not internal_type:
                internal_type_ctx = {
                    'name': 'Internal Transfer',
                    'code': 'internal',
                    'sequence_code': 'INT',
                    'company_id': vals_list['company_id']
                }
                self.env['asset.transfer.type'].sudo().create(internal_type_ctx)
            # reordering sequence
            reordering_seq = self.env['ir.sequence'].sudo().search(
                [('code', '=', 'reordering.rule'),
                 ('company_id', '=', vals_list['company_id'])])
            if not reordering_seq:
                reordering_seq_ctx = {
                    'name': 'Reordering Rule Sequence',
                    'code': 'reordering.rule',
                    'prefix': 'RR/',
                    'padding': 5,
                    'company_id': vals_list['company_id']
                }
                self.env['ir.sequence'].sudo().create(reordering_seq_ctx)
            # machine transfer sequence
            transfer_seq = self.env['ir.sequence'].sudo().search(
                [('code', '=', 'account.machine.transfer'),
                 ('company_id', '=', vals_list['company_id'])])
            if not transfer_seq:
                transfer_seq_ctx = {
                    'name': 'Machine Transfer Sequence',
                    'code': 'account.machine.transfer',
                    'prefix': 'TRANSFER/',
                    'padding': 5,
                    'company_id': vals_list['company_id']
                }
                self.env['ir.sequence'].sudo().create(transfer_seq_ctx)

            operator = self.env['res.company'].sudo().search(
                [('id', '=', vals_list['company_id'])], limit=1)
            # for operator in operators:
            parts_location_data = self.env['stock.warehouse'].sudo().search(
                [('name', '=', str(operator.name) + "parts_location"),
                 ('company_id', '=', vals_list['company_id'])],
                limit=1)
            if not parts_location_data:
                self.env['stock.warehouse'].sudo().create({
                    'name': "Machine parts location",
                    'location_type': 'view',
                    'code': str(operator.name) + "_parts_location",
                    'is_parts_warehouse': True,
                    'company_id': vals_list['company_id'],
                    'zip': operator.zip if operator.zip else ""

                })
        return res


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_address = fields.Char(string='Address',
                                   compute='_compute_customer_address',
                                   search='_search_customer_address')

    send_case_mail = fields.Boolean(string="Send Case Mails", help="Send Case "
                                                                   "Management "
                                                                   "Mail's to "
                                                                   "Accounts "
                                                                   "Manager.")

    def _compute_customer_address(self):
        """We don't want to save the customer address separate so added a
                compute field.But this computes function will not work any timee.But
                we need to provide the compute otherwise the search function will not
                work."""
        for rec in self:
            rec.customer_address = False

        return False

    def _search_customer_address(self, operator, value):
        """ Search function is added to search the customer address. """
        customer_address = self.env['res.partner'].search(
            ['|', '|', '|', ('street', 'ilike', value),
             ('city', 'ilike', value), ('zip', 'ilike', value),
             ('county', 'ilike', value)])
        return [('id', 'in', customer_address.ids)]
