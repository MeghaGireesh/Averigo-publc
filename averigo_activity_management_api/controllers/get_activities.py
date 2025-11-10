import json
from datetime import date, datetime
from odoo import http
from odoo.http import request, Response


class GetActivities(http.Controller):

    @http.route('/Averigo/RestApi/get_activities', type='http', method=['POST'],
                auth='public', csrf=False)
    def get_activities(self, **kwargs):
        if request.httprequest.method == 'POST':
            """Generating an API to show all existing activities,events,notes based on logged user operator in the 
            backend to the App"""

            company_id = request.env['res.company'].sudo().search(
                [('operator_domain', '=', kwargs['OperatorDomain'].lower())])
            if company_id:
                if not company_id:
                    return Response(json.dumps({
                        "status": "Error",
                        "message": "Invalid Operator domain"
                    }), headers={'content-type': 'application/json'})

                """Taking all the Scheduled activities based on the operator and which are in open state"""

                total_activities = request.env['mail.activity'].sudo().search(
                    [('company_id', '=', company_id.id), ('date_deadline', '>=', date.today())])
                list = []
                for rec in total_activities:
                    employee_list = []
                    cust_list = []
                    activity_types = []
                    model = request.env[rec.res_model].sudo().browse(rec.res_id)
                    if rec.res_model != 'res.partner':

                        cust_list.append({"customerId": model.partner_id.id if model.partner_id else "",
                                          "customerName": model.partner_id.name if model.partner_id else "",
                                          "street1": model.partner_id.street if model.partner_id.street else '',
                                          "street2": model.partner_id.street2 if model.partner_id.street2 else '',
                                          "zip": model.partner_id.zip if model.partner_id.zip else '',
                                          "city": model.partner_id.city if model.partner_id.city else '',
                                          "state": model.partner_id.state_id.name if model.partner_id.state_id else '',
                                          "country": model.partner_id.country_id.name if model.partner_id.country_id else ''})
                        employee_list.append({
                            "assignedId": rec.user_id.id if rec.user_id else "",
                            "assignedName": rec.user_id.name if rec.user_id else ""
                        })
                        activity_types.append({
                            "activityType": rec.activity_type_id.name if rec.activity_type_id else "",
                            "typeId": rec.activity_type_id.id if rec.activity_type_id else ""
                        })

                        activities = {
                            "type": "Activity",
                            "id": rec.id,
                            "createdUserId": rec.create_uid.id,
                            "createdUserName": rec.create_uid.name,
                            "createDate": rec.create_date_app.strftime('%m/%d/%Y %H:%M:%S'),
                            "deadLine": rec.date_deadline.strftime('%m/%d/%Y'),
                            "updateDate": rec.update_date_app.strftime(
                                '%m/%d/%Y %H:%M:%S') if rec.update_date_app else '',
                            "customer": cust_list,

                            "assignedTo": employee_list,
                            "assigneeName": rec.user_id.name,
                            "status": "Not Started" if rec.date_deadline > date.today() else (
                                "Deadline Today" if rec.date_deadline == date.today() else "Overdue"),
                            "noteOrActivityOrEventType": activity_types,
                            "name": rec.res_name,
                            "summary": rec.summary if rec.summary else "",
                            "info": rec.note if rec.note else ''
                        }
                        list.append(activities)

                    else:
                        cust_list.append({"customerId": model.id,
                                          "customerName": model.name,
                                          "street1": model.street if model.street else '',
                                          "street2": model.street2 if model.street2 else '',
                                          "zip": model.zip if model.zip else '',
                                          "city": model.city if model.city else '',
                                          "state": model.state_id.name if model.state_id else '',
                                          "country": model.country_id.name if model.country_id else '',
                                          })

                        employee_list.append({
                            "assignedId": rec.user_id.id if rec.user_id else "",
                            "assignedName": rec.user_id.name if rec.user_id else ""
                        })

                        activity_types.append({
                            "activityType": rec.activity_type_id.name if rec.activity_type_id else "",
                            "typeId": rec.activity_type_id.id if rec.activity_type_id else "",
                        })

                        activities = {
                            "type": "Activity",
                            "id": rec.id,
                            "createdUserId": rec.create_uid.id,
                            "createdUserName": rec.create_uid.name,
                            "createDate": rec.create_date_app.strftime('%m/%d/%Y %H:%M:%S'),
                            "deadLine": rec.date_deadline.strftime('%m/%d/%Y'),
                            "updateDate": rec.update_date_app.strftime(
                                '%m/%d/%Y %H:%M:%S') if rec.update_date_app else '',
                            "customer": cust_list if cust_list else "",
                            "street1": model.street if model.street else '',
                            "street2": model.street2 if model.street2 else '',
                            "zip": model.zip if model.zip else '',
                            "city": model.city if model.city else '',
                            "state": model.state_id.name if model.state_id else '',
                            "country": model.country_id.name if model.country_id else '',
                            "assignedTo": employee_list,
                            "status": "Not Started" if rec.date_deadline > date.today() else (
                                "Deadline Today" if rec.date_deadline == date.today() else "Overdue"),
                            "name": rec.res_name,
                            "noteOrActivityOrEventType": activity_types,
                            "summary": rec.summary if rec.summary else "",
                            "info": rec.note if rec.note else ''
                        }
                        list.append(activities)

                """Taking all the Calendar events based on the operator and which are in open state"""

                total_events = request.env['calendar.event'].sudo().search(
                    [('operator_id', '=', company_id.id), ('stop', '>=', datetime.today())])

                for res in total_events:
                    employee_list = []
                    customer_list = []
                    activity_types = []
                    for rec in res.employees:
                        employee = {
                            "assignedId": rec.id,
                            "assignedName": rec.name
                        }
                        employee_list.append(employee)
                    for rec in res.customers:
                        customer = {
                            "customerId": rec.id,
                            "customerName": rec.name,
                            "street1": rec.street if rec.street else "",
                            "street2": rec.street2 if rec.street2 else "",
                            "zip": rec.zip if rec.zip else "",
                            "city": rec.city if rec.city else "",
                            "stateId": rec.state_id.id if rec.state_id.id else "",
                            "state": rec.state_id.name if rec.state_id.name else "",
                            "country": rec.country_id.name if rec.country_id else ""
                        }
                        customer_list.append(customer)
                    for rec in res.activity_type:
                        activity_type = {
                            "activityType": rec.name if rec else "",
                            "typeId": rec.id if rec.id else ""
                        }
                        activity_types.append(activity_type)

                    events = {
                        "type": "Event",
                        "id": res.id,
                        "createdUserId": res.create_uid.id,
                        "createdUserName": res.create_uid.name,
                        "createDate": res.create_date_app.strftime('%m/%d/%Y %H:%M:%S'),
                        "startDate": res.start.strftime('%m/%d/%Y %H:%M:%S'),
                        "deadLine": res.stop.strftime('%m/%d/%Y %H:%M:%S'),
                        "updateDate": res.update_date_app.strftime('%m/%d/%Y %H:%M:%S') if res.update_date_app else '',
                        "customer": customer_list,
                        "assignedTo": employee_list,
                        "status": "Not Started" if res.start > datetime.today() else (
                            "Ongoing" if res.stop >= datetime.today() and res.start <= datetime.today() else "Close"),
                        "name": res.name,
                        "noteOrActivityOrEventType": activity_types,
                        "info": res.description if res.description else ''
                    }
                    list.append(events)

                # """Taking all the Log notes based on the operator and which are in open state"""
                #
                # total_notes = request.env['mail.message'].sudo().search([('create_uid', '=', 212)], order='id desc',
                #                                                         limit=90)
                #
                # for rec in total_notes:
                #     model = request.env[rec.model].sudo().browse(rec.res_id)
                #     partner = request.env['ir.model.fields'].sudo().search(
                #         [('model', '=', rec.model), ('relation', '=', 'res.partner'),
                #          ('field_description', '=', 'Customer')])
                #
                #     notes = {
                #         "type": "Notes",
                #         "createDate": rec.date.strftime('%m/%d/%Y %H:%M:%S'),
                #         "customerId": model[partner.name].id if model[partner.name] else "",
                #         "noteOrActivityOrEventType": rec.message_type,
                #         "info": rec.body if rec.body else ''
                #     }
                #     list.append(notes)

                return Response(json.dumps({
                    "status": "Success" if list else "Error",
                    "activityAndEvents": list
                }), headers={'content-type': 'application/json'})

            else:
                return Response(json.dumps({
                    "status": "Error",
                    "message": "Invalid Operator"
                }), headers={'content-type': 'application/json'})
