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


class BillListLines(models.TransientModel):
    _name = "bill.list.lines"
    _description = " Bill List Lines"

    vendor_id = fields.Many2one('res.partner', string="Vendor")
    vendor_code = fields.Char(string="Vendor #")
    vendor_type = fields.Char()
    po_id = fields.Char(string="PO TRN #")
    type = fields.Char()
    trans_id = fields.Many2one('account.move', string="Trans #")
    date = fields.Date(string="Date")
    ref_no = fields.Char(string="Ref. No")
    status = fields.Char(string="Status")
    amount = fields.Float(string="Amount")
    balance = fields.Float(string="Balance")
    vendor_invoice = fields.Char(string="Vendor Invoice")
    sap_vendor = fields.Char(string="SAP Vendor #")
    bill_report_id = fields.Many2one('bill.list.report')


class BillListReport(models.TransientModel):
    _name = "bill.list.report"
    _description = "Bill List Report"

    def default_from_date(self):
        """Function to gey the current month date."""
        today = datetime.today()
        year = today.year
        month = today.month

        # Get the first day of the current month
        start_of_month = datetime(year, month, 1)
        return start_of_month

    line_ids = fields.One2many('bill.list.lines', 'bill_report_id')
    name = fields.Char(default='Vendor Invoice Report')
    partner_id = fields.Many2one('res.partner', string="Vendor")
    date_from = fields.Date(string="From Date", default=default_from_date, required=True)
    date_to = fields.Date(string="To Date", default=fields.Date.today())
    type = fields.Selection([('direct_bill', 'Direct Bill'), ('purchase_order', 'Purchase Order')], string="Type")
    bill_status = fields.Selection([('open', 'Open'), ('close', 'Closed')])
    report_mode = fields.Selection([('summary', 'Summary'), ('detailed', 'Detail')], default='summary',required=True)
    report_length = fields.Integer()
    generation_date = fields.Date(default=fields.Date.today())

    @api.onchange('date_from', 'date_to')
    def date_check(self):
        if self.date_from and self.date_to:
            if (self.date_to - self.date_from).days / 31 > 3:
                raise UserError(
                    _('The difference between Start Date and End Date should not be more than 3 Months.'))
            if self.date_from > self.date_to:
                self.date_to = None
                return {
                    'warning': {
                        'title': 'Value Error',
                        'message': 'End date should be greater than start date.',
                    }
                }

    def _get_report_status(self, status):
        "Function is used to return the value that we need . From odoo standard to user friendly"
        if status in ["in_payment", "not_paid"]:
            return "Open"
        elif status == "paid":
            return "Closed"

    def _get_status_report(self, status):
        "Revers process of the above function.."
        if status == "open":
            return f"('in_payment', 'not_paid')"
        elif status == "close":
            return f"('paid')"

    def action_generate_report(self):
        invoice_types = dict(self.env['account.move']._fields['invoice_types'].selection)
        query = f"""select am.partner_id as vendor_id,rp.vendor_code,rp.internal_reference as sap_vendor_no,am.invoice_origin as purchase, am.id as trans_id,
        am.date as date,am.invoice_types as invoice_types,am.vendor_invoice as vendor_invoice,am.ref as ref_no,am.invoice_payment_state as status,am.amount_total_view as total ,
        am.amount_residual as paid , (am.amount_total_view-am.amount_residual) as Balance from account_move as am  
        join res_partner as rp on rp.id = am.partner_id where am.type = 'in_invoice' and am.state = 'posted' and am.company_id = {self.env.company.id}"""

        if self.date_from:
            query += f""" and  am.date >= '{self.date_from}'"""
        if self.date_to:
            query += f""" and am.date <= '{self.date_to}'"""
        if self.partner_id:
            query += f""" and am.partner_id = {self.partner_id.id}"""
        if self.bill_status:
            query += f""" and am.invoice_payment_state in {self._get_status_report(self.bill_status)}"""
        if self.type:
            query += f""" and am.invoice_types = '{self.type}'"""
        query += """ order by am.date desc"""
        cr = self.env.cr
        cr.execute(query)
        bills = cr.dictfetchall()
        self.report_length = len(bills)
        self.line_ids = [(5, 0, 0)] + [(0, 0, {
            "vendor_id": rec.get('vendor_id'),
            "vendor_code": rec.get("vendor_code"),
            "sap_vendor":rec.get("sap_vendor_no"),
            "vendor_type": invoice_types.get(rec.get("vendor_type")),
            "vendor_invoice":rec.get("vendor_invoice"),
            "po_id": rec.get('purchase'),
            "trans_id": rec.get('trans_id'),
            "type": invoice_types.get(rec.get("invoice_types")),
            "date": rec.get('date'),
            "ref_no": rec.get("ref_no"),
            "status": self._get_report_status(rec.get('status')),
            "amount": rec.get('total'),
            "balance": rec.get('paid')
        }) for rec in bills]

    @api.onchange('date_from', 'date_to', 'partner_id', 'type', 'bill_status')
    def _onchange_filters(self):
        self.line_ids = [(5, 0, 0)]
        self.report_length = False

    def pdf_export(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('There is no data to export'))
        return self.env.ref('averigo_accounting_reports.report_averigo_bill_list').report_action(self, None)

    def reset_filter(self):
        self.line_ids = [(5, 0, 0)]
        self.report_length = False
        self.partner_id = False
        self.date_from = self.default_from_date()
        self.date_to = fields.Date.today()
        self.type = False
        self.bill_status = False

    def action_export_xlsx(self):
        invoice_types = dict(self.env['account.move']._fields['invoice_types'].selection)
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('There is no data to export'))
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError('Start Date must be less than End Date')
        if self.bill_status == 'open':
            bill_status = 'Open'
        elif self.bill_status == 'close':
            bill_status = 'Close'
        else:
            bill_status = ''

        data = {
            'date_from': self.date_from,
            'date_to': self.date_to if self.date_to else False,
            'partner_id': self.partner_id.display_name,
            'type': invoice_types.get(self.type),
            'report_mode': self.report_mode,
            'generation_date':self.generation_date,
            'bill_status': bill_status,
            'line_ids': [{
                "vendor_id": i.vendor_id.sudo().display_name,
                "vendor_code": i.vendor_code,
                "vendor_type": i.vendor_type,
                "sap_vendor":i.sap_vendor,
                "vendor_invoice":i.vendor_invoice,
                "po_id": i.po_id,
                "type": i.type,
                "trans_id": i.trans_id.sudo().name,
                "date": i.date,
                "ref_no": i.ref_no,
                "status": i.status,
                "amount": i.amount,
                "balance": i.balance,
            } for i in self.line_ids]
        }
        return {
            'type': 'ir_actions_xlsx_download',
            'data': {'model': 'bill.list.report',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Bill Report',
                     },
            'report_type': 'invoice_list_xlsx',
        }

    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        table_body = workbook.add_format({'font_size': 12})
        table_body_num = workbook.add_format({'font_size': 12, 'align': 'right'})
        cell_format = workbook.add_format(
            {'font_size': 12, 'align': 'center'})
        table_head = workbook.add_format(
            {'bold': True, 'font_size': 12, 'bg_color': '#D3D3D3'})
        sum_format = workbook.add_format(
            {'bold': True, 'font_size': 12})
        sum_data_format = workbook.add_format(
            {'bold': True, 'font_size': 12, 'align': 'right'})
        head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': 22,
             'bg_color': '#D3D3D3'})
        txt = workbook.add_format({'font_size': 12, 'align': 'center'})
        sheet.merge_range('B2:K3', 'Vendor Invoice Report', head)
        company_obj = self.env.user.company_id
        c_address_1 = (
                          company_obj.street if company_obj.street else '') + ", " + (
                          company_obj.street2 if company_obj.street2 else '')
        c_address_2 = (company_obj.city if company_obj.city else '') + ", " + (
            company_obj.state_id.code if company_obj.state_id else '') + ", " + (
                          company_obj.zip if company_obj.zip else '')
        sheet.merge_range('M2:O2', company_obj.name, txt)
        sheet.merge_range('M3:O3', c_address_1, txt)
        sheet.merge_range('M4:O4', c_address_2, txt)
        sheet.set_column('B:M', 20)
        # sheet.merge_range('A6:B6', 'From Date:', cell_format)
        # if data['partner_id']:
        sheet.write('B5', "Vendor :", cell_format)
        sheet.write('C5', data['partner_id'] or "", cell_format)
        # if data['bill_status']:
        sheet.write('E5', 'Bill Status :', cell_format)
        sheet.write('F5', data['bill_status'] or "", cell_format)
        # if data['date_from']:
        sheet.write('H5', 'Start Date :', cell_format)
        sheet.write('I5', convert_date_format(data['date_from']), cell_format)
        # if data['type']:
        sheet.write('B7', "Report Type :", cell_format)
        sheet.write('C7', 'Summary' if data['report_mode'] == 'summary' else 'Detail', cell_format)
        sheet.write('E7', 'Report Generation Date :', cell_format)
        sheet.write('F7',convert_date_format( data['generation_date']) or "", cell_format)
        if data['date_to']:
            sheet.write('H7', 'End Date :', cell_format)
            sheet.write('I7', convert_date_format(data['date_to']), cell_format)

        col = 10
        # sheet.set_column(0, 0, 40)
        # sheet.set_column(1, 0, 40)
        a= 'B'
        sheet.write(f'{a}9', "SAP Vendor#", table_head)
        a = chr(ord(a) + 1)
        sheet.write(f'{a}9', "Vendor ", table_head)
        a = chr(ord(a) + 1)
        if data['report_mode'] == 'detailed':
            sheet.write(f'{a}9', "Vendor Code", table_head)
            a = chr(ord(a) + 1)
        sheet.write(f'{a}9', "Invoice Date", table_head)
        a = chr(ord(a) + 1)
        sheet.write(f'{a}9', "Vendor Invoice #", table_head)
        a = chr(ord(a) + 1)
        if data['report_mode'] == 'detailed':
            sheet.write(f'{a}9', "PO.TRN #", table_head)
            a = chr(ord(a) + 1)
        if data['report_mode'] == 'detailed':
            sheet.write(f'{a}9', "Trans #", table_head)
            a = chr(ord(a) + 1)
        if data['report_mode'] == 'detailed':
            sheet.write(f'{a}9', "Ref. No", table_head)
            a = chr(ord(a) + 1)
        if data['report_mode'] == 'detailed':
            sheet.write(f'{a}9', "Status", table_head)
            a = chr(ord(a) + 1)
        sheet.write(f'{a}9', "Invoice Total", table_head)
        a = chr(ord(a) + 1)
        if data['report_mode'] == 'detailed':
            sheet.write(f'{a}9', "Balance", table_head)
            a = chr(ord(a) + 1)
        if data['line_ids']:
            sum_invoice_total = 0
            sum_balance = 0
            for line in data['line_ids']:
                sum_invoice_total += line['amount']
                sum_balance += line['balance']
                a = 'B'
                sheet.write(f'{a}{col}', line['sap_vendor'] or "",
                            table_body)
                a = chr(ord(a) + 1)
                sheet.write(f'{a}{col}', line['vendor_id'] or "",
                            table_body)
                a = chr(ord(a) + 1)
                if data['report_mode'] == 'detailed':
                    sheet.write(f'{a}{col}', line['vendor_code'] or "",
                                table_body)
                    a = chr(ord(a) + 1)
                sheet.write(f'{a}{col}',convert_date_format(line['date']) or "",
                            table_body)
                a = chr(ord(a) + 1)
                sheet.write(f'{a}{col}', line['vendor_invoice'] or "",
                            table_body)
                a = chr(ord(a) + 1)
                if data['report_mode'] == 'detailed':
                    sheet.write(f'{a}{col}', line['po_id'] or "",
                                table_body)
                    a = chr(ord(a) + 1)
                if data['report_mode'] == 'detailed':
                    sheet.write(f'{a}{col}', line['trans_id'] or "",
                                table_body)
                    a = chr(ord(a) + 1)
                if data['report_mode'] == 'detailed':
                    sheet.write(f'{a}{col}', line['ref_no'] or "",
                                table_body)
                    a = chr(ord(a) + 1)
                if data['report_mode'] == 'detailed':
                    sheet.write(f'{a}{col}', line['status'] or "",
                                table_body)
                    a = chr(ord(a) + 1)
                sheet.write(f'{a}{col}', ('%.2f' % line['amount']) or "",
                            table_body_num)
                a = chr(ord(a) + 1)
                if data['report_mode'] == 'detailed':
                    sheet.write(f'{a}{col}', ('%.2f' % line['balance']) or "",
                                table_body_num)
                col += 1
            sheet.write(f'B{col}', "Total", sum_format)
            if data['report_mode'] != 'detailed':
                sheet.write(f'F{col}', sum_invoice_total, sum_data_format)
            else:
                sheet.write(f'K{col}', sum_invoice_total, sum_data_format)
                sheet.write(f'L{col}', sum_balance, sum_data_format)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
