import logging
from odoo import http
from odoo.http import request
from datetime import datetime


_logger = logging.getLogger(__name__)


class CaseAttachment(http.Controller):

    @http.route('/Averigo/RestApi/case_attachment', type='json', method=['POST'],
                auth='public', csrf=False)
    def case_attachment(self):
        """Adding attachments from the App to the backend"""
        user_id = request.env['res.users'].sudo().search([('id', '=', request.jsonrequest['userId'])])
        _logger.warning(f"User Id from App userrrrrr {request.jsonrequest['userId']}")
        if user_id:
            company_id = request.env['res.company'].sudo().search(
                [('operator_domain', '=', request.jsonrequest['operatorDomain'])])
            _logger.warning(f"Case Id from App mmmmmmmmmmmmmmm {request.jsonrequest['caseId']}")
            case_id = request.env['case.management'].sudo().with_user(user_id.id).search([('id', '=',
                                                                                           request.jsonrequest[
                                                                                                   'caseId']), (
                                                                                              'company_id', '=',
                                                                                              company_id.id)])
            if not case_id:
                return {
                    "status": "Error",
                    "message": "This case Id is does not exist"
                }
            if not case_id.stage_id.closed:
                if request.jsonrequest['attachments']:
                    attachment = []
                    base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    url_with_https = base_url.replace("http://", "https://")
                    for rec in request.jsonrequest['attachments']:
                        attachments = request.env['ir.attachment'].sudo().with_user(user_id.id).create({
                            'name': rec.get('name'),
                            'res_model': 'case.management',
                            'res_id': case_id.id,
                            'attachment_view_bool': True,
                            'datas': rec.get('attachment')
                        })
                        attachment_details = {
                            'fileName': attachments.name,
                            'fileSize': attachments.file_size,
                            'uploadedBy': attachments.create_uid.name,
                            'uploadedDate': attachments.create_date,
                            'attachment': '%s/web/image_get?model=ir.attachment&id=%s&name=%s&field=datas' % (
                                url_with_https, attachments.id, attachments.name,)
                        }
                        attachment.append(attachment_details)

                        update_date = datetime.now().replace(microsecond=0)
                        request.env.cr.execute("""
                            UPDATE case_management
                            SET app_update_date = %(update_date)s
                            WHERE company_id = %(company_id)s AND id = %(case_id)s
                        """, {
                            'update_date': update_date,
                            'company_id': company_id.id,
                            'case_id': case_id.id
                        })

                    return {
                        "status": "Success",
                        "message": "Attachments are added successfully",
                        "attachmentDetails": attachment
                    }
                else:
                    return {
                        "status": "Error",
                        "message": "Attachments are do not exist in the corresponding request body"
                    }
            else:
                return {
                    "status": "Error",
                    "message": "This case is already closed"
                }
        else:
            return {
                "status": "Error",
                "message": "Invalid User"
            }
