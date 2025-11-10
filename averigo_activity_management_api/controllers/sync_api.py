from datetime import datetime
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class SyncApi(http.Controller):
    @http.route('/Averigo/RestApi/sync_api', type='json', method=['POST'],
                auth='public', csrf=False)
    def sync_api(self, **kwargs):
        """From App , Activities are only creating for customers"""
        if request.httprequest.method == 'POST':
            json_body = request.env['sync.activity.events'].sudo().create({'json_data': request.jsonrequest})
            user_id = request.env['res.users'].sudo().search([('id', '=', request.jsonrequest.get('userId'))])
            if user_id and request.jsonrequest.get('addOrUpdate'):
                data = []
                for rec in request.jsonrequest.get('addOrUpdate'):
                    """--------------------CREATE NEW ACTIVITY------------------------------------"""
                    if rec.get('inputFlag') == "insert activity":
                        activity_id = request.env['mail.activity'].sudo().with_user(user_id.id).create({
                            "activity_type_id": rec.get('activityType')[0],
                            "create_date_app": datetime.strptime(rec.get('createDate'), "%m/%d/%Y %H:%M:%S"),
                            "date_deadline": datetime.strptime(rec.get('deadLine'), "%m/%d/%Y"),
                            "update_date_app": datetime.strptime(rec.get('createDate'), "%m/%d/%Y %H:%M:%S"),
                            "user_id": int(rec.get('assignedTo')[0]),
                            "res_model_id": 78,
                            "res_id": rec.get('customerId')[0],
                            "summary": rec.get('subject'),
                            "note": rec.get('description'),
                        })

                        created_activity = {
                            "activityId": activity_id.id,
                            "activityName": activity_id.res_name
                        }
                        data.append(created_activity)

                    if rec.get('inputFlag') == "activity update":
                        activity_id = request.env['mail.activity'].sudo().with_user(user_id.id).browse(
                            int(rec.get('activityId')))

                        if activity_id.update_date_app <= datetime.strptime(rec.get('updateDate'), "%m/%d/%Y %H:%M:%S"):
                            activity_id.app_update_date = datetime.strptime(rec.get('updateDate'), "%m/%d/%Y %H:%M:%S")

                            activity = rec.get('activityType')
                            assignee = rec.get('assignedTo')
                            activity_update = activity_id.sudo().with_user(user_id.id).update({
                                "activity_type_id": int(activity[0]),
                                "date_deadline": datetime.strptime(rec.get('deadLine'), "%m/%d/%Y"),
                                "update_date_app": datetime.strptime(rec.get('updateDate'), "%m/%d/%Y %H:%M:%S"),
                                "user_id": int(assignee[0]),
                                "summary": rec.get('subject'),
                                "note": rec.get('description'),
                            })

                            created_activity = {
                                "activityId": activity_id.id,
                                "activityName": activity_id.res_name
                            }
                            data.append(created_activity)
                        else:
                            return {
                                "status": "Error",
                                "message": "There is a problem with the server",
                                "activityEventSync": ""
                            }

                    """-----------------------------------------------EVENT-----------------------------------------"""
                    if rec.get('inputFlag') == "insert event":
                        if datetime.strptime(rec.get('startDatetime'), "%m/%d/%Y %H:%M:%S") <= datetime.strptime(
                                rec.get('stopDatetime'), "%m/%d/%Y %H:%M:%S"):
                            event_id = request.env['calendar.event'].sudo().with_user(user_id.id).create({
                                'active': True,
                                'user_id': user_id.id,
                                'name': rec.get('subject'),
                                'employees': [int(item) for item in rec.get('assignedTo')],
                                'customers': [int(item) for item in rec.get('customerId')],
                                'start': datetime.strptime(rec.get('startDatetime'), "%m/%d/%Y %H:%M:%S"),
                                'stop': datetime.strptime(rec.get('stopDatetime'), "%m/%d/%Y %H:%M:%S"),
                                'create_date_app': datetime.strptime(rec.get('createDate'), "%m/%d/%Y %H:%M:%S"),
                                'start_datetime': datetime.strptime(rec.get('startDatetime'), "%m/%d/%Y %H:%M:%S"),
                                'stop_datetime': datetime.strptime(rec.get('stopDatetime'), "%m/%d/%Y %H:%M:%S"),
                                'update_date_app': datetime.strptime(rec.get('updateDate'), "%m/%d/%Y %H:%M:%S"),
                                'activity_type': [int(item) for item in rec.get('activityType')],
                                'description': rec.get('description')
                            })
                            if rec.get('sendEmail'):
                                event_id.message_post(
                                    body=rec.get('mailContent'),
                                    subtype='mail.mt_comment'
                                )
                            created_event_id = {
                                "eventId": event_id.id,
                                "eventName": event_id.name
                            }
                            data.append(created_event_id)
                        else:
                            return {
                                "status": "Error",
                                "message": "End date and time is less than Start date and time",
                                "activityEventSync": []
                            }

                    if rec.get('inputFlag') == "event update":
                        event_id = request.env['calendar.event'].sudo().with_user(user_id.id).browse(
                            int(rec.get('eventId')))

                        if event_id.update_date_app <= datetime.strptime(rec.get('updateDate'), "%m/%d/%Y %H:%M:%S"):
                            event_id.update_date_app = datetime.strptime(rec.get('updateDate'), "%m/%d/%Y %H:%M:%S")

                            event_update = event_id.sudo().with_user(user_id.id).update({
                                'employees': [int(item) for item in rec.get('assignedTo')],
                                'customers': [int(item) for item in rec.get('customerId')],
                                'name': rec.get('subject'),
                                'stop': datetime.strptime(rec.get('stopDatetime'), "%m/%d/%Y %H:%M:%S"),
                                'update_date_app': datetime.strptime(rec.get('updateDate'), "%m/%d/%Y %H:%M:%S"),
                                'stop_datetime': datetime.strptime(rec.get('stopDatetime'), "%m/%d/%Y %H:%M:%S"),
                                'start': datetime.strptime(rec.get('startDatetime'), "%m/%d/%Y %H:%M:%S"),
                                'start_datetime': datetime.strptime(rec.get('startDatetime'), "%m/%d/%Y %H:%M:%S"),
                                'activity_type': [int(item) for item in rec.get('activityType')],
                                'description': rec.get('description')
                            })

                            """Remove data in the many2many fields (customer, activity type,employees)"""
                            if not rec.get('activityType'):
                                for res in event_id.mapped('activity_type').mapped('id'):
                                    event_id.sudo().with_user(user_id.id).write({
                                        'activity_type': [(3, res)],
                                    })

                            if not rec.get('customerId'):
                                for res in event_id.mapped('customers').mapped('id'):
                                    event_id.sudo().with_user(user_id.id).write({
                                        'customers': [(3, res)],
                                    })

                            if not rec.get('assignedTo'):
                                for res in event_id.mapped('employees').mapped('id'):
                                    event_id.sudo().with_user(user_id.id).write({
                                        'employees': [(3, res)],
                                    })

                            if rec.get('sendEmail'):
                                event_id.message_post(
                                    body=rec.get('mailContent'),
                                    subtype='mail.mt_comment'
                                )
                            created_event_id = {
                                "eventId": event_id.id,
                                "eventName": event_id.name
                            }
                            data.append(created_event_id)
                        else:
                            return {
                                "status": "Error",
                                "message": "There is a problem with the server",
                                "activityEventSync": ""
                            }
                return {
                    "status": "Success" if data else "Error",
                    "message": "Activity Event Sync Successful" if data else "There is a problem with the server",
                    "activityEventSync": data
                }
