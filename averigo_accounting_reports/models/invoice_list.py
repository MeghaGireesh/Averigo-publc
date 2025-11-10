from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError, UserError
import json
from odoo.tools import date_utils
import io

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


def convert_date_format(date_str):
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    return date_obj.strftime('%m-%d-%Y')


class InvoiceListLines(models.TransientModel):
    _name = 'invoice.list.lines'
    _description = "Invoice List Lines"

    customer_number = fields.Char("Customer #")
    partner_id = fields.Many2one('res.partner')
    partner_name = fields.Char()
    route_id = fields.Many2one('route.route')
    route_name = fields.Char()
    invoice_id = fields.Many2one('account.move')
    invoice_date = fields.Date()
    invoice_type = fields.Selection([('direct_invoice', 'Direct Invoice'), ('pantry_invoice', 'Pantry Invoice'),
                                     ('sale_order_invoice', 'Sale Order Invoice'), ('mm_invoice', 'MM Invoice')])
    status = fields.Selection([('all', 'All'), ('not_paid', 'Open'), ('paid', 'Closed')])
    amount = fields.Float()
    amount_paid = fields.Float()
    balance = fields.Float()
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Attachments', compute='_compute_attachment_ids')
    preview = fields.Boolean()

    email = fields.Boolean()
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company)
    report_id = fields.Many2one('invoice.list.report')
    sap_customer = fields.Char(strig="SAP Customer #")
    document_type = fields.Char("Document Type ", default="YT")
    generation_date = fields.Date(default=fields.Date.today)

    @api.depends('invoice_id')
    def _compute_attachment_ids(self):
        for rec in self:
            rec.attachment_ids = False

    def preview_select_all(self, elem):
        for line in self:
            line.write({'preview': elem})


