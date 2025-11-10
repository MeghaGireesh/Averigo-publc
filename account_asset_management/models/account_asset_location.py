from odoo import models, api, fields, _


class AccountAssetLocation(models.Model):
    _name = "account.asset.location"
    _description = "Equipment Location"
    _order = "name"

    name = fields.Char()
    code = fields.Char()
    warehouse = fields.Boolean()
    scrap = fields.Boolean()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, ondelete='cascade')


class AccountMachineLocation(models.Model):
    _inherit = "stock.location"

    is_machine_location = fields.Boolean()
    scrap = fields.Boolean()
