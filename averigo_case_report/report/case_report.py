from odoo import models, api


class CaseReport(models.AbstractModel):
    _name = 'report.averigo_case_report.report_case_management'
    _description = 'Case Management Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        print("_get_report_values", data)
        report = self.env['case.report'].browse(data['model_id'])
        return {
            'doc_ids': docids,
            'doc_model': 'case.report',
            'docs': report,
            # 'data': values,
        }
