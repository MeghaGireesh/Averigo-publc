from odoo import models


class CaseManagement(models.Model):
    _inherit = 'case.management'

    def open_history_case(self):
        view_id = self.env.ref('averigo_case_report.chatter_view_case_report').id
        return {'type': 'ir.actions.act_window',
                'name': 'Case History',
                'res_model': 'case.management',
                'target': 'current',
                'views': [
                    (self.env.ref('averigo_case_report.chatter_view_case_report').id,
                     'form')],
                'res_id': self.id,
                'view_mode': 'form',
                }

    def get_view_id(self):
        values = {
            "list_view_id": self.env.ref(
                "averigo_service_management.case_management_tree").id,
        }
        print("value", values)
        return values

    # @api.model
    def get_case_internal_notes(self, *args, **kwargs):
        return [{'description': item.description,
                 'created': item.create_uid.name, 'date':
                     item.create_date.strftime("%m/%d/%Y %H:%M")} for
                item
                in self.case_description_ids]

    def get_case_resolution_notes(self, *args, **kwargs):
        return [{'description': item.resolution,
                 'created': item.create_uid.name, 'date':
                item.create_date.strftime("%m/%d/%Y %H:%M")} for
                item
                in self.case_resolution_ids]
