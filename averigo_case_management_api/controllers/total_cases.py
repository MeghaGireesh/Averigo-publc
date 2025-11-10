from odoo import http
import re
import json
from odoo.http import request, Response
from odoo.tools import datetime
from datetime import datetime, timezone
import pytz


class TotalCases(http.Controller):

    @http.route('/Averigo/RestApi/total_cases', type='http', method=['POST'],
                auth='public', csrf=False)
    def total_cases(self, **kwargs):
        """ Generated API to show all cases based on logged user operator,
          If a user logged in, We need to show all the cases (both open and in-progress state) in his operator """
        last_updated_date = datetime.now().strftime('%m/%d/%Y %H:%M:%S'),

        if request.httprequest.method == 'POST':
            company_id = request.env['res.company'].sudo().search(
                [('operator_domain', '=', kwargs['OperatorDomain'].lower())])

            if not company_id:
                return Response(json.dumps({
                    "status": "Error",
                    "message": "Invalid Operator domain"
                }), headers={'content-type': 'application/json'})

            total_cases = request.env['case.management'].sudo().search(
                [('company_id', '=', company_id.id)])

            closed_cases = total_cases.filtered(lambda s: s.stage_id.closed == True)

            total_case_ids = total_cases.filtered(
                lambda s: not (s.stage_id.closed == True))
            if kwargs['date']:
                request_date_ids = total_case_ids.filtered(lambda s: s.app_create_date)
                try:
                    datetime_object = datetime.strptime(kwargs['date'], '%m/%d/%Y %H:%M:%S')
                    if datetime_object:
                        total_case_ids = request_date_ids.filtered(
                            lambda s: s.app_create_date.strftime('%m/%d/%Y %H:%M:%S') == kwargs['date'])
                except ValueError:
                    total_case_ids = request_date_ids.filtered(
                        lambda s: s.app_create_date.strftime('%m/%d/%Y') == kwargs['date'])

            if kwargs['caseNo']:
                number_ids = total_case_ids.filtered(lambda s: s.number)
                total_case_ids = number_ids.filtered(lambda s: s.number == kwargs['caseNo'])

            if kwargs['customerId']:
                partner_ids = total_case_ids.filtered(lambda s: s.partner_id)
                total_case_ids = partner_ids.filtered(lambda s: s.partner_id.id == int(kwargs['customerId']))

            if kwargs['city']:
                case_city_ids = total_case_ids.filtered(lambda s: s.city)
                total_case_ids = case_city_ids.filtered(lambda s: s.city == kwargs['city'])

            if kwargs['statusId']:
                case_status_ids = total_case_ids.filtered(lambda s: s.stage_id)
                total_case_ids = case_status_ids.filtered(lambda s: s.stage_id.id == int(kwargs['statusId']))

            if kwargs['techId']:
                """filter by tech person name"""
                tech_person_id = request.env['hr.employee'].sudo().search([('id', '=', int(kwargs['techId']))])
                total_case_ids = total_case_ids.search([('employee_ids', '=', tech_person_id.id),
                                                        ('stage_id.name', 'not in', ["Cancelled", "Closed"])])

            if kwargs['customerAddress']:
                partner_addresses = total_case_ids.filtered(lambda s: s.partner_address)
                total_case_ids = partner_addresses.filtered(lambda s: kwargs['customerAddress'] in s.partner_address)

            if kwargs['caseTypeId']:
                case_type_ids = total_case_ids.filtered(lambda s: s.type_id)
                total_case_ids = case_type_ids.filtered(lambda s: s.type_id.id == int(kwargs['caseTypeId']))

            if not total_case_ids:
                return Response(json.dumps({
                    "status": "Error",
                    "message": "Case does not exist"
                }), headers={'content-type': 'application/json'})

            def remove_html_tags(html_string):
                """Use a regular expression to remove HTML tags"""
                clean_text = re.sub(r'<.*?>', '', html_string)
                return clean_text

            case_list = []

            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url_with_https = base_url.replace("http://", "https://")
            for rec in total_case_ids:
                attachment_list = []
                if rec.attachment_count > 0:
                    attachments = request.env['ir.attachment'].sudo().search(
                        [('res_model', '=', 'case.management'), ('res_id', '=', rec.id),
                         ('company_id', '=', rec.company_id.id)])
                    for record in attachments:
                        url = '%s/web/image_get?model=ir.attachment&id=%s&name=%s&field=datas' % (
                            url_with_https, record.id, record.name,
                        )
                        date_obj = datetime.strptime(str(record.create_date), "%Y-%m-%d %H:%M:%S.%f")
                        attachments = {
                            'fileName': record.name,
                            'fileSize': record.file_size,
                            'uploadedBy': record.create_uid.name,
                            'uploadedDate': date_obj.strftime("%m/%d/%Y %H:%M:%S"),
                            "attachment": url,
                        }
                        attachment_list.append(attachments)

                # comment_list = ""
                comments_list = []
                if rec.case_description_ids:
                    for res in rec.case_description_ids:
                        # internal_comment = "<p>" + str(
                        #     res.create_date) + "</\t>" + res.create_uid.name + "</\t>" + res.description + "</p>"
                        # comment_list += internal_comment

                        date_obj = datetime.strptime(str(res.create_date), "%Y-%m-%d %H:%M:%S.%f")

                        internal_comment_list = {
                            "date": date_obj.strftime("%m/%d/%Y %H:%M:%S"),
                            "comments": res.description,
                            "user": res.create_uid.name
                        }
                        comments_list.append(internal_comment_list)

                resolution_list = []
                if rec.case_resolution_ids:
                    for record in rec.case_resolution_ids:
                        date_obj = datetime.strptime(str(record.create_date), "%Y-%m-%d %H:%M:%S.%f")
                        resolution_comment_list = {
                            "date": date_obj.strftime("%m/%d/%Y %H:%M:%S"),
                            "comments": record.resolution,
                            "user": record.create_uid.name
                        }
                        resolution_list.append(resolution_comment_list)

                employee_list = []
                for res in rec.employee_ids:
                    tech_details = {
                        "techId": res.id,
                        "techPersons": f"""{res.first_name} {res.last_name}""",
                    }
                    employee_list.append(tech_details)
                if rec.partner_address:
                    acc_name = rec.partner_id.kam.first_name if rec.partner_id.kam.first_name else ''
                    acc_name += ' '
                    acc_name += rec.partner_id.kam.last_name if rec.partner_id.kam.last_name else ''
                    cases = {
                        "createdDateTime": rec.app_create_date.strftime('%m/%d/%Y %H:%M:%S'),
                        "updateDateTime": rec.app_update_date.strftime('%m/%d/%Y %H:%M:%S'),
                        "caseId": rec.id,
                        "caseNo": rec.number,
                        "open": rec.open_from,
                        "customerId": rec.partner_id.id,
                        "customer": rec.partner_id.name if rec.partner_id.name else '',
                        "customerAddress": rec.partner_address.replace('\n', ' ') if rec.partner_address.replace('\n',
                                                                                                                 ' ') else '',
                        "zip": rec.zip,
                        "street": rec.street,
                        "street2": rec.street2 if rec.street2 else '',
                        "state": rec.state_id.name,
                        "county": rec.county,
                        "city": rec.city if rec.city else '',
                        "tech": employee_list,
                        "caseType": rec.type_id.name,
                        "route": rec.route_id.name if rec.route_id else "",
                        "caseStatus": rec.stage_id.name,
                        "info": remove_html_tags(rec.case_description),
                        "internalComments": comments_list,
                        "resolutionComments": resolution_list,
                        "equipmentID": rec.machine_ids.id if rec.machine_ids.id else '',
                        "equipmentCode": rec.machine_ids.code if rec.machine_ids.code else '',
                        "equipmentSerialNumber": rec.machine_ids.serial_no if rec.machine_ids.serial_no else '',
                        "equipmentName": rec.machine_ids.name if rec.machine_ids.name else '',
                        "equipmentType": rec.machine_ids.machine_type_id.name if rec.machine_ids.machine_type_id.name else '',
                        "equipmentWareHouse": rec.warehouse_id.name if rec.warehouse_id.name else '',
                        "equipmentLocation": rec.location_dest_id.name if rec.location_dest_id.name else '',
                        'billable': rec.is_billable,
                        'reported_by': rec.reported_by,
                        'account_manager': acc_name,
                        'createdBy': rec.create_uid.name,
                        "attachments ": json.dumps(attachment_list) if rec.attachment_count > 0 else json.dumps([]),
                    }
                    case_list.append(cases)
            return Response(json.dumps({
                "status": "Success",
                "LastSyncDateTime": last_updated_date[0],
                "openCases": len(total_case_ids),
                "closedCases": len(closed_cases),
                "totalCases": case_list
            }), headers={'content-type': 'application/json'})
        return None


