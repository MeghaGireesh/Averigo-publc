from odoo import models, fields, api


class MachineNote(models.Model):
    _name = "machine.notes"
    _order = "create_date desc"

    message = fields.Char("Message")
    created_on = fields.Datetime("Created Date", default=fields.Datetime.now())
    created_by = fields.Many2one('res.users', "Author",
                                 default=lambda self: self.env.uid)
    asset_id = fields.Many2one('account.asset', string="origin_asset")
