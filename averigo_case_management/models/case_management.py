import re
from odoo.tools import pytz
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import datetime
from datetime import datetime, timezone

CLEANR = re.compile("<.*?>")


def cleanhtml(raw_html):
    cleantext = re.sub(CLEANR, "", raw_html)
    return cleantext


class ScheduleTechPerson(models.Model):
    _name = "schedule.tech.person"
    _description = "Schedule Tech Person"

    # wizard_id = fields.Many2one("schedule.tech.person.wizard")
    employee_ids = fields.Many2many("hr.employee", string="Tech Person")
    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    from_time = fields.Float(string="From Time")
    to_time = fields.Float(string="To Time")
    company_id = fields.Many2one("res.company", string="Company",
                                 default=lambda self: self.env.company)
    all_day_available = fields.Boolean(string="All Day Available")
    only_saturday = fields.Boolean(string="Only Saturday Available")
    only_sunday = fields.Boolean(string="Only Sunday Available")

    old_record = fields.Boolean(string="Day ReadOnly",
                                compute='_compute_old_record')

    def _compute_old_record(self):
        for rec in self:
            rec.old_record = False
            if rec.to_date and (rec.to_date < fields.Date.today()):
                rec.old_record = True

    @api.constrains('from_time', 'to_time', 'to_date', 'from_date',
                    'company_id', 'only_sunday', 'only_saturday')
    def _check_schedule_unique(self):
        """This Function is used to check is there any record that is in the
        same range . We don't want to allow to create at the same time.
        """
        """
        STEP:1 - searching the records in b/w the Date range
        """
        schedule = self.search([
            ('id', '!=', self.id),
            '|',
            '&', ('from_date', '<=', self.from_date),
            ('to_date', '>=', self.from_date),
            '&', ('from_date', '<=', self.to_date),
            ('to_date', '>=', self.to_date)
        ])
        """
        All the records that is in the date range will be in the schedule 
        variable.
        """
        if schedule:
            """
            STEP:2 - If the schedule have value then we need to check the 
            shift range.
            """
            overlap = schedule.filtered(lambda l:
                                        ((
                                                 self.from_time >= l.from_time and self.from_time <=
                                                 l.to_time)
                                         or (
                                                 self.to_time >= l.from_time and self.to_time <=
                                                 l.to_time)) or
                                        ((
                                                 l.from_time >=
                                                 self.from_time and
                                                 l.from_time <=
                                                 self.to_time)
                                         or (
                                                 l.to_time >= self.from_time
                                                 and l.to_time <=
                                                 self.to_time))
                                        )
            if overlap:
                """ 
                STEP:3 -If value in overlap then same record is occurred in 
                the same shift. So we need to check the boolean conditions.
                """
                overlap_all_day = overlap.filtered(
                    lambda l: l.all_day_available)
                """
                If Available all day enabled then we need to just show the 
                warning.
                """
                if overlap_all_day or self.all_day_available:
                    raise UserError(
                        _("You cannot create a new schedule with this date and time as a record already exists. You can only update the existing record."))
                """
                STEP :4 - Now wee need to check the only saturday and only 
                sunday is enabled.If that is enabled and we don't want to show 
                the warning.
                """
                only_sunday = overlap.filtered(lambda l: l.only_sunday)
                only_saturday = overlap.filtered(lambda l: l.only_saturday)
                """
                STEP:5 - If Current record only sunday or only Saturday 
                enabled then we need to check the booleans
                """
                if (self.only_sunday and only_sunday) or (self.only_saturday
                                                          and only_saturday):
                    raise UserError(
                        _("You cannot create a new schedule with this date and time as a record already exists. You can only update the existing record."))
                else:
                    for item in self.employee_ids:
                        if item in overlap.mapped('employee_ids'):
                            raise UserError(
                                _("Tech person already exists in the same shift"))
                if (not only_sunday and not only_saturday and
                        not self.only_sunday \
                        and not self.only_saturday):
                    raise UserError(
                        _("You cannot create a new schedule with this date and time as a record already exists. You can only update the existing record."))
                else:
                    for item in self.employee_ids:
                        if item in overlap.mapped('employee_ids'):
                            raise UserError(
                                _("Tech person already exists in the same shift"))
            else:
                for item in self.employee_ids:
                    if item in schedule.mapped('employee_ids'):
                        raise UserError(
                            _("Tech person already exists in the same shift"))

    @api.onchange('from_date', 'to_date')
    def _onchange_date(self):
        if self.from_date and self.from_date < fields.Date.today():
            raise UserError(_("Date should be greater than today."))
        if self.to_date and self.to_date < fields.Date.today():
            raise UserError(_("Date should be greater than today."))

    @api.constrains('from_time', 'to_time')
    def check_times(self):
        """Function to check the time."""
        for rec in self:
            if rec.from_time > 23.99 or rec.to_time > 23.99:
                raise UserError(_("Time should be between 0 to 23.59"))
            if rec.to_time <= rec.from_time:
                raise UserError(_("Time To must be greater than Time From."))

    @api.onchange('all_day_available')
    def _onchnage_all_day_available(self):
        """Function to trigger the readonly of the fields."""
        if self.all_day_available:
            self.only_saturday = False
            self.only_sunday = False

    @api.onchange('only_saturday', 'only_sunday')
    def _onchange_only_saturday(self):
        if self.only_saturday or self.only_sunday:
            self.all_day_available = False


