from odoo import models, fields, api, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    # advance_sequence = fields.Boolean(string='Dedicated Advance Sequence', default=False,
    #                                   help="Check this box if you don't want to share the same sequence for payments and advance made from this journal", )
    # advance_sequence_id = fields.Many2one('ir.sequence', string='Advance Entry Sequence', copy=False,
    #                                       help="This field contains the information related to the numbering of the Advance entries of this journal.")
    # advance_sequence_number_next = fields.Integer(string='Advance Next Number',
    #                                               help='The next sequence number will be used for the next credit note.',
    #                                               compute='_compute_advance_seq_number_next',
    #                                               inverse='_inverse_advance_seq_number_next')

    # do not depend on 'refund_sequence_id.date_range_ids', because
    # refund_sequence_id._get_current_sequence() may invalidate it!
    # @api.depends('advance_sequence_id.use_date_range', 'advance_sequence_id.number_next_actual')
    # def _compute_advance_seq_number_next(self):
    #     '''Compute 'sequence_number_next' according to the current sequence in use,
    #     an ir.sequence or an ir.sequence.date_range.
    #     '''
    #     for journal in self:
    #         if journal.advance_sequence_id and journal.advance_sequence:
    #             sequence = journal.advance_sequence_id._get_current_sequence()
    #             journal.advance_sequence_number_next = sequence.number_next_actual
    #         else:
    #             journal.advance_sequence_number_next = 1
    #
    # def _inverse_advance_seq_number_next(self):
    #     '''Inverse 'refund_sequence_number_next' to edit the current sequence next number.
    #     '''
    #     for journal in self:
    #         if journal.advance_sequence_id and journal.advance_sequence and journal.advance_sequence_number_next:
    #             sequence = journal.advance_sequence_id._get_current_sequence()
    #             sequence.sudo().number_next = journal.advance_sequence_number_next

    def name_get(self):
        res = []
        for journal in self:
            # currency = journal.currency_id or journal.company_id.currency_id
            # name = "%s (%s)" % (journal.name, currency.name)
            name = "%s" % (journal.name)
            res += [(journal.id, name)]
        return res

    # @api.model
    # def _get_adv_sequence_prefix(self, code):
    #     prefix = code.upper()
    #     prefix = 'ADV' + prefix
    #     return prefix + '/%(range_year)s/'

    # @api.model
    # def _create_sequence_advance(self, vals):
    #     """ Create new no_gap entry sequence for every new Journal"""
    #     prefix = self._get_adv_sequence_prefix(vals['code'])
    #     seq_name = vals['code'] + _(': Advance') or vals['code']
    #     seq = {
    #         'name': _('%s Sequence') % seq_name,
    #         'implementation': 'no_gap',
    #         'prefix': prefix,
    #         'padding': 4,
    #         'number_increment': 1,
    #         'use_date_range': True,
    #     }
    #     if 'company_id' in vals:
    #         seq['company_id'] = vals['company_id']
    #     seq = self.env['ir.sequence'].create(seq)
    #     seq_date_range = seq._get_current_sequence()
    #     seq_date_range.number_next = vals.get('advance_sequence_number_next', 1) or vals.get('sequence_number_next', 1)
    #     return seq

    # @api.model
    # def create(self, vals):
    #     if 'advance_sequence' not in vals:
    #         vals['advance_sequence'] = vals['type'] in ('cash', 'bank')
    #     if vals.get('type') in ('cash', 'bank') and vals.get('advance_sequence') and not vals.get(
    #             'advance_sequence_id'):
    #         vals.update({'advance_sequence_id': self.sudo()._create_sequence_advance(vals).id})
    #     res = super(AccountJournal, self).create(vals)
    #     return res

    # def write(self, vals):
    #     # create the relevant advance sequence
    #     if vals.get('advance_sequence'):
    #         for journal in self.filtered(lambda j: j.type in ('cash', 'bank') and not j.advance_sequence_id):
    #             journal_vals = {
    #                 'name': journal.name,
    #                 'company_id': journal.company_id.id,
    #                 'code': journal.code,
    #                 'advance_sequence_number_next': vals.get('advance_sequence_number_next',
    #                                                          journal.advance_sequence_number_next),
    #             }
    #             journal.advance_sequence_id = self.sudo()._create_sequence_advance(journal_vals).id
    #     res = super(AccountJournal, self).write(vals)
    #     return res
