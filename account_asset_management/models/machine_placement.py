from odoo import models, fields


class MachinePlacementHistory(models.Model):
    _name = 'machine.placement.history'
    _description = 'Equipment Placement History'
    _order = 'date desc'

    source_location_id = fields.Many2one('stock.location', string='Source Location')
    location_id = fields.Many2one('stock.location', string='Destination Location')
    destination_location = fields.Char(string='Location Name')
    source_location = fields.Char(string='Source Location')
    machine_id = fields.Many2one('account.asset', string='Equipment')
    operator_id = fields.Many2one('res.company', string='Operator')
    in_date = fields.Datetime(string='In Service Date')
    date = fields.Datetime(string='Out Service Date')
    customer_id = fields.Many2one('res.partner', string="Customer")
    activity_type = fields.Selection(
        [('install', 'Install'), ('remove', 'Remove'), ('exchange', 'Exchange'), ('retire', 'Retire')],
        string="Activity Type", default='install')
    closed_case = fields.Integer(string="Closed Cases")
