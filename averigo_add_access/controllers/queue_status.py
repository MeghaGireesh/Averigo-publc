from odoo.http import Controller, request, route, Response, fields
import json
import base64
import logging
_logger = logging.getLogger(__name__)

from datetime import datetime, timedelta


class QueueStatusChecker(Controller):
    VALID_USERNAME = "admin@averigo.com"
    VALID_PASSWORD = "Gz8$kL!m92@XpTqV"

    @route('/Averigo/RestApi/StatusCheck', type='http', auth='public', csrf=False, method=['POST'])
    def status_check(self, uuid, **kw):
        if request.httprequest.method == 'POST':
            auth_header = request.httprequest.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Basic '):
                return Response("Unauthorized: Missing or invalid Authorization header", status=401)
                # Decode and validate credentials
            encoded_credentials = auth_header.split(' ')[1]
            try:
                decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
                username, password = decoded_credentials.split(':', 1)
            except Exception as e:
                return Response("Unauthorized: Invalid credentials format", status=401)
            if username != self.VALID_USERNAME or password != self.VALID_PASSWORD:
                return Response("Unauthorized: Invalid username or password", status=401)
            else:
                _logger.info('---------------------------------------------------')
                _logger.info(fields.datetime.now())
                # query = """select id, state from queue_job where uuid = '%s' limit 1""" %uuid
                # request.env.cr.execute(query)
                # vals = request.env.cr.fetchone()
                # queue = request.env['queue.job'].sudo().browse(vals[0]) if vals else request.env['queue.job'].sudo()
                # print(queue)
                # _logger.info(fields.datetime.now())
                queue = request.env['queue.job'].sudo().search([('uuid', '=', uuid)])
                history = request.env['product.history'].sudo().search([('uuid', '=', uuid)])
                if not history:
                    history = request.env['market.history'].sudo().search([('uuid', '=', uuid)])
                _logger.info(fields.datetime.now())
                if queue:
                    if queue.state == 'done':
                        response_data = {
                            "uuid": uuid,
                            "status": "SUCCESS",
                        }
                        if history.error_code:
                            response_data["error_code"] = history.error_code
                            response_data["error_description"] = history.remarks

                        return Response(json.dumps(response_data), status=200)

                    elif queue.state == 'pending':
                        response_data = {
                            "uuid": uuid,
                            "status": "PENDING",
                        }
                        if history.error_code:
                            response_data["error_code"] = history.error_code
                            response_data["error_description"] = history.remarks

                        return Response(json.dumps(response_data), status=400)
                    elif queue.state == 'failed':
                        response_data = {
                            "uuid": uuid,
                            "status": "FAILED",
                        }
                        if history.error_code:
                            response_data["error_code"] = history.error_code
                            response_data["error_description"] = history.remarks

                        return Response(json.dumps(response_data), status=400)
                else:
                    return Response("UUID not found", status=400)
        else:
            return Response("Page not found", status=404)


