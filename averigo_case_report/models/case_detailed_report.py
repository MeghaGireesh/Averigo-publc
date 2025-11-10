import io
import json
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import date_utils
import re

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter
CLEANR = re.compile('<.*?>')


def cleanhtml(raw_html):
    cleantext = ""
    if raw_html:
        cleantext = re.sub(CLEANR, '', raw_html)
    return cleantext


class CasesReport(models.TransientModel):
    _name = 'case.report'
    _description = 'Case Management Report'
    _rec_name = ''

    name = fields.Char(string='Name', default='Case Detailed Report')
    is_reported = fields.Boolean(string="Reported From", default=True)
    reported_from = fields.Date(string='Reported From Date')
    reported_to = fields.Date(string='Reported To Date',
                              default=fields.Date.today())
    is_closed = fields.Boolean(string="Closed")
    close_from = fields.Date(string='Case Close From Date')
    close_to = fields.Date(string='Case Close To Date',
                           default=fields.Date.today())
    subject_id = fields.Many2one('case.subject', string='Subject')
    account_id = fields.Many2one('res.partner', string='Account Name')
    stage_ids = fields.Many2many('case.management.stage',
                                 'case_management_stage_report',
                                 string='Case Status')
    assigned_ids = fields.Many2many('hr.employee',
                                    'hr_employee_assigned_report',
                                    string='Assigned To')
    report_order = fields.Selection(
        [('report_date', 'Report Date'), ('closed_date', 'Closed Date')],
        default='report_date')
    sort_by = fields.Selection(
        [('ascending', 'Ascending'), ('descending', 'Descending')],
        string='Sort By',
        default='descending')

    # line_ids = fields.One2many('case.report.line', 'report_id', string='Report Lines')
    any_stage = fields.Boolean(string='Any Stage')
    line_ids = fields.Many2many('case.management', string='Report Lines')

    report_length = fields.Integer(string="Report Length")

    @api.onchange('any_stage', 'stage_ids', 'account_id',
                  'close_to', 'close_from', 'is_closed', 'reported_to',
                  'reported_from', 'is_reported')
    def filters_changed(self):
        """Function will run when any field value change occurs."""
        if any((self.any_stage, self.stage_ids, self.account_id, self.close_to,
                self.close_from, self.is_closed, self.reported_to,
                self.reported_from, self.is_reported)):
            self.show_warning = True
            if (self.close_to and self.close_from) and (
                    self.close_to < self.close_from):
                raise UserError(_("TO DATE must be grater than FROM DATE."))
            if (self.reported_to and self.reported_from) and (
                    self.reported_to < self.reported_from):
                raise UserError(_("TO DATE must be grater than FROM DATE."))
        self.line_ids = [(5, 0, 0)]
        self.report_length = 0

    @api.onchange('reported_from', 'reported_to')
    def onchange_reported_from(self):
        if self.reported_from and self.reported_to:
            if self.reported_from > self.reported_to:
                raise UserError(
                    _('Reported From Date should be less than Reported To Date'))

    @api.onchange('close_from', 'close_to')
    def onchange_close_from(self):
        if self.reported_from and self.reported_to:
            if self.reported_from > self.reported_to:
                raise UserError(
                    _('Reported From Date should be less than Reported To Date'))

    @api.onchange('is_reported')
    def _onchage_is_reported(self):
        if self.is_reported:
            self.is_closed = False
        # if self.is_closed:
        #     self.is_reported = False

    @api.onchange('is_closed')
    def _onchage_is_closed(self):
        if self.is_closed:
            self.is_reported = False

    # def generate_report_data(self):

    def action_generate_report(self):
        first_condition = False
        stage_join = False
        employe_join = False
        query = """select cm.id from case_management as cm"""
        join = """ """
        where_query = f"""where cm.company_id ={self.env.company.id}"""
        first_condition = True
        if self.any_stage and self.stage_ids:
            # if first_condition:
            #     query += " and "
            # else:
            #     first_condition = True
            stage_join = True
            join += """ inner join case_stages_stage_rel as cssr on cssr.case_management_id = cm.id """
        if self.assigned_ids:
            # if first_condition:
            #     where_query += " and "
            # else:
            #     first_condition = True
            first_join = True
            employe_join = True
            join += """ inner join all_employee_case_rael as ecr on cm.id = ecr.case_id """
        if stage_join:
            if first_condition:
                where_query += " and "
            else:
                first_condition = True
                where_query += " where "
            satges_tuple = tuple(self.stage_ids.ids)
            satges = ""
            if len(tuple(self.stage_ids.ids)) == 1:
                satges += str(satges_tuple).replace(",", "")
            else:
                satges = tuple(self.stage_ids.ids)
            #     TODO : CHECK
            where_query += """cssr.case_management_stage_id in %s""" % str(
                satges)
        if employe_join:
            print("employee ---", self.assigned_ids.ids)
            if first_condition:
                where_query += " and "
            else:
                first_condition = True
                where_query += " where "
            assigned_persons_tuple = tuple(self.assigned_ids.ids)
            if len(assigned_persons_tuple) == 1:
                assigned_persons = str(assigned_persons_tuple).replace(",", "")
            else:
                assigned_persons = tuple(self.assigned_ids.ids)
            where_query += """ecr.emp_id in %s""" % str(assigned_persons)
        if self.is_reported and self.reported_from and self.reported_to:
            if first_condition:
                where_query += " and "
            else:
                first_condition = True
                where_query += " where "
            where_query += """ cm.create_date >= '%s' and cm.create_date <= '%s'""" % (
                str(self.reported_from) + " 00:00:00",
                str(self.reported_to) + " 12:59:59")
        if self.is_closed:
            close_fr = "1=1"
            close_to = "1=1"
            closed_state = "cm.closed = True"
            if first_condition:
                where_query += " and "
            else:
                first_condition = True
                where_query += " where "

            if self.close_from:
                close_fr = f"""cm.closed_date >= '{str(self.close_from)}""" + " 00:00:00'"
            if self.close_to:
                close_to = f"""cm.closed_date <=  '{str(self.close_to)}""" + " 12:59:59'"
            where_query += closed_state+" and "+close_fr +" and "+ close_to

        if self.account_id:
            if first_condition:
                where_query += " and "
            else:
                first_condition = True
                where_query += " where"
            where_query += """  cm.partner_id = %s""" % self.account_id.id
        if self.stage_ids and not self.any_stage:
            if first_condition:
                where_query += " and "
            else:
                first_condition = True
                where_query += " where "
            satges_tuple = tuple(self.stage_ids.ids)
            satges = ""
            if len(tuple(self.stage_ids.ids)) == 1:
                satges += str(satges_tuple).replace(",", "")
            else:
                satges = tuple(self.stage_ids.ids)

            where_query += """ cm.stage_id in %s""" % str(satges)
        if self.subject_id:
            if first_condition:
                where_query += " and "
            else:
                first_condition = True
                where_query += " where "
            where_query += f""" cm.subject_id = {self.subject_id.id}"""

        self.env.cr.execute(query + join + where_query)
        results = self.env.cr.dictfetchall()
        list = [x['id'] for x in results]

        self.line_ids = [(6, 0, list)]
        self.report_length = len(self.line_ids)

    def action_export_xlsx(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('There is no data to export'))
        list_line_ids = []

        for rec in self.line_ids:
            employe_names = ""
            for custom in rec.employee_visible_ids:
                employe_names += custom.name + ", "
            value = {
                'case_no': rec.number,
                'account': rec.partner_id.name,
                'equipment': rec.machine_ids.name,
                'location': rec.machine_ids.equipment_location,
                'reported_by': rec.reported_by if rec.reported_by else " ",
                'reported_date': rec.request_date if rec.request_date else " ",
                'subject': rec.subject_id.name if rec.subject_id else " ",
                'description': rec.case_description if rec.case_description else " ",
                'employee_ids': employe_names,
                'internal_comments': rec.internal_comment if rec.internal_comment else " ",
                'internal_comment_count': rec.internal_comment_count if
                rec.internal_comment_count else 0,
                'resolution_comment_count': rec.case_resolution_count if
                rec.case_resolution_count else 0,
                'resolution': rec.resolution if rec.resolution else " ",
                'case_status': rec.stage_id.name,
                'collected': rec.collected,
                'refund': rec.refunded,
                'closed_by': rec.closed_user_id.name or " ",
                'closed_date': rec.closed_date,
                'all_internal_comments':rec.all_internal_comments,
                "all_resolution_comments":rec.all_resolution_comments,
            }
            list_line_ids.append(value)
        data = {
            'model_id': self.id,
            'reported_from': self.reported_from,
            'reported_to': self.reported_to,
            'close_from': self.close_from,
            'close_to': self.close_to,
            'subject': self.subject_id.name,
            'account_id': self.account_id.name,
            'stage_id': [stage.name for stage in self.stage_ids],
            'assigned_id': [rec.name for rec in self.assigned_ids],
            'any_stage': self.any_stage,
            'line_ids': list_line_ids,
            # 'report_order': self.report_order,
            # 'sort_by': self.sort_by,
        }
        return {
            'type': 'ir_actions_xlsx_download',
            'data': {'model': 'case.report',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Case Management Report',
                     },
            'report_type': 'xlsx',
        }

    # @api.model
    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     res = super(CaseseReport, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
    #                                                     submenu=submenu)
    #     doc = etree.XML(res['arch'])
    #     if view_type == 'form':
    #         nodes = doc.xpath("//form/field[@name='line_ids']")
    #         if nodes:
    #             nodes[0].addnext(etree.Element('label', {'string': 'hellow from py'}))
    #
    #             res['arch'] = etree.tostring(doc, encoding='unicode')
    #         # nodes = doc.xpath("//form/field[@name='line_ids']/button[@name='prior_cases_report']")
    #         print("nodes", nodes)
    #     return res

    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        print("data 111", data)
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        cell_format = workbook.add_format(
            {'font_size': '12', 'bg_color': '#D3D3D3'})
        head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '20'})
        txt = workbook.add_format({'font_size': '11', 'bg_color': '#D3D3D3'})
        table_head = workbook.add_format(
            {'bold': True, 'font_size': '10', 'bg_color': '#D3D3D3'})
        table_body = workbook.add_format({'font_size': '10'})
        sheet.merge_range('B2:I3', 'Case Detailed Report', head)
        company_obj = self.env.user.company_id
        c_address_1 = (
                          company_obj.street if company_obj.street else '') + ", " + (
                          company_obj.street2 if company_obj.street2 else '')
        c_address_2 = (company_obj.city if company_obj.city else '') + ", " + (
            company_obj.state_id.code if company_obj.state_id else '') + ", " + (
                          company_obj.zip if company_obj.zip else '')
        sheet.merge_range('K2:M2', company_obj.name, txt)
        sheet.merge_range('K3:M3', c_address_1, txt)
        sheet.merge_range('K4:M4', c_address_2, txt)
        sheet.set_column('B:M', 15)
        if data['reported_from']:
            sheet.write('B6', 'Reported From : ', cell_format)
            sheet.write('C6', datetime.strptime(data['reported_from'],
                                                "%Y-%m-%d").strftime(
                "%m/%d/%Y"), txt)
        elif data['close_from']:
            sheet.write('B6', 'Closed From : ', cell_format)
            sheet.write('C6', datetime.strptime(data['close_from'],
                                                "%Y-%m-%d").strftime(
                "%m/%d/%Y"), txt)
        if data['reported_to']:
            sheet.write('D6', 'Reported To : ', cell_format)
            sheet.write('E6', datetime.strptime(data['reported_to'],
                                                "%Y-%m-%d").strftime(
                "%m/%d/%Y"), txt)
        elif data['close_to']:
            sheet.write('D6', 'Closed To : ', cell_format)
            sheet.write('E6', datetime.strptime(data['close_to'],
                                                "%Y-%m-%d").strftime(
                "%m/%d/%Y"), txt)
        if data['account_id']:
            sheet.write('F6', 'Account : ', cell_format)
            sheet.write('G6', data['account_id'], txt)
        if data['stage_id']:
            stages = ""
            for stage in data['stage_id']:
                stages += stage + ", "
            sheet.write('H6', 'Case Status :', cell_format)
            sheet.write('I6', stages, txt)
        if data['assigned_id']:
            assigend_persons = " "
            for rec in data['assigned_id']:
                assigend_persons += rec + ", "
            sheet.write('J6', 'Assigned To :', cell_format)
            sheet.write('K6', assigend_persons, txt)
        col = 10

        sheet.write('A9', "Case No", table_head)
        sheet.write('B9', "Account Name", table_head)
        sheet.write('C9', "Location", table_head)
        sheet.write('D9', "Reported By", table_head)
        sheet.write('E9', "Reported Date", table_head)
        sheet.write('F9', "Description", table_head)
        sheet.write('G9', "Tech", table_head)
        sheet.write('H9', "Internal Comments", table_head)
        sheet.write('I9', "Resolution Comments", table_head)
        sheet.write('J9', "Case Stage", table_head)
        sheet.write('K9', "Closed By", table_head)
        sheet.write('L9', "Closed Date", table_head)
        if data['line_ids']:
            for line in data['line_ids']:
                description = line['description']
                # soup = cleanhtml(line['internal_comments'], 'lxml')
                # internal_comments = soup.get_text()
                # soup = cleanhtml(line['resolution'], 'lxml')
                # resolution = soup.get_text()
                sheet.write(f'A{col}', line['case_no'],
                            table_body)
                sheet.write(f'B{col}', line['account'],
                            table_body)
                sheet.write(f'C{col}', line['location'],
                            table_body)
                sheet.write(f'D{col}', line['reported_by'],
                            table_body)
                sheet.write(f'E{col}', datetime.strptime(line[
                                                             'reported_date'],
                                                         "%Y-%m-%d %H:%M:%S").strftime(
                    "%m/%d/%Y %H:%M"), table_body)
                sheet.write(f'F{col}', description, table_body)
                sheet.write(f'G{col}', line['employee_ids'],
                            table_body)
                sheet.write(f'H{col}', cleanhtml(line[
                    'all_internal_comments']),
                            table_body)
                sheet.write(f'I{col}', cleanhtml(line[
                    'all_resolution_comments']),
                            table_body)

                sheet.write(f'J{col}', line['case_status'],
                            table_body)
                sheet.write(f'K{col}', line['closed_by'], table_body)
                sheet.write(f'L{col}',
                            datetime.strptime(line['closed_date'],
                                              "%Y-%m-%d %H:%M:%S").strftime(
                                "%m/%d/%Y %H:%M") if
                            line[
                                'closed_date'] else "", table_body)
                col += 1
        sheet.freeze_panes(9, 0)
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

    # return {
    #     'type': 'ir.actions.act_url',
    #     'url': '/web/export_case_management_report?model=case.management&id=%s&'
    #            'filename=Case_Management_Report.xlsx' % self.id,
    #     'target': 'self',
    # }

    def pdf_export(self):
        print("-- pdf_export -- ")
        if not self.line_ids:
            raise UserError(_('Please generate report first'))

        data = {
            'model_id': self.id,
            'reported_from': self.reported_from,
            'reported_to': self.reported_to,
            'close_from': self.close_from,
            'close_to': self.close_to,
            'subject': self.subject_id,
            'account_id': self.account_id.id,
            'stage_id': self.stage_ids,
            'assigned_id': self.assigned_ids.ids,
            'any_stage': self.any_stage,
            'line_ids': self.line_ids.ids,
            'report_order': self.report_order,
            'sort_by': self.sort_by,
        }
        print("dataa", data)
        return self.env.ref(
            'averigo_case_report.action_case_report').report_action(None,
                                                                    data=data)

    def reset_filter(self):
        print("reset")
        self.reported_from = False
        self.reported_to = False
        self.close_from = False
        self.close_to = False
        self.subject = False
        self.account_id = False
        self.stage_ids = False
        self.assigned_ids = False
        self.any_stage = False
        self.line_ids = [(5, 0, 0)]

# class CaseReportLine(models.TransientModel):
#     _name = 'case.report.line'
#     _description = 'Case Management Report Line'
#
#     report_id = fields.Many2one('case.report', string='Report')
#     case_id = fields.Many2one('case.management', string='Case')
#     account_id = fields.Many2one('res.partner', string='Account Name')
#     location = fields.Char(string='Location')
#     reported = fields.Char(string='Reported By')
#     reported_date = fields.Date(string='Reported Date')
#     subject = fields.Char(string='Subject')
#     description = fields.Char(string='Description')
#     employee_ids = fields.Many2many('hr.employee', string='Tech')
#     internal_comments = fields.Char(string='Internal Comments')
#     resolution = fields.Char(string='Resolution')
#     stage_id = fields.Many2one('case.stage', string='Case Status')
#     currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
#     collected = fields.Monetary(string='Collected')
#     refunded = fields.Monetary(string='Refunded')
#     closed_id = fields.Many2one('res.users', string='Closed By')
#     close_date = fields.Date(string='Closed Date')
#     # prior_case = fields.