class TotalCasesV2(http.Controller):

    @http.route('/Averigo/RestApi/total_cases_V2', type='http', method=['POST'],
                auth='public', csrf=False)
    def total_cases_v2(self, **kwargs):
        """ Generated API to show all cases based on logged user operator,
          If a user logged in, We need to show all the cases (both open and in-progress state) in his operator """
        global create_time_local, write_time_local
        user_id = request.env['res.users'].sudo().search([('id', '=', kwargs['UserId'])])
        user_tz = pytz.timezone(user_id.tz)
        updt_utc = pytz.utc.localize(datetime.now())
        current_date = updt_utc.astimezone(user_tz)

        if request.httprequest.method == 'POST':
            company_id = request.env['res.company'].sudo().search(
                [('operator_domain', '=', kwargs['OperatorDomain'].lower())])

            if not company_id:
                return Response(json.dumps({
                    "status": "Error",
                    "message": "Invalid Operator domain"
                }), headers={'content-type': 'application/json'})

            total_cases = request.env['case.management'].sudo().search(
                [('company_id', '=', company_id.id)])

            closed_cases = total_cases.filtered(lambda s: s.stage_id.closed == True)

            total_case_ids = total_cases.filtered(
                lambda s: not (s.stage_id.closed == True))

            if kwargs['UserId']:
                case_group_ids = request.env['res.groups'].sudo().search(
                    [('users', '=', int(kwargs['UserId'])),
                     ('name', '=', 'Service Management')]).ids
                if case_group_ids:
                    total_case_ids = total_cases.filtered(
                        lambda s: not (s.stage_id.closed == True))
                else:
                    tech_group_ids = request.env['res.groups'].sudo().search(
                        [('users', '=', int(kwargs['UserId'])),
                         ('name', '=', 'Service Management Tech Person')]).ids
                    if tech_group_ids:
                        total_case_ids = request.env['case.management'].sudo().search(
                            [('company_id', '=', company_id.id),('stage_id.closed','=',False),('allowed_user_ids','in',[int(kwargs['UserId'])])])
                    else:
                        return Response(json.dumps({
                            "status": "Error",
                            "message": "Case does not exist"
                        }), headers={'content-type': 'application/json'})


            if kwargs['date']:
                try:
                    datetime_object = datetime.strptime(kwargs['date'], '%m/%d/%Y %H:%M:%S')
                    if datetime_object:
                        total_case_ids = total_case_ids.filtered(
                            lambda s: s.app_create_date.strftime('%m/%d/%Y %H:%M:%S') == kwargs['date'])
                except ValueError:
                    total_case_ids = total_case_ids.filtered(
                        lambda s: s.app_create_date.strftime('%m/%d/%Y') == kwargs['date'])

            # if kwargs['updatedDate']:
            #     try:
            #         datetime_object = datetime.strptime(kwargs['updatedDate'], '%m/%d/%Y %H:%M:%S')
            #         if datetime_object:
            #             total_case_ids = total_case_ids.filtered(
            #                 lambda s: s.write_date.strftime('%m/%d/%Y %H:%M:%S') > kwargs['updatedDate'])
            #     except ValueError:
            #         total_case_ids = total_case_ids.filtered(
            #             lambda s: s.app_create_date.strftime('%m/%d/%Y') == kwargs['updatedDate'])

            if kwargs['caseNo']:
                number_ids = total_case_ids.filtered(lambda s: s.number)
                total_case_ids = number_ids.filtered(lambda s: s.number == kwargs['caseNo'])

            if kwargs['customerId']:
                partner_ids = total_case_ids.filtered(lambda s: s.partner_id)
                total_case_ids = partner_ids.filtered(lambda s: s.partner_id.id == int(kwargs['customerId']))

            if kwargs['city']:
                case_city_ids = total_case_ids.filtered(lambda s: s.city)
                total_case_ids = case_city_ids.filtered(lambda s: s.city == kwargs['city'])

            if kwargs['statusId']:
                case_status_ids = total_case_ids.filtered(lambda s: s.stage_id)
                total_case_ids = case_status_ids.filtered(lambda s: s.stage_id.id == int(kwargs['statusId']))

            if kwargs['customerAddress']:
                partner_addresses = total_case_ids.filtered(lambda s: s.partner_address)
                total_case_ids = partner_addresses.filtered(lambda s: kwargs['customerAddress'] in s.partner_address)

            if kwargs['caseTypeId']:
                case_type_ids = total_case_ids.filtered(lambda s: s.type_id)
                total_case_ids = case_type_ids.filtered(lambda s: s.type_id.id == int(kwargs['caseTypeId']))

            if not total_case_ids:
                return Response(json.dumps({
                    "status": "Error",
                    "message": "Case does not exist"
                }), headers={'content-type': 'application/json'})

            def remove_html_tags(html_string):
                """Use a regular expression to remove HTML tags"""
                clean_text = re.sub(r'<.*?>', '', html_string)
                return clean_text

            case_list = []

            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url_with_https = base_url.replace("http://", "https://")
            for rec in total_case_ids:
                create_time_utc = datetime.strptime(str(rec.create_date), "%Y-%m-%d %H:%M:%S.%f")
                write_time_utc = datetime.strptime(str(rec.write_date), "%Y-%m-%d %H:%M:%S.%f")

                if user_id.tz:
                    user_tz = pytz.timezone(user_id.tz)
                    create_utc = pytz.utc.localize(create_time_utc)
                    write_utc = pytz.utc.localize(write_time_utc)

                    create_time_local = create_utc.astimezone(user_tz)
                    write_time_local = write_utc.astimezone(user_tz)
                else:
                    user_tz = pytz.timezone(company_id.timezone)
                    create_utc = pytz.utc.localize(create_time_utc)
                    write_utc = pytz.utc.localize(write_time_utc)

                    create_time_local = create_utc.astimezone(user_tz)
                    write_time_local = write_utc.astimezone(user_tz)

                attachment_list = []
                if rec.attachment_count > 0:
                    attachments = request.env['ir.attachment'].sudo().search(
                        [('res_model', '=', 'case.management'), ('res_id', '=', rec.id),
                         ('company_id', '=', rec.company_id.id)])
                    for record in attachments:
                        url = '%s/web/image_get?model=ir.attachment&id=%s&name=%s&field=datas' % (
                            url_with_https, record.id, record.name,
                        )
                        date_obj = datetime.strptime(str(record.create_date), "%Y-%m-%d %H:%M:%S.%f")
                        attachments = {
                            'fileName': record.name,
                            'fileSize': record.file_size,
                            'uploadedBy': record.create_uid.name,
                            'uploadedDate': date_obj.strftime("%m/%d/%Y %H:%M:%S"),
                            "attachment": url,
                        }
                        attachment_list.append(attachments)

                # comment_list = ""
                comments_list = []
                if rec.case_description_ids:
                    for res in rec.case_description_ids:
                        # internal_comment = "<p>" + str(
                        #     res.create_date) + "</\t>" + res.create_uid.name + "</\t>" + res.description + "</p>"
                        # comment_list += internal_comment

                        date_obj = datetime.strptime(str(res.create_date), "%Y-%m-%d %H:%M:%S.%f")

                        internal_comment_list = {
                            "date": date_obj.strftime("%m/%d/%Y %H:%M:%S"),
                            "comments": res.description,
                            "user": res.create_uid.name
                        }
                        comments_list.append(internal_comment_list)

                resolution_list = []
                if rec.case_resolution_ids:
                    for record in rec.case_resolution_ids:
                        date_obj = datetime.strptime(str(record.create_date), "%Y-%m-%d %H:%M:%S.%f")
                        resolution_comment_list = {
                            "date": date_obj.strftime("%m/%d/%Y %H:%M:%S"),
                            "comments": record.resolution,
                            "user": record.create_uid.name
                        }
                        resolution_list.append(resolution_comment_list)

                employee_list = []
                for res in rec.employee_ids:
                    tech_details = {
                        "techId": res.id,
                        "techPersons": f"""{res.first_name if res.first_name else ''} {res.last_name if res.last_name else ''}""",
                    }
                    employee_list.append(tech_details)
                if rec.partner_address:
                    acc_name = rec.partner_id.kam.first_name if rec.partner_id.kam.first_name else ''
                    acc_name += ' '
                    acc_name += rec.partner_id.kam.last_name if rec.partner_id.kam.last_name else ''
                    cases = {
                        "createdDateTime": create_time_local.strftime('%m/%d/%Y %H:%M:%S'),
                        "updateDateTime": write_time_local.strftime('%m/%d/%Y %H:%M:%S'),
                        "caseId": rec.id,
                        "caseNo": rec.number,
                        "open": rec.open_from,
                        "customerId": rec.partner_id.id,
                        "customer": rec.partner_id.name if rec.partner_id.name else '',
                        "customerAddress": rec.partner_address.replace('\n', ' ') if rec.partner_address.replace('\n',
                                                                                                                 ' ') else '',
                        "zip": rec.zip,
                        "street": rec.street,
                        "street2": rec.street2 if rec.street2 else '',
                        "state": rec.state_id.name,
                        "county": rec.county,
                        "city": rec.city if rec.city else '',
                        "tech": employee_list,
                        "caseType": rec.type_id.name,
                        "route": rec.route_id.name if rec.route_id else "",
                        "caseStatus": rec.stage_id.name,
                        "info": remove_html_tags(rec.case_description),
                        "internalComments": comments_list,
                        "resolutionComments": resolution_list,
                        "equipmentID": rec.machine_ids.id if rec.machine_ids.id else '',
                        "equipmentCode": rec.machine_ids.code if rec.machine_ids.code else '',
                        "equipmentSerialNumber": rec.machine_ids.serial_no if rec.machine_ids.serial_no else '',
                        "equipmentName": rec.machine_ids.name if rec.machine_ids.name else '',
                        "equipmentType": rec.machine_ids.machine_type_id.name if rec.machine_ids.machine_type_id.name else '',
                        "equipmentWareHouse": rec.warehouse_id.name if rec.warehouse_id.name else '',
                        "equipmentLocation": rec.location_dest_id.name if rec.location_dest_id.name else '',
                        'billable': rec.is_billable,
                        'reported_by': rec.reported_by,
                        'account_manager': acc_name,
                        'createdBy': rec.create_uid.name,
                        "attachments ": json.dumps(attachment_list) if rec.attachment_count > 0 else json.dumps([]),
                    }
                    case_list.append(cases)
            return Response(json.dumps({
                "status": "Success",
                # "LastSyncDateTime": str(last_updated_date),
                "LastSyncDateTime": current_date.strftime('%m/%d/%Y %H:%M:%S'),
                "openCases": len(total_case_ids),
                "closedCases": len(closed_cases),
                "totalCases": case_list
            }), headers={'content-type': 'application/json'})
        return None


