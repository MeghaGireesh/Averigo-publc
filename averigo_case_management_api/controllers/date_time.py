from odoo import http
from odoo.http import request


class DateTime(http.Controller):

    @http.route('/Averigo/RestApi/date_time_updation', type='json', method=['POST'],
                auth='public', csrf=False)
    def date_time_updation(self):
        """Script for removing date time microseconds in app_update_date and app_create_date.
        From the Averigo field App they are only sending date time with m/d/Y H:M:S format,does not sending microseconds.
        But in odoo default it taking microseconds too. Therefore now we are restricted the microsecond """

        case_records = request.env['case.management'].sudo().search([])
        print(case_records,len(case_records),"-ohbnjkoas")
        for rec in case_records:
            if rec.app_update_date.microsecond != 0:
                rec.app_update_date = rec.app_update_date.replace(microsecond=0)
            if rec.app_create_date.microsecond != 0:
                rec.app_create_date = rec.app_create_date.replace(microsecond=0)

