from odoo import models, fields, api


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    attachment_view_bool = fields.Char("Preview",
                                       compute='_compute_attachment_view_bool',
                                       store=True)

    @api.depends('datas')
    def _compute_attachment_view_bool(self):
        for rec in self:
            if rec.name:
                rec.attachment_view_bool = rec.name
            else:
                rec.attachment_view_bool = False