class TotalCasesV3(http.Controller):

    @http.route('/Averigo/RestApi/total_cases_V3', type='http', method=['POST'],
                auth='public', csrf=False)
    def total_cases_v3(self, **kwargs):
        """ Generated API to show all cases based on logged user operator,
          If a user logged in, We need to show all the cases (both open and in-progress state) in his operator """

        global create_time_local, write_time_local
        user_id = request.env['res.users'].sudo().search([('id', '=', kwargs['UserId'])])
        user_tz = pytz.timezone(user_id.tz)
        updt_utc = pytz.utc.localize(datetime.now())
        current_date = updt_utc.astimezone(user_tz)

        if request.httprequest.method == 'POST':
            company_id = request.env['res.company'].sudo().search(
                [('operator_domain', '=', kwargs['OperatorDomain'].lower())])

            if not company_id:
                return Response(json.dumps({
                    "status": "Error",
                    "message": "Invalid Operator domain"
                }), headers={'content-type': 'application/json'})

            total_cases = request.env['case.management'].sudo().search(
                [('company_id', '=', company_id.id)])

            closed_cases = total_cases.filtered(lambda s: s.stage_id.closed == True)

            total_case_ids = total_cases.filtered(
                lambda s: not (s.stage_id.closed == True))

            if kwargs['UserId']:
                case_group_ids = request.env['res.groups'].sudo().search(
                    [('users', '=', int(kwargs['UserId'])),
                     ('name', '=', 'Service Management')]).ids
                if case_group_ids:
                    total_case_ids = total_cases.filtered(
                        lambda s: not (s.stage_id.closed == True))
                else:
                    tech_group_ids = request.env['res.groups'].sudo().search(
                        [('users', '=', int(kwargs['UserId'])),
                         ('name', '=', 'Service Management Tech Person')]).ids
                    if tech_group_ids:
                        total_case_ids = request.env['case.management'].sudo().search(
                            [('company_id', '=', company_id.id),('stage_id.closed','=',False),('allowed_user_ids','in',[int(kwargs['UserId'])])])
                    else:
                        return Response(json.dumps({
                            "status": "Error",
                            "message": "Case does not exist"
                        }), headers={'content-type': 'application/json'})


            if kwargs['date']:
                try:
                    datetime_object = datetime.strptime(kwargs['date'], '%m/%d/%Y %H:%M:%S')
                    if datetime_object:
                        total_case_ids = total_case_ids.filtered(
                            lambda s: s.app_create_date.strftime('%m/%d/%Y %H:%M:%S') == kwargs['date'])
                except ValueError:
                    total_case_ids = total_case_ids.filtered(
                        lambda s: s.app_create_date.strftime('%m/%d/%Y') == kwargs['date'])

            if kwargs['caseNo']:
                number_ids = total_case_ids.filtered(lambda s: s.number)
                total_case_ids = number_ids.filtered(lambda s: s.number == kwargs['caseNo'])

            if kwargs['customerId']:
                partner_ids = total_case_ids.filtered(lambda s: s.partner_id)
                total_case_ids = partner_ids.filtered(lambda s: s.partner_id.id == int(kwargs['customerId']))

            if kwargs['city']:
                case_city_ids = total_case_ids.filtered(lambda s: s.city)
                total_case_ids = case_city_ids.filtered(lambda s: s.city == kwargs['city'])

            if kwargs['statusId']:
                case_status_ids = total_case_ids.filtered(lambda s: s.stage_id)
                total_case_ids = case_status_ids.filtered(lambda s: s.stage_id.id == int(kwargs['statusId']))

            if kwargs['customerAddress']:
                partner_addresses = total_case_ids.filtered(lambda s: s.partner_address)
                total_case_ids = partner_addresses.filtered(lambda s: kwargs['customerAddress'] in s.partner_address)

            if kwargs['caseTypeId']:
                case_type_ids = total_case_ids.filtered(lambda s: s.type_id)
                total_case_ids = case_type_ids.filtered(lambda s: s.type_id.id == int(kwargs['caseTypeId']))

            if not total_case_ids:
                return Response(json.dumps({
                    "status": "Error",
                    "message": "Case does not exist"
                }), headers={'content-type': 'application/json'})

            def remove_html_tags(html_string):
                """Use a regular expression to remove HTML tags"""
                clean_text = re.sub(r'<.*?>', '', html_string)
                return clean_text

            case_list = []

            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url_with_https = base_url.replace("http://", "https://")

            if kwargs['updatedDate']:
                total_case_ids = request.env['case.management'].sudo().search(
                    [('company_id', '=', company_id.id)])
                for rec in total_case_ids:
                    create_time_utc = datetime.strptime(str(rec.app_create_date), "%Y-%m-%d %H:%M:%S")
                    write_time_utc = datetime.strptime(str(rec.app_update_date), "%Y-%m-%d %H:%M:%S")

                    if user_id.tz:
                        user_tz = pytz.timezone(user_id.tz)
                        create_utc = pytz.utc.localize(create_time_utc)
                        write_utc = pytz.utc.localize(write_time_utc)

                        create_time_local = create_utc.astimezone(user_tz)
                        write_time_local = write_utc.astimezone(user_tz)
                    else:
                        user_tz = pytz.timezone(company_id.timezone)
                        create_utc = pytz.utc.localize(create_time_utc)
                        write_utc = pytz.utc.localize(write_time_utc)

                        create_time_local = create_utc.astimezone(user_tz)
                        write_time_local = write_utc.astimezone(user_tz)

                    write_time = datetime.strptime(write_time_local.strftime('%m/%d/%Y %H:%M:%S'), '%m/%d/%Y %H:%M:%S')
                    updated_date = datetime.strptime(kwargs['updatedDate'], '%m/%d/%Y %H:%M:%S')

                    if write_time>updated_date:
                        attachment_list = []
                        if rec.attachment_count > 0:
                            attachments = request.env['ir.attachment'].sudo().search(
                                [('res_model', '=', 'case.management'), ('res_id', '=', rec.id),
                                 ('company_id', '=', rec.company_id.id)])
                            for record in attachments:
                                url = '%s/web/image_get?model=ir.attachment&id=%s&name=%s&field=datas' % (
                                    url_with_https, record.id, record.name,
                                )
                                date_obj = datetime.strptime(str(record.create_date), "%Y-%m-%d %H:%M:%S.%f")
                                attachments = {
                                    'fileName': record.name,
                                    'fileSize': record.file_size,
                                    'uploadedBy': record.create_uid.name,
                                    'uploadedDate': date_obj.strftime("%m/%d/%Y %H:%M:%S"),
                                    "attachment": url,
                                }
                                attachment_list.append(attachments)

                        comments_list = []
                        if rec.case_description_ids:
                            for res in rec.case_description_ids:
                                date_obj = datetime.strptime(str(res.create_date), "%Y-%m-%d %H:%M:%S.%f")
                                if user_id.tz:
                                    user_tz = pytz.timezone(user_id.tz)
                                    create_utc = pytz.utc.localize(date_obj)
                                    create_time_local = create_utc.astimezone(user_tz)
                                else:
                                    user_tz = pytz.timezone(company_id.timezone)
                                    create_utc = pytz.utc.localize(date_obj)
                                    create_time_local = create_utc.astimezone(user_tz)
                                internal_comment_list = {
                                    "date": create_time_local.strftime("%m/%d/%Y %H:%M:%S"),
                                    "comments": res.description,
                                    "user": res.create_uid.name
                                }
                                comments_list.append(internal_comment_list)

                        resolution_list = []
                        if rec.case_resolution_ids:
                            for record in rec.case_resolution_ids:
                                date_obj = datetime.strptime(str(record.create_date), "%Y-%m-%d %H:%M:%S.%f")
                                if user_id.tz:
                                    user_tz = pytz.timezone(user_id.tz)
                                    create_utc = pytz.utc.localize(date_obj)
                                    create_time_local = create_utc.astimezone(user_tz)
                                else:
                                    user_tz = pytz.timezone(company_id.timezone)
                                    create_utc = pytz.utc.localize(date_obj)
                                    create_time_local = create_utc.astimezone(user_tz)

                                resolution_comment_list = {
                                    "date": create_time_local.strftime("%m/%d/%Y %H:%M:%S"),
                                    "comments": record.resolution,
                                    "user": record.create_uid.name
                                }
                                resolution_list.append(resolution_comment_list)

                        employee_list = []
                        for res in rec.employee_ids:
                            tech_details = {
                                "techId": res.id,
                                "techPersons": f"""{res.first_name if res.first_name else ''} {res.last_name if res.last_name else ''}""",
                            }
                            employee_list.append(tech_details)

                        if rec.partner_address:
                            acc_name = rec.partner_id.kam.first_name if rec.partner_id.kam.first_name else ''
                            acc_name += ' '
                            acc_name += rec.partner_id.kam.last_name if rec.partner_id.kam.last_name else ''
                            cases = {
                                "createdDateTime": create_time_local.strftime('%m/%d/%Y %H:%M:%S'),
                                "updateDateTime": write_time_local.strftime('%m/%d/%Y %H:%M:%S'),
                                "caseId": rec.id,
                                "caseNo": rec.number,
                                "open": rec.open_from,
                                "customerId": rec.partner_id.id,
                                "customer": rec.partner_id.name if rec.partner_id.name else '',
                                "customerAddress": rec.partner_address.replace('\n', ' ') if rec.partner_address.replace('\n',
                                                                                                                         ' ') else '',
                                "zip": rec.zip,
                                "street": rec.street,
                                "street2": rec.street2 if rec.street2 else '',
                                "state": rec.state_id.name,
                                "county": rec.county,
                                "city": rec.city if rec.city else '',
                                "tech": employee_list,
                                "caseType": rec.type_id.name,
                                "route": rec.route_id.name if rec.route_id else "",
                                "caseStatus": rec.stage_id.name,
                                "info": remove_html_tags(rec.case_description),
                                "internalComments": comments_list,
                                "resolutionComments": resolution_list,
                                "equipmentID": rec.machine_ids.id if rec.machine_ids.id else '',
                                "equipmentCode": rec.machine_ids.code if rec.machine_ids.code else '',
                                "assetNo": rec.machine_ids.asset_no if rec.machine_ids.asset_no else '',
                                "equipmentSerialNumber": rec.machine_ids.serial_no if rec.machine_ids.serial_no else '',
                                "equipmentName": rec.machine_ids.name if rec.machine_ids.name else '',
                                "equipmentType": rec.machine_ids.machine_type_id.name if rec.machine_ids.machine_type_id.name else '',
                                "equipmentWareHouse": rec.warehouse_id.name if rec.warehouse_id.name else '',
                                "equipmentLocation": rec.location_dest_id.name if rec.location_dest_id.name else '',
                                'billable': rec.is_billable,
                                'reported_by': rec.reported_by,
                                'account_manager': acc_name,
                                'createdBy': rec.create_uid.name,
                                "attachments ": json.dumps(attachment_list) if rec.attachment_count > 0 else json.dumps([]),
                            }
                            case_list.append(cases)

            else:
                for rec in total_case_ids:
                    create_time_utc = datetime.strptime(str(rec.app_create_date), "%Y-%m-%d %H:%M:%S")
                    write_time_utc = datetime.strptime(str(rec.app_update_date), "%Y-%m-%d %H:%M:%S")
                    if user_id.tz:
                        user_tz = pytz.timezone(user_id.tz)
                        create_utc = pytz.utc.localize(create_time_utc)
                        write_utc = pytz.utc.localize(write_time_utc)

                        create_time_local = create_utc.astimezone(user_tz)
                        write_time_local = write_utc.astimezone(user_tz)
                    else:
                        user_tz = pytz.timezone(company_id.timezone)
                        create_utc = pytz.utc.localize(create_time_utc)
                        write_utc = pytz.utc.localize(write_time_utc)

                        create_time_local = create_utc.astimezone(user_tz)
                        write_time_local = write_utc.astimezone(user_tz)

                    attachment_list = []
                    if rec.attachment_count > 0:
                        attachments = request.env['ir.attachment'].sudo().search(
                            [('res_model', '=', 'case.management'), ('res_id', '=', rec.id),
                             ('company_id', '=', rec.company_id.id)])
                        for record in attachments:
                            url = '%s/web/image_get?model=ir.attachment&id=%s&name=%s&field=datas' % (
                                url_with_https, record.id, record.name,
                            )
                            date_obj = datetime.strptime(str(record.create_date), "%Y-%m-%d %H:%M:%S.%f")
                            attachments = {
                                'fileName': record.name,
                                'fileSize': record.file_size,
                                'uploadedBy': record.create_uid.name,
                                'uploadedDate': date_obj.strftime("%m/%d/%Y %H:%M:%S"),
                                "attachment": url,
                            }
                            attachment_list.append(attachments)

                    comments_list = []
                    if rec.case_description_ids:
                        for res in rec.case_description_ids:
                            date_obj = datetime.strptime(str(res.create_date), "%Y-%m-%d %H:%M:%S.%f")
                            if user_id.tz:
                                user_tz = pytz.timezone(user_id.tz)
                                create_utc = pytz.utc.localize(date_obj)
                                create_time_local = create_utc.astimezone(user_tz)
                            else:
                                user_tz = pytz.timezone(company_id.timezone)
                                create_utc = pytz.utc.localize(date_obj)
                                create_time_local = create_utc.astimezone(user_tz)
                            internal_comment_list = {
                                "date": create_time_local.strftime("%m/%d/%Y %H:%M:%S"),
                                "comments": res.description,
                                "user": res.create_uid.name
                            }
                            comments_list.append(internal_comment_list)

                    resolution_list = []
                    if rec.case_resolution_ids:
                        for record in rec.case_resolution_ids:
                            date_obj = datetime.strptime(str(record.create_date), "%Y-%m-%d %H:%M:%S.%f")
                            if user_id.tz:
                                user_tz = pytz.timezone(user_id.tz)
                                create_utc = pytz.utc.localize(date_obj)
                                create_time_local = create_utc.astimezone(user_tz)
                            else:
                                user_tz = pytz.timezone(company_id.timezone)
                                create_utc = pytz.utc.localize(date_obj)
                                create_time_local = create_utc.astimezone(user_tz)

                            resolution_comment_list = {
                                "date": create_time_local.strftime("%m/%d/%Y %H:%M:%S"),
                                "comments": record.resolution,
                                "user": record.create_uid.name
                            }
                            resolution_list.append(resolution_comment_list)

                    employee_list = []
                    for res in rec.employee_ids:
                        tech_details = {
                            "techId": res.id,
                            "techPersons": f"""{res.first_name if res.first_name else ''} {res.last_name if res.last_name else ''}""",
                        }
                        employee_list.append(tech_details)

                    if rec.partner_address:
                        acc_name = rec.partner_id.kam.first_name if rec.partner_id.kam.first_name else ''
                        acc_name += ' '
                        acc_name += rec.partner_id.kam.last_name if rec.partner_id.kam.last_name else ''
                        cases = {
                            "createdDateTime": create_time_local.strftime('%m/%d/%Y %H:%M:%S'),
                            "updateDateTime": write_time_local.strftime('%m/%d/%Y %H:%M:%S'),
                            "caseId": rec.id,
                            "caseNo": rec.number,
                            "open": rec.open_from,
                            "customerId": rec.partner_id.id,
                            "customer": rec.partner_id.name if rec.partner_id.name else '',
                            "customerAddress": rec.partner_address.replace('\n', ' ') if rec.partner_address.replace('\n',
                                                                                                                     ' ') else '',
                            "zip": rec.zip,
                            "street": rec.street,
                            "street2": rec.street2 if rec.street2 else '',
                            "state": rec.state_id.name,
                            "county": rec.county,
                            "city": rec.city if rec.city else '',
                            "tech": employee_list,
                            "caseType": rec.type_id.name,
                            "route": rec.route_id.name if rec.route_id else "",
                            "caseStatus": rec.stage_id.name,
                            "info": remove_html_tags(rec.case_description),
                            "internalComments": comments_list,
                            "resolutionComments": resolution_list,
                            "equipmentID": rec.machine_ids.id if rec.machine_ids.id else '',
                            "equipmentCode": rec.machine_ids.code if rec.machine_ids.code else '',
                            "assetNo": rec.machine_ids.asset_no if rec.machine_ids.asset_no else '',
                            "equipmentSerialNumber": rec.machine_ids.serial_no if rec.machine_ids.serial_no else '',
                            "equipmentName": rec.machine_ids.name if rec.machine_ids.name else '',
                            "equipmentType": rec.machine_ids.machine_type_id.name if rec.machine_ids.machine_type_id.name else '',
                            "equipmentWareHouse": rec.warehouse_id.name if rec.warehouse_id.name else '',
                            "equipmentLocation": rec.location_dest_id.name if rec.location_dest_id.name else '',
                            'billable': rec.is_billable,
                            'reported_by': rec.reported_by,
                            'account_manager': acc_name,
                            'createdBy': rec.create_uid.name,
                            "attachments ": json.dumps(attachment_list) if rec.attachment_count > 0 else json.dumps([]),
                        }
                        case_list.append(cases)
            return Response(json.dumps({
                "status": "Success",
                "LastSyncDateTime": current_date.strftime('%m/%d/%Y %H:%M:%S'),
                "openCases": len(total_cases.filtered(lambda s: not s.stage_id.closed)),
                "closedCases": len(closed_cases),
                "totalCases": case_list
            }), headers={'content-type': 'application/json'})
        return None

