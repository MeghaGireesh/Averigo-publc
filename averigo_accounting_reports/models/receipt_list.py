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


class ReceiptList(models.TransientModel):
    _name = 'receipt.list'
    _description = "Receipt List"

    def default_from_date(self):
        """Function to gey the current month date."""
        today = datetime.today()
        year = today.year
        month = today.month

        # Get the first day of the current month
        start_of_month = datetime(year, month, 1)
        return start_of_month

    def _get_payment_mode_id(self):
        payment_mode_id = self.env['account.payment.mode'].search(
            [('type', '=', 'check')], limit=1)
        return payment_mode_id

    name = fields.Char(string='Name', default='Receipt List Report')
    partner_id = fields.Many2one('res.partner')
    start_date = fields.Date(string="From Date", default=default_from_date)
    end_date = fields.Date(string="From Date", default=fields.Date.today())
    account_ids = fields.Many2many('account.account', 'report_account_ids_receipt_list', compute='_compute_account_ids')
    account_id = fields.Many2one('account.account', string='Account')
    payment_mode_id = fields.Many2one('account.payment.mode',
                                      string="Mode of Payment")
    report_length = fields.Integer()
    line_ids = fields.Many2many('receipt.list.lines')

    @api.onchange('start_date', 'end_date')
    def check_date(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise UserError(
                _('Reported From Date should be less than Reported To Date'))
        # if self.start_date and self.end_date:
        #     if (self.end_date - self.start_date).days / 31 > 3:
        #         self.end_date = False
        #         return {
        #             'warning': {
        #                 'title': 'Date Out Of Range',
        #                 'message': 'The difference between Start Date and End '
        #                            'Date should not be more than 3 Months.',
        #             }
        #         }
        #     if self.start_date > self.end_date:
        #         self.end_date = False
        #         return {
        #             'warning': {
        #                 'title': 'Date Out Of Range',
        #                 'message': 'End Date should be after the Start Date.',
        #             }
        #         }


    @api.depends('start_date', 'end_date', 'account_id', 'partner_id', 'payment_mode_id')
    def _compute_account_ids(self):
        print("compute_account_dom_ids")
        for rec in self:
            print("rec")
            bank_and_cash_account_id = self.env.ref(
                'account.data_account_type_liquidity')
            print("bank_and_cash_account_id", bank_and_cash_account_id)
            if rec:
                account_ids = self.env['account.account'].search(
                    [('user_type_id', '=', bank_and_cash_account_id.id)])
                rec.account_ids = [(6, 0, account_ids.ids)]
            else:
                account_ids = self.env['account.account'].search(
                    [('user_type_id', '=', bank_and_cash_account_id.id)])
                rec.account_ids = [(6, 0, account_ids.ids)]

    @api.onchange('start_date', 'end_date', 'account_id', 'partner_id', 'payment_mode_id')
    def _onchange_filters(self):
        self.line_ids = [(5, 0, 0)]
        self.report_length = False

    def pdf_export(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('There is no data to export'))
        return self.env.ref('averigo_accounting_reports.report_averigo_receipt_list').report_action(self, None)

    def action_export_xlsx(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('There is no data to export'))
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError('Start Date must be less than End Date')
        data = {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'customer': self.partner_id.display_name,
            'account_id': self.account_id.name,
            'payment_mode_id': self.payment_mode_id.name,
            'line_ids': [{
                "partner_id": i.partner_id.display_name,
                "receipt_id": i.receipt_id.name,
                "receipt_date": i.receipt_date,
                "mode_of_payment": i.mode_of_payment.name,
                "account_id": i.account_id.name,
                "check_no": i.check_no,
                "amount": i.amount,
                "code": i.code
            } for i in self.line_ids]
        }
        return {
            'type': 'ir_actions_xlsx_download',
            'data': {'model': 'receipt.list',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Receipt List Report',
                     },
            'report_type': 'invoice_list_xlsx',
        }

    def action_generate_report(self):
        self.check_date()
        query = f"""select ir.partner_id as partner_id,ir.id as receipt_id,ir.receipt_date as receipt_date, rp.code as code,
        ir.payment_mode_id as mode_of_payment,ir.check_no as check_no,ir.card_number as card_number,ir.reference_no 
        as reference_no,ir.account_id,ir.amount from invoice_receipt as ir join res_partner rp ON rp.id=ir.partner_id where ir.company_id = {self.env.company.id}"""
        if self.start_date:
            query += f""" and  ir.receipt_date >= '{self.start_date}'"""
        if self.end_date:
            query += f""" and ir.receipt_date <= '{self.end_date}'"""
        if self.partner_id:
            query += f""" and ir.partner_id = {self.partner_id.id}"""
        if self.account_id:
            query += f""" and ir.account_id = {self.account_id.id}"""
        if self.payment_mode_id:
            query += f""" and ir.payment_mode_id = {self.payment_mode_id.id}"""
        query += """ order by ir.receipt_date asc"""
        cr = self.env.cr
        print("-----------------------> Query <--------------------")
        print(query)
        cr.execute(query)
        receipts = cr.dictfetchall()
        self.report_length = len(receipts)
        self.line_ids = [(5, 0, 0)] + [(0, 0, {
            "partner_id": rec.get('partner_id'),
            "receipt_id": rec.get('receipt_id'),
            "receipt_date": rec.get('receipt_date'),
            "mode_of_payment": rec.get('mode_of_payment'),
            "check_no": rec.get('check_no') or rec.get('card_number') or rec.get('reference_no') if self.env[
                                                                                                        'account.payment.mode'].browse(
                rec.get(
                    'mode_of_payment')).type not in ('cash', 'write_off', 'advance') else "",
            "account_id": rec.get('account_id'),
            "amount": rec.get('amount'),
            "code": rec.get('code')

        }) for rec in receipts]

    def reset_filter(self):
        self.line_ids = [(5, 0, 0)]
        self.report_length = False
        self.start_date = False
        self.end_date = False
        self.partner_id = False
        self.start_date = self.default_from_date()
        self.end_date = fields.Date.today()


    def get_xlsx_report(self, data, response):
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
        sheet.merge_range('A1:I3', 'Receipt List Report', head)
        company_obj = self.env.user.company_id
        c_address_1 = (
                          company_obj.street if company_obj.street else '') + ", " + (
                          company_obj.street2 if company_obj.street2 else '')
        c_address_2 = (company_obj.city if company_obj.city else '') + ", " + (
            company_obj.state_id.code if company_obj.state_id else '') + ", " + (
                          company_obj.zip if company_obj.zip else '')
        sheet.merge_range('J2:L2', company_obj.name, txt)
        total_value_format = workbook.add_format(
            {'bold': True, 'font_size': 12, 'num_format': '#,##0.00'})

        sheet.merge_range('J3:L3', c_address_1, txt)
        sheet.merge_range('J4:L4', c_address_2, txt)
        sheet.set_column('B:M', 20)
        # sheet.merge_range('A6:B6', 'From Date:', cell_format)
        if data['customer']:
            sheet.write('B5', "Customer :", cell_format)
            sheet.write('C5', data['customer'] or "", cell_format)
        if data['payment_mode_id']:
            sheet.write('E5', 'Mode of Payment :', cell_format)
            sheet.write('F5', data['payment_mode_id'] or "", cell_format)
        if data['start_date']:
            sheet.write('H5', 'Start Date :', cell_format)
            sheet.write('I5', convert_date_format(data['start_date']), cell_format)
        if data['account_id']:
            sheet.write('B7', "Account :", cell_format)
            sheet.write('C7', data['account_id'] or "", cell_format)
        if data['end_date']:
            sheet.write('H7', 'End Date :', cell_format)
            sheet.write('I7', convert_date_format(data['end_date']), cell_format)

        col = 10
        # sheet.set_column(0, 0, 40)
        # sheet.set_column(1, 0, 40)
        sheet.write('A9', "Customer #", table_head)
        sheet.write('B9', "Customer", table_head)
        sheet.write('C9', "Account", table_head)
        sheet.write('D9', "Receipt", table_head)
        sheet.write('E9', "Date", table_head)
        sheet.write('F9', "Mode of Payment", table_head)
        sheet.write('G9', "Check / Reference No", table_head)
        sheet.write('H9', "Amount", table_head)
        total_amount = sum(line['amount'] for line in data['line_ids'])
        if data['line_ids']:
            for line in data['line_ids']:
                sheet.write(f'A{col}', line['code'],
                            table_body)
                sheet.write(f'B{col}', line['partner_id'],
                            table_body)
                sheet.write(f'C{col}', line['account_id'] or "",
                            table_body)
                sheet.write(f'D{col}', line['receipt_id'],
                            table_body)
                sheet.write(f'E{col}', convert_date_format(line['receipt_date']),
                            table_body)
                sheet.write(f'F{col}', line['mode_of_payment'] or "",
                            table_body)
                sheet.write(f'G{col}', line['check_no'] or "",
                            table_body)
                sheet.write(f'H{col}', line['amount'],
                            table_body)
                col += 1
            sheet.write(col, 0,  "Total", total_value_format)
            sheet.write(col, 7, total_amount, total_value_format)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()



class ReceiptListLines(models.TransientModel):
    _name = 'receipt.list.lines'
    _description = "Receipt List Lines"

    partner_id = fields.Many2one('res.partner', string="Customer")
    receipt_id = fields.Many2one('invoice.receipt', string="Receipt")
    receipt_type = fields.Char(string="Receipt Type")
    receipt_date = fields.Date("Receipt Date")
    mode_of_payment = fields.Many2one('account.payment.mode',
                                      string="Mode of Payment")
    account_id = fields.Many2one('account.account', string='Account')
    check_no = fields.Char(string="Check No.")
    amount = fields.Float(string="Amount")
    code = fields.Char(relation='partner_id.code', string='Customer #')
