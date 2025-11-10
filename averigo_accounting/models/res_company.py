from odoo import models, fields, api, _


class AccountJournalCompany(models.Model):
    _inherit = 'res.company'

    def open_default_receivable(self):
        res_id = self.env['default.receivable'].search([('operator_id', '=', self.env.company.id)])
        action = self.env.ref('averigo_accounting.action_default_receivable').read()[0]
        action['res_id'] = res_id.id
        return action

    def open_payable_default(self):
        res_id = self.env['default.payable'].search([('operator_id', '=', self.env.company.id)])
        action = self.env.ref('averigo_accounting.action_payable_default_info').read()[0]
        action['res_id'] = res_id.id
        return action

    @api.model
    def create(self, vals_list):
        res = super(AccountJournalCompany, self).create(vals_list)
        self.env['default.receivable'].create({'operator_id': res.id})
        self.env['default.payable'].create({'operator_id': res.id})
        # tax_model = self.env['ir.model'].search([('model', '=', 'account.tax')])
        # account_model = self.env['ir.model'].search([('model', '=', 'account.account')])
        # journal_model = self.env['ir.model'].search([('model', '=', 'account.journal')])
        property_model = self.env['ir.model'].search([('model', '=', 'ir.property')])
        # tax_rules = self.env['ir.rule'].search([('model_id', '=', tax_model.id)])
        # account_rules = self.env['ir.rule'].search([('model_id', '=', account_model.id)])
        # journal_rules = self.env['ir.rule'].search([('model_id', '=', journal_model.id)])
        property_rules = self.env['ir.rule'].search([('model_id', '=', property_model.id)])
        # for tax_rule in tax_rules:
        #     tax_rule.active = False
        # for account_rule in account_rules:
        #     account_rule.active = False
        # for journal_rule in journal_rules:
        #     journal_rule.active = False
        for property_rule in property_rules:
            property_rule.active = False
        res.load_coa()
        # for tax_rule in tax_rules:
        #     tax_rule.active = True
        # for account_rule in account_rules:
        #     account_rule.active = True
        # for journal_rule in journal_rules:
        #     journal_rule.active = True
        for property_rule in property_rules:
            property_rule.active = True
        return res