class CaseCompletion(models.Model):
    _name = "case.employee"
    _rec_name = "employee_id"

    employee_id = fields.Many2one("hr.employee", string="Tech Person")
    employee_ids = fields.Many2many(
        "hr.employee", compute="_compute_employee_ids", string="Tech " "Person"
    )

    @api.model
    def default_origin_id(self):
        self.origin_id = self.env.context.get("default_origin_id")
        return self.env.context.get("default_origin_id")

    origin_id = fields.Many2one(
        "case.management", string="origin case", default=default_origin_id
    )
    company_id = fields.Many2one(
        "res.company", "Operator", default=lambda self: self.env.company
    )
    internal_comment = fields.Text(string="Internal Comment")
    resolution_comment = fields.Text(string="Resolution Comment")

    @api.depends("origin_id")
    def _compute_employee_ids(self):
        """We added the domain based on this field.So if we log in as a tech
        person so the tech person only see their employee only in the
        selection field.And the Employee will select automatically."""
        for rec in self:
            rec.employee_ids = False
            if rec.origin_id.employee_ids and self.env.user.has_group(
                    "averigo_service_management.res_groups_service_management_data"
            ):
                rec.employee_ids = rec.origin_id.employee_ids.ids
            elif rec.origin_id.employee_ids and self.env.user.has_group(
                    "averigo_service_management.res_groups_service_management_tech_person_data"
            ):
                employee_users = rec.origin_id.employee_ids
                employe_user = (
                    self.env["hr.employee"]
                    .sudo()
                    .search([("user_id", "=", self.env.user.id)])
                    .id
                )
                if employe_user in employee_users.ids:
                    rec.employee_ids = [employe_user]
                    rec.employee_id = employe_user

    def close_case_employee(self):
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
        print("employe_name", employe_name)
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
        # difference = set(all_emp) - tech_emp
        all_exist = all(item in all_emp for item in tech_emp)

        if all_exist:
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

        # self.origin_id.employee_ids = [(3, self.employee_id.id)]

        # for employee in self.origin_id.employee_ids:
        #     for item in all_emp:
        #         if employee ==
        # for completion in set(all_emp):
        #     if completion


class CaseDescription(models.Model):
    _name = "case.description"
    _rec_name = "description"

    description = fields.Char("Case Description")
    company_id = fields.Many2one(
        "res.company", "Operator", default=lambda self: self.env.company
    )
    origin_id = fields.Many2one("case.management", "origin_case")


