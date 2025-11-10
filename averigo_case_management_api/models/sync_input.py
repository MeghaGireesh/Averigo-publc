import re

from odoo import models, fields, api, _
from datetime import date

CLEANR = re.compile("<.*?>")


def cleanhtml(raw_html):
    cleantext = re.sub(CLEANR, "", raw_html)
    return cleantext


class SyncCase(models.Model):
    """Adding Case Sync Api json request body to the backend"""
    _name = 'case.sync.api'
    _description = "Case sync json request body"

    json_data = fields.Text('Json Input')
    date = fields.Date(string="Date", default=date.today())


class CaseCompletionApi(models.Model):
    _inherit = 'case.employee'
    _description = "Close case"

    def close_case_employee_api(self):
        """Used to close the case."""
        self.env["case.description"].create(
            {
                "description": cleanhtml(self.internal_comment),
                "origin_id": self.origin_id.id,
            }
        )
        self.env["case.resolution"].create(
            {
                "resolution": cleanhtml(self.resolution_comment),
                "origin_id": self.origin_id.id,
            }
        )

        internal_comment = self.origin_id.all_internal_comments or ""
        resolution_comment = self.origin_id.all_resolution_comments or ""
        employe_name = False
        if self.employee_id:
            employe_name = f"""{self.employee_id.first_name or ""} {self.employee_id.last_name or ""}"""

        if not employe_name:
            employe_name = self.env.user.name

        self.origin_id.all_internal_comments = f"""{internal_comment}<b>{employe_name or ""} - {fields.Date.today().strftime('%m-%d-%Y')}</b><br/> {cleanhtml(self.internal_comment)}<br/>"""
        self.origin_id.all_resolution_comments = f"""{resolution_comment}<b>{employe_name or ""} - {fields.Date.today().strftime('%m-%d-%Y')}</b><br/> {cleanhtml(self.resolution_comment)}<br/>"""

        self.origin_id.message_post(
            body=_(
                "<strong> %s </strong> - Marked the case as Closed.<br/> "
                "<hr/><b>Internal Comment</b>"
                "<br/><p>%s<p><br/>"
                "<hr/>"
                "<b>Resolution "
                "Comment</b><br/><p>%s<p><br/>"
            )
                 % (
                     self.employee_id.name or self.env.user.name or "",
                     self.internal_comment,
                     self.resolution_comment,
                 )
        )

        # Now We are checking all the tech persons are closed their case. So
        # if this is the last person then we need to change the state of the
        # case.
        all_emp = (
            self.env["case.employee"]
            .search([("origin_id", "=", self.origin_id.id)])
            .mapped("employee_id")
            .ids
        )
        all_emp.append(self.employee_id.id)
        close_case = True

        tech_emp = set(self.origin_id.employee_ids.ids)
        all_exist = all(item in all_emp for item in tech_emp)
        user = self.env.user

        if all_exist or user.has_group('averigo_service_management.res_groups_service_management_data'):


            state = self.env["case.management.stage"].search(
                [
                    ("closed", "=", True),
                    ("company_id", "=", self.env.user.company_id.id),
                ],
                limit=1,
            )
            self.origin_id.write(
                {
                    "stage_id": state.id,
                    "closed": True,
                    "closed_date": fields.Datetime.now(),
                    "closed_by": self.employee_id.id,
                    "closed_user_id": self.env.user.id,
                }
            )
            if self.origin_id.partner_id.send_case_mail:
                accounts_manager_email = self.origin_id.partner_id.kam.work_email
                mail_template = self.env.ref(
                    "averigo_case_management.case_management_closed_case_notification_mail"
                )
                mail_template.with_context(
                    email_to=accounts_manager_email
                ).sudo().send_mail(res_id=self.origin_id.id, force_send=True)
        else:
            state = self.env["case.management.stage"].search(
                [
                    ("name", "=", "In Progress"),
                    ("company_id", "=", self.env.user.company_id.id),
                ],
                limit=1,
            )
            self.origin_id.write({"stage_id": state.id})
