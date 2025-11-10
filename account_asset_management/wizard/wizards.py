from odoo import models, fields, api, _


class AccountMove(models.TransientModel):
    _name = 'asset.journal.wizard'

    journal_ids = fields.Many2many('account.move', string='Journal')


class NoteWizard(models.TransientModel):
    _name = 'note.wizard'

    # journal_ids = fields.Many2many('account.move', string='Journal')
    message_ids = fields.Many2many('mail.activity', string='Message')


class MachinePlacementhistory(models.TransientModel):
    _name = 'machine.placement.history.wizard'

    machine_placement_ids = fields.Many2many('machine.placement.history', string='Equipment Placement History')
