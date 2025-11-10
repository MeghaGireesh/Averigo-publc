import json
from odoo import http
from odoo.http import content_disposition, request
from odoo.addons.web.controllers.main import _serialize_exception
from odoo.tools import html_escape


class CaseManagementReportAccess(http.Controller):
    @http.route('/case_report_access', type='http', auth='none', method=['POST'], csrf=False)
    def case_report_access(self, **kw):
        if request.httprequest.method == 'POST':
            operators = request.env['res.company'].sudo().with_context(active_test=False).search([])
            for operator in operators:
                service_management_group = request.env['res.groups'].sudo().search(
                    [('name', '=', 'Service Management'), ('operator_id', '=', operator.id)])
                if service_management_group:
                    service_management_group.menu_access = [
                        (4, request.env.ref('averigo_case_report.averigo_menu_case_management_report_menu').id)]
                    service_management_group.model_access = [(0, 0, {
                        'name': 'Case Management Report',
                        'model_id': request.env.ref('averigo_case_report.model_case_report').id,
                        'perm_write': False,
                        'perm_create': False,
                        'perm_unlink': False
                    }), ]
            return "Success"
        else:
            return "Failed"
