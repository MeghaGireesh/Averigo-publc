from odoo.http import Controller, request, route
from threading import Lock
import json
from odoo.http import content_disposition, request, serialize_exception as _serialize_exception
from odoo import http
from odoo.tools import html_escape


class InvoiceTypeUpdate(Controller):

    @route('/update_invoice_type', type='json', auth="public")
    def update_invoice_type(self):
        """
            {
                "company_ids":[87],
                "date": "2024-01-01",
                "type":"in_invoice"
            }
        """
        self._lock = Lock()
        items = request.jsonrequest['company_ids']
        date = request.jsonrequest['date']
        type = request.jsonrequest['type']
        operators = request.env['res.company'].sudo().with_context(active_test=False).search([('id', 'in', items)])
        for operator in operators:
            self._run_script(operator, date, type)
        return "Sucess"

    def _run_script(self, operator, date, type):
        self._lock.acquire()
        invoices = request.env['account.move'].sudo().search(
            [('company_id', '=', operator.id), ('date', '>', date), ('type', '=', type)])
        for item in invoices:
            item._check_invoice_type()
        self._lock.release()

    @http.route('/xlsx_reports', type='http', auth='user', methods=['POST'], csrf=False)
    def get_xlsx_report(self, model, options, output_format, token, report_name, **kw):
        uid = request.session.uid
        report_obj = request.env[model].with_user(uid)
        options = json.loads(options)
        type = options.get('report_type')
        try:
            if output_format == 'xlsx':
                response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', content_disposition(report_name + '.xlsx'))
                    ]
                )
                if type and type == 'xlsx_invoice_reports':
                    report_obj.get_invoice_xlsx_report(options, response)
                else:
                    report_obj.get_xlsx_report(options, response)
            response.set_cookie('fileToken', token)
            return response
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': 'Odoo Server Error',
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))
