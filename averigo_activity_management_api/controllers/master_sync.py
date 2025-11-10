import json
from odoo import http
from odoo.http import request, Response


class master_sync(http.Controller):

    @http.route('/Averigo/RestApi/master_sync', type='http', method=['POST'],
                auth='public', csrf=False)
    def master_sync(self, **kwargs):
        """Customer details,employee details,user details and activity type details"""

        if request.httprequest.method == 'POST':

            company_id = request.env['res.company'].sudo().search(
                [('operator_domain', '=', kwargs['OperatorDomain'].lower())])
            if company_id:
                activity_type = request.env['mail.activity.type'].sudo().search(
                    [('company_id', '=', company_id.id), ('res_model_id', '!=', 472)])

                activity_type_list = []
                for rec in activity_type:
                    activity_types = {
                        "id": rec.id,
                        "name": rec.name if rec.name else "",
                        "actionToPerform": rec.category if rec.category else "",
                        "defaultUserId": rec.default_user_id.id if rec.default_user_id else None,
                        "model": rec.res_model_id.id if rec.res_model_id else None,
                        "defaultSummary": rec.summary if rec.summary else "",
                        "icon": rec.icon if rec.icon else "",
                        "decorationType": rec.decoration_type if rec.decoration_type else "",
                        "scheduledDate": rec.delay_count if rec.delay_count else None,
                        "unit": rec.delay_unit if rec.delay_unit else None,
                        "delayFrom": rec.delay_from if rec.delay_from else None,
                        "triggerNextActivity": rec.force_next if rec.force_next else "",
                        "defaultNextActivity": rec.default_next_type_id.id if rec.default_next_type_id else "",
                        "emailTemplates": [(res.id, res.name) for res in rec.mail_template_ids],
                        "defaultDescription": rec.default_description if rec.default_description else ""
                    }
                    activity_type_list.append(activity_types)

                assign_to_list = []
                assign_to = request.env['res.users'].sudo().search(
                    [('company_id', '=', company_id.id), ('user_type', '=', "operator")])
                for rec in assign_to:
                    assignees = {
                        "id": rec.id,
                        "name": rec.name
                    }
                    assign_to_list.append(assignees)

                employee_list = []
                employees = request.env['hr.employee'].sudo().search([('company_id', '=', company_id.id)])
                for rec in employees:
                    employees = {
                        "id": rec.id,
                        "name": rec.name,
                        "company": rec.company_id.id
                    }
                    employee_list.append(employees)

                customers = request.env['res.partner'].sudo().search(
                    [('operator_id', '=', company_id.id), ('is_customer', '=', True),('type','=','contact'),('parent_id','=',False)])
                customer_list = []
                for rec in customers:
                    customer = {
                        "customerId": rec.id,
                        "customerName": rec.name if rec.name else "",
                        "primaryAccountManager": rec.kam.id if rec.kam else None,
                        "primaryAccountManagerName": rec.kam.name if rec.kam else "",
                        "customerStreet": rec.street if rec.street else "",
                        "customerStreet2": rec.street2 if rec.street2 else "",
                        "customerCity": rec.city if rec.city else "",
                        "customerStateId": rec.state_id.id if rec.state_id.id else "",
                        "customerStateName": rec.state_id.name if rec.state_id.name else "",
                        "customerCounty": rec.county if rec.county else "",
                        "customerZIP": rec.zip if rec.zip else "",
                        "customerCountry": rec.country_id.name if rec.country_id else "",
                    }
                    customer_list.append(customer)
                return Response(json.dumps({
                    "status": "Success",
                    "activityTypes": activity_type_list,
                    "assignees": assign_to_list,
                    "employees": employee_list,
                    "customers": customer_list,
                }), headers={'content-type': 'application/json'})
            else:
                return Response(json.dumps({
                    "status": "Error",
                    "message": "Invalid Operator"
                }), headers={'content-type': 'application/json'})
