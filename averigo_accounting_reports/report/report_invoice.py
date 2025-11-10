from odoo import models, api


class ReportIinvoiceListPreview(models.AbstractModel):
    _name = "report.averigo_accounting_reports.report_multi_invoice_preview"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(data.get("data"))
        return {
            'doc_ids': docids,
            'doc_model': 'invoice.list.report',
            'docs': docs,
            'data': data,
        }