class InvoiceListReport(models.TransientModel):
    _name = 'invoice.list.report'
    _description = "Invoice List Report"

    def default_from_date(self):
        """Function to gey the current month date."""
        today = datetime.today()
        year = today.year
        month = today.month

        # Get the first day of the current month
        start_of_month = datetime(year, month, 1)
        return start_of_month

    def _get_country(self):
        """ Get default country as United States"""
        # country = self.env['res.country'].search([('code', '=', 'US')]).id
        # return country
        country = self.env.ref('base.us').id
        return country

    name = fields.Char(default='Invoice List Report')
    partner_id = fields.Many2one('res.partner', string="Customer")
    date_from = fields.Date(string="From Date", default=default_from_date, required=True)
    date_to = fields.Date(string="To Date", default=fields.Date.today())
    invoice_type = fields.Selection([('direct_invoice', 'Direct Invoice'), ('pantry_invoice', 'Pantry Invoice'),
                                     ('sale_order_invoice', 'Sale Order Invoice')])
    # Removed pantry invoice option because it is on hold
    # invoice_type = fields.Selection([('direct_invoice', 'Direct Invoice'),
    #                                  ('sale_order_invoice', 'Sale Order Invoice')])
    route_id = fields.Many2one('route.route', string="Route")
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    country_id = fields.Many2one('res.country', string="Country", default=_get_country)
    state_id = fields.Many2one('res.country.state', string='State', domain="[('country_id', '=', country_id)]")
    report_length = fields.Integer()
    status = fields.Selection([('all', 'All'), ('not_paid', 'Open'), ('paid', 'Closed')], required=True, default='all')
    line_ids = fields.One2many('invoice.list.lines', 'report_id')
    enable_all_preview = fields.Boolean(default=False)

    @api.onchange('date_from', 'date_to')
    def check_date(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise UserError(
                _('Reported From Date should be less than Reported To Date'))
        if self.date_from and self.date_to:
            if (self.date_to - self.date_from).days / 31 > 3:
                self.date_to = False
                return {
                    'warning': {
                        'title': 'Date Out Of Range',
                        'message': 'The difference between Start Date and End '
                                   'Date should not be more than 3 Months.',
                    }
                }
            if self.date_from > self.date_to:
                self.date_to = False
                return {
                    'warning': {
                        'title': 'Date Out Of Range',
                        'message': 'End Date should be after the Start Date.',
                    }
                }

    def action_view_preview(self):
        # data = self.env['invoice.list.lines'].browse(self).ids
        print("data", self)
        invoice_ids = self.env['invoice.list.lines'].browse([rec.id for rec in self]).mapped("invoice_id").ids
        data = {'data': invoice_ids, 'report': {}}
        return self.env.ref('averigo_accounting_reports.action_invoices_preview').report_action(False, data)

    def pdf_export(self):
        if not self.line_ids:
            raise UserError(_('There is no data to export'))
        return self.env.ref('averigo_accounting_reports.report_averigo_invoice_export').report_action(self, None)

    def pdf_invoice_export(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('There is no data to export'))
        return self.env.ref('averigo_accounting_reports.report_averigo_invoice_list').report_action(self, None)

    @api.onchange('date_from', 'date_to', 'partner_id', 'status', 'invoice_type', 'route_id')
    def _onchange_filters(self):
        self.line_ids = [(5, 0, 0)]
        self.report_length = False

    def reset_filter(self):
        self.line_ids = [(5, 0, 0)]
        self.report_length = False
        self.date_from = False
        self.date_to = False
        self.partner_id = False
        self.status = "all"
        self.route_id = False
        self.invoice_type = False
        self.date_from = self.default_from_date()
        self.date_to = fields.Date.today()

    def action_generate_report(self):
        self.check_date()
        query = f"""select am.partner_id as partner_id,rp.internal_reference as sap_customer, am.date as invoice_date, am.route_id as route_id, am.id as invoice_id,am.invoice_payment_state as status,
am.amount_total_view as amount,am.amount_residual as balance , SUM(am.amount_total_view - am.amount_residual) as 
amount_paid,am.invoice_types as invoice_type,rp.code  as customer_number from account_move as am join res_partner as rp on rp.id =am.partner_id where am.type = 'out_invoice' and state = 'posted' and am.company_id = {self.env.company.id} """
        if self.date_from:
            query += f""" and am.date >= '{self.date_from}'"""
        if self.date_to:
            query += f""" and am.date <= '{self.date_to}'"""
        if self.partner_id:
            query += f""" and am.partner_id = '{self.partner_id.id}'"""
        if self.status != 'all':
            query += f""" and am.invoice_payment_state = '{self.status}'"""
        if self.route_id:
            query += f""" and am.route_id = '{self.route_id.id}'"""
        if self.invoice_type:
            query += f""" and am.invoice_types = '{self.invoice_type}'"""
        query += "group by am.partner_id,am.date,am.route_id, am.id,rp.id"
        cr = self.env.cr
        cr.execute(query)
        invoices = cr.dictfetchall()
        self.report_length = len(invoices)
        self.line_ids = [(5, 0, 0)] + [(0, 0, rec) for rec in invoices]

    def action_export_invoice_xlsx(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('There is no data to export'))
        # if self.date_from > self.date_to:
        #     raise ValidationError('Start Date must be less than End Date')
        data = {
            'start_date': self.date_from,
            'end_date': self.date_to,
            'customer': self.partner_id.display_name,
            'route': self.route_id.name,
            'invoice_type': self.invoice_type,
            'status': self.status,
            'line_ids': [{
                "code":i.customer_number,
                "sap_customer": i.sap_customer,
                "partner_id": i.partner_id.display_name,
                "route_id": i.route_id.name,
                "invoice_id": i.invoice_id.name,
                "invoice_type": i.invoice_type,
                "invoice_date": i.invoice_date,
                "status": i.status,
                "amount": i.amount,
                "amount_paid": i.amount_paid,
                "balance": i.balance
            } for i in self.line_ids]
        }
        return {
            'type': 'ir_actions_xlsx_download',
            'data': {'model': 'invoice.list.report',
                     'options': json.dumps({'data': data, 'report_type': 'xlsx_invoice_reports'},
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Invoice List Report',
                     },
            'report_type': 'xlsx_invoice_reports',
        }

    def action_export_xlsx(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('There is no data to export'))
        # if self.date_from > self.date_to:
        #     raise ValidationError('Start Date must be less than End Date')
        data = {
            'start_date': self.date_from,
            'end_date': self.date_to,
            'customer': self.partner_id.display_name,
            'route': self.route_id.name,
            'invoice_type': self.invoice_type,
            'status': self.status,
            "report_generation_date": fields.Date.today(),
            'line_ids': [{
                "partner_id": i.partner_id.display_name,
                "sap_customer": i.sap_customer,
                "route_id": i.route_id.name,
                "invoice_id": i.invoice_id.name,
                "invoice_type": i.invoice_type,
                "invoice_date": i.invoice_date,
                "generation_date": i.generation_date,
                "document_type": i.document_type,
                "status": i.status,
                "amount": i.amount,
                "amount_paid": i.amount_paid,
                "balance": i.balance
            } for i in self.line_ids]
        }
        return {
            'type': 'ir_actions_xlsx_download',
            'data': {'model': 'invoice.list.report',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Invoice Export',
                     },
            'report_type': 'invoice_export_xlsx',
        }

    def get_invoice_xlsx_report(self, data, response):
        output = io.BytesIO()
        data = data.get('data')
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        table_body = workbook.add_format({'font_size': 12})
        cell_format = workbook.add_format(
            {'font_size': 12, 'align': 'center'})
        table_head = workbook.add_format(
            {'bold': True, 'font_size': 12, 'bg_color': '#D3D3D3'})
        head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': 22,
             'bg_color': '#D3D3D3'})
        txt = workbook.add_format({'font_size': 12, 'align': 'center'})
        sum_format = workbook.add_format({'font_size': 12, 'bold': True})
        sum_data_format = workbook.add_format({'font_size': 12, 'bold': True, 'align': 'right'})
        sheet.merge_range('B2:J3', 'Invoice List Report', head)
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
        # sheet.merge_range('A6:B6', 'From Date:', cell_format)
        if data['customer']:
            sheet.write('B5', "Customer", cell_format)
            sheet.write('C5', data['customer'] or "", cell_format)
        if data['route']:
            sheet.write('E5', 'Route', cell_format)
            sheet.write('F5', data['route'] or "", cell_format)
        sheet.write('H5', 'Start Date', cell_format)
        sheet.write('I5', convert_date_format(data['start_date']), cell_format)
        filter_invoice_type = ""
        if data['invoice_type'] == "direct_invoice":
            filter_invoice_type = "Direct Invoice"
        elif data['invoice_type'] == "pantry_invoice":
            filter_invoice_type = "Pantry Invoice"
        elif data['invoice_type'] == "sale_order_invoice":
            filter_invoice_type = "Sale Order Invoice"
        if filter_invoice_type:
            sheet.write('B7', "Invoice Type", cell_format)
            sheet.write('C7', filter_invoice_type or "", cell_format)
        if data['status']:
            sheet.write('E7', 'Status', cell_format)
            filter_status = ""
            if data['status'] == "not_paid":
                filter_status = "Open"
            elif data['status'] == "paid":
                filter_status = "Closed"
            elif data['status'] == "all":
                filter_status = "All"
            sheet.write('F7', filter_status or "", cell_format)
        if data['end_date']:
            sheet.write('H7', 'End Date', cell_format)
            sheet.write('I7', convert_date_format(data['end_date']), cell_format)

        col = 10
        # sheet.set_column(0, 0, 40)
        # sheet.set_column(0, 0, 40)
        sheet.set_column('B:B', 75)  # Adjust the width as needed
        sheet.write('A9', "Customer #", table_head)
        sheet.write('B9', "Customer", table_head)
        sheet.write('C9', "SAP Customer#", table_head)
        sheet.write('D9', "Route", table_head)
        sheet.write('E9', "Invoice No", table_head)
        sheet.write('F9', "Invoice Date", table_head)
        sheet.write('G9', "Invoice Type", table_head)
        sheet.write('H9', "Status", table_head)
        sheet.write('I9', "Amount", table_head)
        sheet.write('J9', "Amount Paid", table_head)
        sheet.write('K9', "Balance", table_head)
        if data['line_ids']:
            sum_amt = 0
            sum_amt_paid = 0
            sum_bal = 0
            for line in data['line_ids']:
                sum_amt += line['amount']
                sum_amt_paid += line['amount_paid']
                sum_bal += line['balance']
                status = ""
                if line['status'] == "not_paid":
                    status = "Open"
                elif line['status'] == "paid":
                    status = "Closed"

                invoice_type = ""
                if line['invoice_type'] == "direct_invoice":
                    invoice_type = "Direct Invoice"
                elif line['invoice_type'] == "pantry_invoice":
                    invoice_type = "Pantry Invoice"
                elif line['invoice_type'] == "sale_order_invoice":
                    invoice_type = "Sale Order Invoice"

                sheet.write(f'A{col}', line['code'], table_body)
                sheet.write(f'B{col}', line['partner_id'], table_body)
                sheet.write(f'C{col}', line['sap_customer'] or "", table_body)
                sheet.write(f'D{col}', line['route_id'] or "", table_body)
                sheet.write(f'E{col}', line['invoice_id'], table_body)
                sheet.write(f'F{col}', convert_date_format(line['invoice_date']), table_body)
                sheet.write(f'G{col}', invoice_type or "", table_body)
                sheet.write(f'H{col}', status, table_body)
                sheet.write(f'I{col}', line['amount'], table_body)
                sheet.write(f'J{col}', line['amount_paid'], table_body)
                sheet.write(f'K{col}', line['balance'], table_body)
                col += 1
            sheet.write(f'A{col}', 'SUM', sum_format)
            sheet.write(f'I{col}', round(sum_amt, 2), sum_data_format)
            sheet.write(f'J{col}', round(sum_amt_paid, 2), sum_data_format)
            sheet.write(f'K{col}', round(sum_bal, 2), sum_data_format)
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

    def get_xlsx_report(self, data, response):
        # from_date = convert_date_format(data['start_date'])
        # to_date = convert_date_format(data['end_date'])
        print("-->", data)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        table_body = workbook.add_format({'font_size': 12})
        cell_format = workbook.add_format(
            {'font_size': 12, 'align': 'center'})
        table_head = workbook.add_format(
            {'bold': True, 'font_size': 12, 'bg_color': '#D3D3D3'})
        head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': 22,
             'bg_color': '#D3D3D3'})
        txt = workbook.add_format({'font_size': 12, 'align': 'center'})
        sheet.merge_range('B2:J3', 'Invoice Export', head)
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
        # sheet.merge_range('A6:B6', 'From Date:', cell_format)
        if data['customer']:
            sheet.write('B5', "Customer", cell_format)
            sheet.write('C5', data['customer'] or "", cell_format)
        # if data['route']:
        #     sheet.write('E5', 'Route', cell_format)
        #     sheet.write('F5', data['route'] or "", cell_format)
        sheet.write('F5', 'Start Date', cell_format)
        sheet.write('G5', convert_date_format(data['start_date']), cell_format)
        # filter_invoice_type = ""
        # if data['invoice_type'] == "direct_invoice":
        #     filter_invoice_type = "Direct Invoice"
        # elif data['invoice_type'] == "pantry_invoice":
        #     filter_invoice_type = "Pantry Invoice"
        # elif data['invoice_type'] == "sale_order_invoice":
        #     filter_invoice_type = "Sale Order Invoice"
        # if filter_invoice_type:
        sheet.write('B7', "Report Generation Date", cell_format)
        sheet.write('C7', convert_date_format(data['report_generation_date']) or "", cell_format)
        # if data['status']:
        #     sheet.write('E7', 'Status', cell_format)
        #     filter_status = ""
        #     if data['status'] == "not_paid":
        #         filter_status = "Open"
        #     elif data['status'] == "paid":
        #         filter_status = "Closed"
        #     elif data['status'] == "all":
        #         filter_status = "All"
        #     sheet.write('F7', filter_status or "", cell_format)
        if data['end_date']:
            sheet.write('F7', 'End Date', cell_format)
            sheet.write('G7', convert_date_format(data['end_date']), cell_format)

        col = 10
        # sheet.set_column(0, 0, 40)
        # sheet.set_column(0, 0, 40)
        sheet.write('B9', "SAP Customer #", table_head)
        sheet.write('C9', "Invoice Date", table_head)
        sheet.write('D9', "Invoice No", table_head)
        sheet.write('E9', "Generation Date", table_head)
        sheet.write('F9', "Document Type", table_head)
        sheet.write('G9', "Amount", table_head)
        # sheet.write('H9', "Amount", table_head)
        # sheet.write('I9', "Amount Paid", table_head)
        # sheet.write('J9', "Balance", table_head)
        if data['line_ids']:
            for line in data['line_ids']:
                # status = ""
                # if line['status'] == "not_paid":
                #     status = "Open"
                # elif line['status'] == "paid":
                #     status = "Closed"
                # invoice_type = ""
                # if line['invoice_type'] == "direct_invoice":
                #     invoice_type = "Direct Invoice"
                # elif line['invoice_type'] == "pantry_invoice":
                #     invoice_type = "Pantry Invoice"
                # elif line['invoice_type'] == "sale_order_invoice":
                #     invoice_type = "Sale Order Invoice"
                #
                sheet.write(f'B{col}', line['sap_customer'] or "",
                            table_body)
                sheet.write(f'C{col}', convert_date_format(line['invoice_date']) or "",
                            table_body)
                sheet.write(f'D{col}', line['invoice_id'],
                            table_body)
                sheet.write(f'E{col}', convert_date_format(line['generation_date']),
                            table_body)
                sheet.write(f'F{col}', line['document_type'] or "",
                            table_body)
                sheet.write(f'G{col}', line['amount'],
                            table_body)
                # sheet.write(f'H{col}', line['amount'],
                #             table_body)
                # sheet.write(f'I{col}', line['amount_paid'],
                #             table_body)
                # sheet.write(f'J{col}', line['balance'],
                #             table_body)
                col += 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
