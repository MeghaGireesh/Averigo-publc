from datetime import date
from odoo import models, fields
from odoo.tools import datetime


class SyncActivityEvent(models.Model):
    """Adding sync Activity & Event Api json body to the backend"""
    _name = 'sync.activity.events'
    _description = 'store sync activity & events'

    json_data = fields.Text('Json Input')
    date = fields.Date(string="Date", default=date.today())


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    create_date_app = fields.Datetime(string="Created Date from App", default=datetime.today())
    update_date_app = fields.Datetime(string="Updated Date from App", default=datetime.today())


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    create_date_app = fields.Datetime(string="Created Date from App", default=datetime.today())
    update_date_app = fields.Datetime(string="Updated Date from App", default=datetime.today())
