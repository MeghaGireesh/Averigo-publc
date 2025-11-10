from odoo import http
import re
import json
from odoo.http import request, Response
from odoo.tools import datetime


class CustomerHistory(http.Controller):

    @http.route('/Averigo/RestApi/customer_history', type='http', method=['POST'],
                auth='public', csrf=False)
    def customer_history(self, **kwargs):
        """This screen shows the existing case details of the concerned customer."""
        if request.httprequest.method == 'POST':

            page = int(request.params.get('page', 1))
            page_size = int(request.params.get('pageSize', 15))
            offset = (page - 1) * page_size

            kwargs['OperatorDomain'] = kwargs['OperatorDomain'].lower()
            company_id = request.env['res.company'].sudo().search(
                [('operator_domain', '=', kwargs['OperatorDomain'])])
            if not company_id:
                return Response(json.dumps({
                    "status": "Error",
                    "message": "Invalid OperatorDomain"
                }), headers={'content-type': 'application/json'})

            total_count = request.env['case.management'].sudo().search_count(
                [('company_id', '=', company_id.id), ('partner_id', '=', int(kwargs['Customer']))]
            )

            total_cases = request.env['case.management'].sudo().search(
                [('company_id', '=', company_id.id), ('partner_id', '=', int(kwargs['Customer']))], offset=offset,
                limit=page_size)

            def remove_html_tags(html_string):
                """Use a regular expression to remove HTML tags"""
                clean_text = re.sub(r'<.*?>', '', html_string)
                return clean_text

            history = []
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url_with_https = base_url.replace("http://", "https://")
            for rec in total_cases:
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
                        "techPersons": res.name
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
                        "customer": rec.partner_id.name if rec.partner_id.name else '',
                        "customerAddress": rec.partner_address.replace('\n', ' ') if rec.partner_address.replace('\n',
                                                                                                                 ' ') else '',
                        "zip": rec.zip,
                        "street": rec.street,
                        "street2": rec.street2 if rec.street2 else '',
                        "state": rec.state_id.name,
                        "county": rec.county,
                        "city": rec.city if rec.city else '',
                        "route": rec.route_id.name if rec.route_id else "",
                        "tech": employee_list,
                        "caseType": rec.type_id.name,
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
                        "attachments ": json.dumps(attachment_list) if rec.attachment_count > 0 else json.dumps([]),
                    }
                    history.append(cases)
            return Response(json.dumps({
                "status": "Success" if history else "Error",
                "message": "Customer history are successfully generated" if history else "No history available for this customer",
                "totalListCount": total_count,
                "customerCaseHistory": history
            }), headers={'content-type': 'application/json'})
        return None
