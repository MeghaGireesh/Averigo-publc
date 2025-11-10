import base64

from odoo import http
from odoo.http import request
from odoo.tools import datetime
import pytz

import logging

_logger = logging.getLogger(__name__)

class CaseAddSync(http.Controller):

    @http.route('/Averigo/RestApi/case_sync2', type='json', method=['POST'],
                auth='public', csrf=False)
    def case_sync2(self):
        """Create/Update case through this api from app"""
        json_body = request.env['case.sync.api'].sudo().create({'json_data': request.jsonrequest})
        user_id = request.env['res.users'].sudo().search([('id', '=', request.jsonrequest.get('userId'))])
        _logger.warning(f"CASE MANAGEMENT--------- request body{request.jsonrequest}")


        if user_id and request.jsonrequest.get('addOrUpdate'):
            data = []
            for rec in request.jsonrequest.get('addOrUpdate'):
                """--------------------CREATE NEW CASE------------------------------------"""
                if rec.get('inputFlag') == "insert":
                    if user_id.tz:
                        user_tz = pytz.timezone(user_id.tz)
                        tz_utc = pytz.utc
                        datetime_user = user_tz.localize(datetime.strptime(rec.get('createdDateTime'), "%m/%d/%Y %H:%M:%S"))
                        datetime_utc = datetime_user.astimezone(tz_utc)
                        formatted_datetime = datetime_utc.strftime("%m/%d/%Y %H:%M:%S")

                        update_datetime_user = user_tz.localize(datetime.strptime(rec.get('updateDateTime'), "%m/%d/%Y %H:%M:%S"))
                        update_datetime_utc = update_datetime_user.astimezone(tz_utc)
                        update_datetime = update_datetime_utc.strftime("%m/%d/%Y %H:%M:%S")
                    else:
                        user_tz = pytz.timezone(user_id.company_id.timezone)
                        tz_utc = pytz.utc
                        datetime_user = user_tz.localize(datetime.strptime(rec.get('createdDateTime'), "%m/%d/%Y %H:%M:%S"))
                        datetime_utc = datetime_user.astimezone(tz_utc)
                        formatted_datetime = datetime_utc.strftime("%m/%d/%Y %H:%M:%S")

                        update_datetime_user = user_tz.localize(datetime.strptime(rec.get('updateDateTime'), "%m/%d/%Y %H:%M:%S"))
                        update_datetime_utc = update_datetime_user.astimezone(tz_utc)
                        update_datetime = update_datetime_utc.strftime("%m/%d/%Y %H:%M:%S")

                    context = request.env.context.copy()
                    context.update({'from_app':True})
                    new_case_id = request.env['case.management'].sudo().with_user(user_id.id).with_context(context).create({
                        'partner_id': rec.get('customerId'),
                        'machine_ids': rec.get('machineIds'),
                        'partner_address': rec.get('customerAddress'),
                        'city': rec.get('city'),
                        'category_id': rec.get('caseCategoryId'),
                        'is_billable': rec.get('billable'),
                        'type_id': rec.get('caseTypeId'),
                        'route_id': rec.get('route'),
                        'stage_id': rec.get('caseStatusId'),
                        'reported_by': rec.get('reportedBy'),
                        'company_id': user_id.company_id.id,
                        'reported_phone': rec.get('reportedPhone'),
                        'reported_email': rec.get('reportedEmail'),
                        # 'employee_ids': [item.get('id') for item in rec.get('techId')],
                        'employee_ids': [int(item) for item in rec.get('techId')],
                        'case_description': rec.get('caseDescription'),
                        'app_create_date': datetime.strptime(formatted_datetime, "%m/%d/%Y %H:%M:%S"),
                        "app_update_date":update_datetime_utc.replace(tzinfo=None)
                        # 'app':True
                    })
                    new_case_id._onchange_partner_id()
                    new_case_id._compute_allowed_user_ids()

                    created_cases = {
                        "CaseNumber": new_case_id.number,
                        "CreatedDateTime": new_case_id.app_create_date.strftime('%m/%d/%Y %H:%M:%S'),
                        "UpdateDateTime": new_case_id.app_update_date.strftime('%m/%d/%Y %H:%M:%S')
                    }
                    data.append(created_cases)

                """------------------------UPDATE NEW CASE------------------------------------"""

                if rec.get('inputFlag') == "update":
                    _logger.warning(f"--------------update-------------------")
                    case_id = request.env['case.management'].sudo().with_user(user_id.id).browse(
                        int(rec.get('caseId')))
                    if user_id.tz:
                        user_tz = pytz.timezone(user_id.tz)
                        tz_utc = pytz.utc
                        update_datetime_user = user_tz.localize(datetime.strptime(rec.get('updateDateTime'), "%m/%d/%Y %H:%M:%S"))
                        update_datetime_utc = update_datetime_user.astimezone(tz_utc)

                    else:
                        user_tz = pytz.timezone(user_id.company_id.timezone)
                        tz_utc = pytz.utc
                        update_datetime_user = user_tz.localize(datetime.strptime(rec.get('updateDateTime'), "%m/%d/%Y %H:%M:%S"))
                        update_datetime_utc = update_datetime_user.astimezone(tz_utc)

                    if not case_id.stage_id.closed and case_id.app_update_date <= update_datetime_utc.replace(tzinfo=None):
                        context = request.env.context.copy()
                        context.update({'from_app':True})
                        case_id.with_context(context).write({
                            "app_update_date":update_datetime_utc.replace(tzinfo=None),
                            'route_id': rec.get('route')
                        })

                        """Add route to the case"""
                        if rec.get('route'):
                            case_id.sudo().with_user(user_id.id).update({
                                'route_id': rec.get('route')
                            })

                        """Assign/remove tech persons to the corresponding case"""
                        _logger.warning(f"---------------------- {rec.get('techId')}")

                        case_id.employee_ids = [(6, 0, list(map(int,rec.get('techId'))))]
                        case_id._compute_allowed_user_ids()

                        """Add Activities to the corresponding Api"""
                        if rec.get('activities'):
                            record = []
                            for res in rec.get('activities'):
                                val = (0, 0, {
                                    'note': res.get('notes'),
                                    'res_model_id': request.env['ir.model'].sudo().with_user(user_id.id).search(
                                        [('model', '=', 'case.management')]).id,
                                    'res_id': case_id.id,
                                    'activity_type_id': res.get('activityTypeId'),
                                    'user_id': request.jsonrequest.get('userId')
                                })
                                record.append(val)

                            case_id.with_context(context).update({
                                'activity_ids': record
                            })

                        """If we close a case must need to add internal comment and resolution comment"""
                        if rec.get('caseStatusId'):
                            if rec.get('caseStatusId') != case_id.stage_id.id:
                                case_id.with_context(context).update({
                                    'stage_id': rec.get('caseStatusId')
                                })
                        if rec.get('internalComment') and not rec.get('resolutionComment'):
                            case_id.case_description_ids.with_context(context).create({
                                'description': rec.get('internalComment'),
                                'create_uid': request.jsonrequest.get('userId'),
                                'origin_id': case_id.id
                            })

                        if rec.get('resolutionComment'):
                            close_wizard = request.env['case.employee'].with_context(context).create({
                                'employee_id': request.env['hr.employee'].sudo().search(
                                    [('user_id', '=', request.jsonrequest.get('userId'))]).id,
                                'origin_id': case_id.id,
                                'company_id': case_id.company_id.id,
                                'internal_comment': rec.get('internalComment'),
                                'resolution_comment': rec.get('resolutionComment')
                            })
                            close_wizard.with_user(user_id.id).close_case_employee_api()

                        if rec.get('billable') == "true":
                            case_id.sudo().with_user(user_id.id).update({
                                'is_billable': True
                            })
                            if case_id.stage_id.closed:
                                invoice_id = case_id.sudo().create_invoice()
                                invoice_url = []
                                if invoice_id:
                                    pdf = \
                                        request.env.ref('account.account_invoices').sudo().render_qweb_pdf(
                                            [invoice_id.id])[
                                            0]
                                    base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                                    url_with_https = base_url.replace("http://", "https://")
                                    attachment = request.env['ir.attachment'].sudo().create({
                                        'name': invoice_id.name + ".pdf",
                                        'type': 'binary',
                                        'res_id': invoice_id.id,
                                        'res_model': 'account.move',
                                        'datas': base64.b64encode(pdf),
                                        'mimetype': 'application/x-pdf'
                                    })
                                    url = '%s/web/invoice.pdf?model=ir.attachment&id=%s&name=inv.pdf&field=datas' % (
                                        url_with_https, attachment.id
                                    )
                                    invoice_url.append(url)
                                    updated_cases = {
                                        "invoiceUrl": invoice_url,
                                        "CreatedDateTime": case_id.app_create_date.strftime('%m/%d/%Y %H:%M:%S'),
                                        "UpdateDateTime": case_id.app_update_date.strftime('%m/%d/%Y %H:%M:%S'),
                                    }
                                    data.append(updated_cases)
                            else:
                                updated_cases = {
                                    "CaseNumber": case_id.number,
                                    "CreatedDateTime": case_id.app_create_date.strftime('%m/%d/%Y %H:%M:%S'),
                                    "UpdateDateTime": case_id.app_update_date.strftime('%m/%d/%Y %H:%M:%S')
                                }
                                data.append(updated_cases)
                        else:
                            case_id.with_context(context).update({
                                'is_billable': False
                            })
                            updated_cases = {
                                "CaseNumber": case_id.number,
                                "CreatedDateTime": case_id.app_create_date.strftime('%m/%d/%Y %H:%M:%S'),
                                "UpdateDateTime": case_id.app_update_date.strftime('%m/%d/%Y %H:%M:%S')
                            }
                            data.append(updated_cases)
                    # else:
                    #     updated_cases = {
                    #         "status": "Error",
                    #         "message": "There is a problem with the server"
                    #     }
                    #     data.append(updated_cases)
            return {
                "status": "Success" if data else "Error",
                "message": "Case Sync Successful" if data else "There is a problem with the server",
                "CaseSync": data
            }
