from odoo import http
import json
from odoo.http import request, Response


class CaseEquipment(http.Controller):

    @http.route('/Averigo/RestApi/case_equipment', type='http', method=['POST'],
                auth='public', csrf=False)
    def case_equipment(self, **kwargs):
        """Generating API for passing the Case equipments to the App."""
        if request.httprequest.method == 'POST':
            kwargs['OperatorDomain'] = kwargs['OperatorDomain'].lower()
            company_id = request.env['res.company'].sudo().search(
                [('operator_domain', '=', kwargs['OperatorDomain'])])
            if company_id:
                equipments = request.env['account.asset'].sudo().search([('company_id', '=', company_id.id)])
                if equipments:
                    equipments_list = []
                    if kwargs['customerId']:
                        equipments = request.env['account.asset'].sudo().search(
                            [('company_id', '=', company_id.id), ('location_partner_id.id', '=', kwargs['customerId'])])
                        equipments_list.append(equipments)

                    equipment_list = []
                    for rec in equipments:
                        total_cases = request.env['case.management'].sudo().search(
                            [('company_id', '=', company_id.id), ('machine_ids', '=', rec.id)])
                        equipment = {
                            "customerId": rec.location_partner_id.id if rec.location_partner_id else '',
                            "customerName": rec.location_partner_id.name if rec.location_partner_id else '',
                            "equipmentId": rec.id,
                            "equipmentCode": rec.code,
                            "equipmentNo": "",
                            "assetNo": rec.asset_no if rec.asset_no else "",
                            "equipmentType": rec.machine_type_id.name,
                            "area": rec.equipment_location,
                            "posNo": rec.area_or_pos if rec.area_or_pos else "",
                            "manufacturer": rec.manufacture if rec.manufacture else "",
                            "model": rec.equipment_model_no_id.name if rec.equipment_model_no_id else "",
                            "serialNo": rec.serial_no,
                            "equipmentServiceHistory": "",
                            "caseCount":len(total_cases),
                            "addOrmodifyImages": str(rec.image_1920)
                        }
                        equipment_list.append(equipment)
                    return Response(json.dumps({
                        "status": "Success",
                        "count":len(equipment_list),
                        "equipments": equipment_list
                    }), headers={'content-type': 'application/json'})
                return Response(json.dumps({
                    "status": "Error",
                    "message": "Equipments does not exist"
                }), headers={'content-type': 'application/json'})
            return Response(json.dumps({
                "status": "Error",
                "message": "Operator does not exist"
            }), headers={'content-type': 'application/json'})
        return None
