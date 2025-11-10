# -----------------MASTER SYNC API---------------------------------
from odoo import http
import json
from odoo.http import request, Response


class CaseCategory(http.Controller):

    @http.route('/Averigo/RestApi/case_category_type_status', type='http', method=['POST'],
                auth='public', csrf=False)
    def case_details(self, **kwargs):
        """Passing master Sync data to App"""
        kwargs['OperatorDomain'] = kwargs['OperatorDomain'].lower()
        company_id = request.env['res.company'].sudo().search(
            [('operator_domain', '=', kwargs['OperatorDomain'])])
        if company_id:
            case_category = request.env['case.management.category'].sudo().search([('company_id', '=', company_id.id)])
            case_stage = request.env['case.management.stage'].sudo().search([('company_id', '=', company_id.id)])
            case_type = request.env['case.management.type'].sudo().search([('company_id', '=', company_id.id)])
            employees = request.env['hr.employee'].sudo().search([('company_id', '=', company_id.id)])
            mail_activity_type = request.env['mail.activity.type'].sudo().search([('company_id', '=', company_id.id)])
            category_list = []
            for rec in case_category:
                category = {
                    "categoryName": rec.name,
                    "categoryId": rec.id
                }
                category_list.append(category)
            status = []
            for res in case_stage:
                stages = {
                    "stageId": res.id,
                    "stageName": res.name,
                    "closed": res.closed
                }
                status.append(stages)
            case_types = []
            for record in case_type:
                types = {
                    "typeId": record.id,
                    "typeName": record.name,
                }
                case_types.append(types)
            employee_list = []
            for res in employees:
                case_management_ids = request.env['case.management'].sudo().search(
                    [('company_id', '=', company_id.id), ('employee_ids', '=', res.name), ('closed', '=', False)])
                case_management_count = len(case_management_ids)
                employee = {
                    "techId": res.id,
                    "techName": f"""{res.first_name} {res.last_name}""",
                    "assignedCases": case_management_count
                }
                employee_list.append(employee)
            mail_activity_type_list = []
            for res in mail_activity_type:
                activities = {
                    "id": res.id,
                    "name": res.name
                }
                mail_activity_type_list.append(activities)

            return Response(json.dumps({
                "status": "Success",
                "caseCategory": category_list,
                "caseStatus": status,
                "caseTypes": case_types,
                "caseTechPersons": employee_list,
                "mailActivities": mail_activity_type_list
            }), headers={'content-type': 'application/json'})
        else:
            return Response(json.dumps({
                "status": "Operator does not exist"
            }), headers={'content-type': 'application/json'})


class Customer(http.Controller):
    @http.route('/Averigo/RestApi/customer', type='http', method=['POST'],
                auth='public', csrf=False)
    def equipment_customer(self, **kwargs):
        """Passing all customer details to the app"""
        kwargs['OperatorDomain'] = kwargs['OperatorDomain'].lower()
        company_id = request.env['res.company'].sudo().search(
            [('operator_domain', '=', kwargs['OperatorDomain'])])
        if company_id:
            customers = request.env['res.partner'].sudo().search([('operator_id', '=', company_id.id),('is_customer','=',True)])
            if customers:
                customer_list = []
                for rec in customers:
                    customer = {
                        "customerId": rec.id,
                        "customerName": rec.name if rec.name else "",
                        "customerStreet": rec.street if rec.street else "",
                        "customerCity": rec.city if rec.city else "",
                        "customerZIP": rec.zip if rec.zip else "",
                        "customerCountry": rec.country_id.name if rec.country_id else "",
                    }
                    customer_list.append(customer)
                return Response(json.dumps({
                    "status": "Success",
                    "customers": customer_list
                }), headers={'content-type': 'application/json'})
            return Response(json.dumps({
                "status": "Error",
                "message": "Customer does not exist"
            }), headers={'content-type': 'application/json'})
        return Response(json.dumps({
            "status": "Error",
            "message": "Operator does not exist"
        }), headers={'content-type': 'application/json'})