class CaseResolution(models.Model):
    _name = "case.resolution"
    _rec_name = "resolution"

    resolution = fields.Char("Case Resolution")
    company_id = fields.Many2one(
        "res.company", "Operator", default=lambda self: self.env.company
    )
    origin_id = fields.Many2one("case.management", "origin_case")


class CaseManagement(models.Model):
    _inherit = 'case.management'

    app_create_date = fields.Datetime(string="App Created Date",
                                      default=lambda self: datetime.now().replace(microsecond=0))

    app_update_date = fields.Datetime(string="App Updated Date",
                                      default=lambda self: datetime.now().replace(microsecond=0))

    # def test_mail_send(self):
    #     accounts_manager_email = (
    #         self.partner_id.kam.work_email)
    #     print("44444", accounts_manager_email)
    #     print("44444", self.partner_id.kam)
    #     mail_template = self.env.ref(
    #         'averigo_case_management.case_management_case_created_notification_mail')
    #     # mail_template.with_context(
    #     #     email_to=accounts_manager_email).sudo().send_mail(
    #     #     res_id=self.id,
    #     #     force_send=True)
    #     user_name = (f"{self.partner_id.kam.first_name or ''} "
    #                  f"{self.partner_id.kam.last_name or ''}")
    #     mail_template.with_context(
    #         case_mail_to=accounts_manager_email, case_description=cleanhtml(
    #             self.case_description)).sudo().send_mail(
    #         res_id=self.id,
    #         force_send=True)
    #     # mail_template = self.env.ref(
    #     'averigo_case_management.case_management_assigned_case_notification_mail')
    # email_to = str([rec.work_email or rec.user_id.partner_id.email for
    #                 rec in self.employee_ids])[1:-1]
    # print("pppppppp", email_to)
    # for rec in self.employee_ids:
    #     mail_template.with_context(
    #         case_url=f"/web#id="
    #                  f"{self.id}&amp;view_type=form&amp;model=case.management",
    #         case_mail_to=rec.work_email,
    #         case_tech_person=f"{rec.first_name or ''}"
    #                          f" {rec.last_name or ''}",
    #         case_description=cleanhtml(
    #             self.case_description)).sudo().send_mail(
    #         res_id=self.id, force_send=True)

    # self.send_user_mail()
    def cleanhtml(self, raw_html):
        cleantext = False
        if raw_html:
            cleantext = re.sub(CLEANR, "", raw_html)
            print("cleantext", cleantext)
        return cleantext

    def _get_warehouse_id(self):
        warehouse_id = self.env["stock.warehouse"].search(
            [
                ("is_parts_warehouse", "=", True),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
            order="id asc",
        )
        self.warehouse_id = warehouse_id.id
        return warehouse_id.id

    equipment_ids = fields.Many2many(
        "account.asset", compute="_compute_equipment_ids", store=True
    )

    project_id = fields.Many2one("project.project", string="Project")

    account_close_case = fields.Integer(
        string="Account close case",
    )
    request_date = fields.Datetime(
        "Request Date",
        default=fields.Datetime.now,
        help="Date requested for the maintenance to happen",
    )
    machine_ids = fields.Many2one(
        "account.asset", string="Equipment", track_visibility="onchange"
    )
    serial_number = fields.Char(
        string="Equipment Serial Number", related="machine_ids.serial_no"
    )
    asset_no = fields.Char("Asset No", related="machine_ids.asset_no")

    location_dest_id = fields.Many2one(
        "stock.location",
        string="Equipment Location",
        related="machine_ids.machine_location_id",
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Warehouse",
        ondelete="restrict",
        default=_get_warehouse_id,
    )
    partner_id = fields.Many2one("res.partner", string="Customer", store=True)
    route_id = fields.Many2one('route.route', string="Route")
    phone = fields.Char(string="Phone", related="partner_id.phone", deault=None)
    mobile = fields.Char(string="Mobile", related="partner_id.mobile")
    in_progress = fields.Boolean(string="case in progress")

    is_case_started = fields.Boolean(default=False)

    confirm_without_parts = fields.Boolean(string="Confirm without parts")
    confirm_without_return = fields.Boolean(
        string="Confirm without parts return")

    case_notes = fields.One2many("casemanagement.notes", "origin_id",
                                 String="Notes")

    subject = fields.Char(string="Subject")

    serial_no = fields.Char(string="Serial No", related="machine_ids.serial_no")
    machine_type_id = fields.Many2one(
        "account.asset.type", related="machine_ids.machine_type_id"
    )

    partner_address = fields.Char(
        string="Customer Address", compute="_compute_partner_address",
        store=True
    )

    case_description_ids = fields.One2many(
        "case.description", "origin_id", string="Case Description"
    )
    case_resolution_ids = fields.One2many(
        "case.resolution", "origin_id", string="Case Resolution"
    )

    # SmartButton count fields
    attachment_count = fields.Integer(
        string="Attachment Count", compute="_compute_attachment_count",
        store=True
    )
    internal_comment_count = fields.Integer(
        string="Internal Comment Count",
        compute="_compute_internal_comment_count",
        store=True,
    )
    case_resolution_count = fields.Integer(
        string="Internal Comment Count",
        compute="_compute_resolution_comment_count",
        store=True,
    )

    case_notes_count = fields.Integer(
        string="Case Note Count", compute="_compute_case_note_count", store=True
    )

    activities_count = fields.Integer(
        string="Case Note Count", compute="_compute_activities_count",
        store=True
    )
    cancel_reason = fields.Char("Case Cancel Reason")

    is_tech_user = fields.Boolean(
        string="Is tech user?", compute="_compute_is_tech_user"
    )

    completion_ids = fields.One2many(
        "case.employee", "origin_id", string="Employee Completion ids"
    )

    hide_close_btn = fields.Boolean(
        string="Field used to hide and show the " "close button.",
        compute="_compute_show_close_btn",
    )

    closed_by = fields.Many2one("hr.employee")
    closed_user_id = fields.Many2one("res.users")

    all_internal_comments = fields.Text(string="Internal Commments")
    all_resolution_comments = fields.Text(string="Resolution Commments")

    def conv_time_float(self, value):
        """Function to convert the time to float."""
        print("value", value)
        vals = value.split(':')
        t, hours = divmod(float(vals[0]), 24)
        t, minutes = divmod(float(vals[1]), 60)
        minutes = minutes / 60.0
        print("conv_time_float", hours + minutes)
        return hours + minutes

    @api.constrains('number')
    def _assign_schedule_technician(self):
        """Checking the tech person Schedule and assign tech person."""
        try:
            today = datetime.today()
            tz = pytz.timezone(self.env.user.tz) or pytz.utc
            user_tz_date = pytz.utc.localize(datetime.now()).astimezone(tz)
            if not self.employee_ids:
                tech_persons_records = self.env['schedule.tech.person'].sudo(
                ).search([('from_date', '<=', today),
                          ('to_date', '>=', today)])
                now = self.conv_time_float(
                    f"""{user_tz_date.hour}:{user_tz_date.minute}""")
                all_day = tech_persons_records.filtered(lambda l:
                                                        now >= l.from_time and
                                                        now <= l.to_time)
                # l.all_day_available and
                if today.weekday() not in (5, 6) or all_day.all_day_available:
                    """If All day enabled then just assing the person."""
                    print("Assign")
                    self.employee_ids = [(4, i.id) for i in
                                         all_day.employee_ids]
                    return

                saturday = tech_persons_records.filtered(lambda l:
                                                         l.only_saturday and
                                                         now >= l.from_time and
                                                         now <= l.to_time)
                if saturday and today.weekday() == 5:
                    self.employee_ids = [(4, i.id) for i in
                                         saturday.employee_ids]
                    return

                sunday = tech_persons_records.filtered(lambda l:
                                                       l.only_sunday and
                                                       now >= l.from_time and
                                                       now <= l.to_time)
                if sunday and today.weekday() == 6:
                    self.employee_ids = [(4, i.id) for i in sunday.employee_ids]
                    return
        except Exception as e:
            print("Exception in assign tech person ----->", str(e))

    @api.depends("completion_ids")
    def _compute_show_close_btn(self):
        for rec in self:
            employe_user = (
                self.env["hr.employee"]
                .sudo()
                .search([("user_id", "=", self.env.user.id)])
                .id
            )
            if rec.stage_id.closed:
                rec.hide_close_btn = True
            elif employe_user in rec.completion_ids.mapped(
                    "employee_id"
            ).ids and not self.env.user.has_group(
                "averigo_service_management.res_groups_service_management_data"
            ):
                rec.hide_close_btn = True
            else:
                rec.hide_close_btn = False

    def _compute_is_tech_user(self):
        print("_compute_is_tech_user")
        for rec in self:
            if not self.env.user.has_group(
                    "averigo_service_management.res_groups_service_management_data"
            ):
                """If this is false then the user is tech person"""
                rec.is_tech_user = True
            else:
                rec.is_tech_user = False

    # Functions to calculate the counts . All are smart buttons
    @api.depends("partner_id")
    def _compute_equipment_ids(self):
        for rec in self:
            if rec.partner_id:
                equipment_ids = (
                    self.env["account.asset"]
                    .search(
                        [
                            ("location_partner_id", "=", rec.partner_id.id),
                            ("company_id", "in", self.env.user.company_ids.ids),
                        ]
                    )
                    .ids
                )
                rec.write({"equipment_ids": [(6, 0, equipment_ids)]})
            else:
                equipment_ids = (
                    self.env["account.asset"]
                    .search(
                        [("company_id", "in", self.env.user.company_ids.ids)])
                    .ids
                )
                rec.write({"equipment_ids": [(6, 0, equipment_ids)]})

    @api.depends("activity_ids")
    def _compute_activities_count(self):
        for rec in self:
            rec.activities_count = len(rec.activity_ids)

    @api.depends("case_notes")
    def _compute_case_note_count(self):
        for rec in self:
            rec.case_notes_count = len(rec.case_notes)

    @api.depends("case_resolution_ids")
    def _compute_resolution_comment_count(self):
        for rec in self:
            rec.case_resolution_count = len(rec.case_resolution_ids)

    @api.depends("case_description_ids")
    def _compute_internal_comment_count(self):
        for rec in self:
            rec.internal_comment_count = len(rec.case_description_ids)

    @api.depends("attachment_ids")
    def _compute_attachment_count(self):
        for rec in self:
            rec.attachment_count = len(rec.attachment_ids)

    def action_open_descriptions(self):
        # Smart Button :- Smart button to show the Internal comments
        view_id = self.env.ref(
            "averigo_case_management.case_management_descriptions_form"
        ).id
        value = {
            "type": "ir.actions.act_window",
            "name": _("Internal Comments"),
            "res_model": "case.management",
            "target": "new",
            "view_id": view_id,
            "res_id": self.id,
            "view_mode": "form",
        }
        return value

    def action_open_resolution(self):
        # Smart Button :- Smart button to show the Resolution comments
        view_id = self.env.ref(
            "averigo_case_management.case_management_resolution_form"
        ).id
        value = {
            "type": "ir.actions.act_window",
            "name": _("Resolution Comments"),
            "res_model": "case.management",
            "target": "new",
            "view_id": view_id,
            "res_id": self.id,
            "view_mode": "form",
        }
        return value

    @api.depends("partner_id")
    def _compute_partner_address(self):
        """Function to calculate the customer address in Case Home page."""
        for rec in self:
            rec.partner_address = False
            if rec.partner_id:
                rec.partner_address = rec.partner_id._display_address(
                    without_company=True
                )

    @api.model
    def create(self, vals):
        # Custom validation before create
        if 'reported_phone' in vals and vals.get('reported_phone') != False:
            match = re.match(
                "^\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})$",
                vals['reported_phone'])
            if match is None:
                raise ValidationError(_("Please provide a valid phone number."))
        return super(CaseManagement, self).create(vals)

    def write(self, vals):
        # Custom validation before write
        if 'reported_phone' in vals:
            match = re.match(
                "^\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})$",
                vals['reported_phone'])
            if match is None:
                raise ValidationError(_("Please provide a valid phone number."))
        return super(CaseManagement, self).write(vals)

    @api.constrains("reported_phone")
    def validation_reported_phone(self):
        """
        Function for checking phone number valid or not as per the US format
        """
        if self.reported_phone:
            new = len(self.reported_phone)
            match = re.match(
                "^\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})$",
                self.reported_phone)
            if match is None:
                raise ValidationError(_("Please provide a valid phone number."))
            # if not new == 10 or new == 12:
            #     raise ValidationError(_("Please provide a valid phone number."))

    @api.constrains("portal_subject")
    def _check_subject(self):
        if self.subject and not self.subject_id:
            self.subject_id = (
                self.env["case.subject"]
                .sudo()
                .create(
                    {"name": self.subject, "company_id": self.env.company.id})
                .id
            )
        elif self.subject and self.subject_id:
            self.subject_id.name = self.subject

    @api.constrains("employee_ids")
    def _check_employee_ids(self):
        """Function is used to track the Assign to (Tech-persons).Field value
        change.Odoo default tracking is not working correctly."""
        self.message_post(
            body=_("Assigned To : %s")
                 % (
                     self.employee_ids.mapped(
                         lambda l: "%s %s" % (
                             l.first_name or "", l.last_name or "")
                     )
                 )
        )
        if self.employee_ids:
            self.start_case()

    @api.onchange("machine_ids")
    def check_customer_adn_fill(self):
        if self.machine_ids.route_id:
            "Fetching the rote from equipment."
            self.route_id = self.machine_ids.route_id

        if not self.partner_id and self.machine_ids:
            self.partner_id = self.machine_ids.location_partner_id
            if not self.machine_ids.location_partner_id:
                raise UserError(_("No Account Related to this machine"))
            if self.machine_ids.warehouse_id:
                self.warehouse_id = self.machine_ids.warehouse_id
            self._onchange_partner_id()
        elif self.machine_ids.location_partner_id:
            # TODO : NEED TO FIX
            if self.machine_ids.warehouse_id:
                self.warehouse_id = self.machine_ids.warehouse_id
            self.partner_id = self.machine_ids.location_partner_id
            self._onchange_partner_id()
            # raise UserError(_("You selected a different customer from machine"))
        elif self.machine_ids and not self.machine_ids.location_partner_id:
            if self.machine_ids.warehouse_id:
                self.warehouse_id = self.machine_ids.warehouse_id
            raise UserError(_("No Account Related to this machine"))

    @api.constrains("stage_id")
    def _check_stage_id(self):
        """This function will check the stage of the case and changing the
        values of some boolean and creating invoice and pickings """
        # if self.stage_id and self.stage_id.name == 'In Progress' and self.in_progress == False:
        #     self.start_case()
        if self.stage_id and self.stage_id.name == 'Closed':
            self.closed = True
            self.created_picking = True
            self.created_invoice = True
            self.is_case_started = True
            if self.is_billable or len(self.parts_line_ids):
                self.created_invoice = False
            elif self.parts_line_ids:
                self.created_picking = False
            self.create_invoice()

    @api.model
    def get_case_close_view(self):
        return self.env.ref(
            "averigo_case_management.case_management_completion_form"
        ).id

    def close_case_btn(self):
        """Smart Button :-This function is used to close the case"""
        view_id = self.env.ref(
            "averigo_case_management.case_management_completion_form"
        ).id
        # res_id = self.env['case.employee'].sudo().create(
        #     {'origin_id': self.id})
        value = {
            "type": "ir.actions.act_window",
            "name": _("Close Case"),
            "res_model": "case.employee",
            "target": "new",
            "view_id": view_id,
            # 'res_id': res_id.id,
            "context": {"default_origin_id": self.id},
            "view_mode": "form",
        }
        return value

    def start_case(self):
        # Function is used to start the case
        state = self.env['case.management.stage'].search(
            [('name', '=', 'In Progress'), ('company_id',
                                            '=', self.env.company.id)])
        self.write({'stage_id': state.id, 'in_progress': True,
                    'is_case_started': True})

    def confirm_case_close(self):
        # This function will ensure the case is closable or not.
        if (
                self.confirm_without_parts and self.confirm_without_return
        ) or self.hide_fields:
            state = self.env["case.management.stage"].search(
                [("name", "=", "Closed")])
            self.write(
                {
                    "stage_id": state.id,
                    "in_progress": True,
                    "closed_id": self.env.user.id,
                }
            )
            self.created_picking = True
            self.is_case_started = True
            self.created_invoice = True
            if self.is_billable or len(self.parts_line_ids):
                self.created_invoice = False
            self.create_invoice()
        return 0

    def close_case(self):
        # state = self.env['case.management.stage'].search([('name', '=', 'Closed')])
        self.write({"in_progress": True})
        self.is_case_started = True
        # print(" casesss", self.parts_line_ids.search_count([('case_id', '=', self.id)]))
        # if self.damaged_parts_line_ids:
        view_id = self.env.ref(
            "averigo_case_management.case_management_wizard").id
        if (
                self.parts_line_ids.search_count(
                    [("case_id", "=", self.id)]) == 0
                and self.damaged_parts_line_ids.search_count(
            [("damaged_parts_case_id", "=", self.id)]
        )
                == 0
        ):
            # If not selected any parts and any damaged parts thw popup will show.
            self.hide_fields = False
            value = {
                "type": "ir.actions.act_window",
                "name": _("No Parts Used "),
                "res_model": "case.management",
                "target": "new",
                "view_id": view_id,
                "res_id": self.id,
                "view_mode": "form",
            }
        else:
            # state = self.env['case.management.stage'].search([('name', '=', 'Closed')])
            # self.write({'stage_id': state.id, 'in_progress': True})
            self.hide_fields = True
            value = {
                "type": "ir.actions.act_window",
                "name": _("No Parts Used "),
                "res_model": "case.management",
                "target": "new",
                "view_id": view_id,
                "res_id": self.id,
                "view_mode": "form",
            }
        return value

    def cancel_case(self):
        # TODO:- Need to Add the Warning and cancel reason.
        return {
            "type": "ir.actions.act_window",
            "name": _("Cancel Case"),
            "res_model": "case.management",
            "target": "new",
            "view_id": self.env.ref(
                "averigo_case_management.case_management_cancel_comment_form"
            ).id,
            "res_id": self.id,
            "view_mode": "form",
        }

    def confirm_cancel_case(self):
        state = self.env["case.management.stage"].search(
            [("name", "=", "Cancelled")])
        self.write({"stage_id": state.id, "cancelled_case": True})
        self.message_post(
            body=_("<b>Cancel Reason</b><br/>%s" % (self.cancel_reason)))

    def action_get_attachment_view(self):
        # Smart Button :- This function is used to get the attachment. This
        # function will be used by the js.
        view_id = self.env.ref(
            "averigo_case_management.case_management_attachment_form"
        ).id
        # self.ensure_one()
        res = self.env["ir.actions.act_window"].for_xml_id("base",
                                                           "action_attachment")
        res["domain"] = [
            ("res_model", "=", "case.management"),
            ("res_id", "in", self.ids),
        ]
        res["context"] = {
            "default_res_model": "case.management",
            "default_res_id": self.id,
        }
        res["view_id"] = [(view_id, "form")]
        res["target"] = "current"
        res["view_type"] = "kanban"
        return res

    def open_activities(self):
        """Smart Button :- Activitys display function."""
        context = {"default_activity_ids": self.activity_ids.ids}
        view_id = self.env.ref(
            "averigo_case_management.activity_wizard_case_view").id
        return {
            "name": _("Activities"),
            "view_mode": "form",
            "res_model": "case.management",
            "view_id": view_id,
            "type": "ir.actions.act_window",
            "context": context,
            "target": "new",
        }

    def open_notes(self):
        """Smart Button :- Notes display function."""
        view_id = self.env.ref(
            "averigo_case_management.note_wizard_case_view").id
        context = {"default_origin_id": self.id}
        return {
            "name": _("Notes"),
            "view_mode": "form",
            "res_model": "case.management",
            "view_id": view_id,
            "res_id": self.id,
            "type": "ir.actions.act_window",
            "context": context,
            "target": "new",
        }

    def send_user_mail(self, addition):
        """Function to send the mail to Each employee(tech person)."""
        mail_template = self.env.ref(
            "averigo_case_management.case_management_assigned_case_notification_mail"
        )
        if addition:
            employees = self.env["hr.employee"].browse(list(addition))
        else:
            employees = self.employee_ids
        for rec in employees:
            mail_template.with_context(
                case_url=f"/web#id="
                         f"{self.id}&amp;view_type=form&amp;model=case.management",
                case_mail_to=rec.work_email,
                case_tech_person=f"{rec.first_name or ''}" f" {rec.last_name or ''}",
                case_description=cleanhtml(self.case_description),
            ).sudo().send_mail(res_id=self.id, force_send=True)

    @api.constrains("partner_id")
    def _send_partner_id_mail(self):
        """Function to send the mail to the partners Accounts manager."""
        accounts_manager_email = self.partner_id.kam.work_email
        if self.partner_id and self.partner_id.send_case_mail:
            mail_template = self.env.ref(
                "averigo_case_management"
                ".case_management_case_created_notification_mail"
            )
            mail_template.with_context(
                case_mail_to=accounts_manager_email,
                case_description=cleanhtml(self.case_description),
            ).sudo().send_mail(res_id=self.id, force_send=True)


class CaseMangementNotes(models.Model):
    _name = "casemanagement.notes"
    _order = "created_on desc"

    message = fields.Char("Message")
    company_id = fields.Many2one(
        "res.company", "Operator", default=lambda self: self.env.company
    )
    created_on = fields.Datetime("Created Date", default=fields.Datetime.now())
    origin_id = fields.Many2one("case.management", "origin_case")

#
# Case = env['case.management'].browse(7048)
# # Revert case stage
# in_progress_stage = env['case.management.stage'].search([
#     ('name', '=', 'In Progress'),
#     ('company_id', '=', Case.company_id.id),
# ], limit=1)
#
# # Reset fields
# Case.write({
#     'stage_id': in_progress_stage.id,
#     'closed': False,
#     'closed_date': False,
#     'closed_by': False,
#     'closed_user_id': False,
#     'all_internal_comments': ' ',
#     'all_resolution_comments': ' '
# })
#
#
# # Delete related case.employee records
# env['case.employee'].search([('origin_id', '=', 7048)]).unlink()
#
# # Optionally delete related case.description and case.resolution
# env['case.description'].search([('origin_id', '=', 7048)]).unlink()
# env['case.resolution'].search([('origin_id', '=', 7048)]).unlink()
#
