from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    open_case_count = fields.Integer(string="Count", compute='_compute_open_case_count')

    def _compute_open_case_count(self):
        for rec in self:
            rec.open_case_count = self.env['case.management'].search_count(
                [('employee_ids', 'in', rec.id), ('closed', '!=', True), ('cancelled_case', '!=', True)])


    def name_get(self):
        result = []
        for employee in self:
            name = employee.name
            if not employee.active:
                name = f"{name} (Archived)"
            result.append((employee.id, name))
        return result

