from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = "account.move"

    invoice_types = fields.Selection([('direct_invoice', 'Direct Invoice'), ('pantry_invoice', 'Pantry Invoice'),
                                      ('sale_order_invoice', 'Sale Order Invoice'), ('direct_bill', 'Direct Bill'),
                                      ('purchase_order', 'Purchase Order')], string="Invoice / Bill Types")

    @api.constrains('name')
    def _check_invoice_type(self):
        """
        --- Invoice --
        1 - check the move is invoice or bill.
        2 - check the necessary boolean fields.
        3- update the invoice_type field.

        --- Bill ---

        1 - check the move is  bill.
        2 - check the necessary boolean fields.
        3- update the invoice_type field.
        """
        if self.type == 'out_invoice' and not self.invoice_types:
            if self.direct_invoice:
                self.write({'invoice_types': 'direct_invoice'})
            elif self.invoice_line_ids.mapped('sale_line_id'):
                self.write({'invoice_types': 'sale_order_invoice'})
            elif not self.invoice_line_ids.mapped('sale_line_id') and self.invoice_origin and \
                    self.invoice_origin.split("/")[0] == "PNTR":
                self.write({'invoice_types': 'pantry_invoice'})
            else:
                self.write({'invoice_types': False})
        if self.type == 'in_invoice' and not self.invoice_types:
            if self.direct_bill:
                self.write({'invoice_types': 'direct_bill'})
            elif self.invoice_line_ids.mapped('purchase_line_id'):
                self.write({'invoice_types': 'purchase_order'})
            else:
                self.write({'invoice_types': False})
