# -*- coding: utf-8 -*-
######################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2019-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>))
#
#    This program is under the terms of the Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the Software
#    or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#    IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#    DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
#    ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
########################################################################################
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_default_control_account_id(self):
        """ default KAM for vendor and false for customer"""
        control_account_id = None
        if self._context.get('default_is_customer') == True:
            default_receivable = self.env['default.receivable'].search(
                [('operator_id', '=', self.env.company.id)])
            if default_receivable:
                control_account_id = self.env['default.receivable'].search(
                    [('operator_id', '=', self.env.company.id)]).receivables_control_account_id.id
        return control_account_id

    def _get_default_sales_discount_account_id(self):
        """ default KAM for vendor and false for customer"""
        sales_discount_account_id = None
        if self._context.get('default_is_customer') == True:
            default_receivable = self.env['default.receivable'].search(
                [('operator_id', '=', self.env.company.id)])
            if default_receivable:
                sales_discount_account_id = self.env['default.receivable'].search(
                    [('operator_id', '=', self.env.company.id)]).sales_discount_account_id.id

        return sales_discount_account_id

    def _get_default_advance_account_id(self):
        """ default KAM for vendor and false for customer"""
        advance_account_id = None
        if self._context.get('default_is_customer') == True:
            default_receivable = self.env['default.receivable'].search(
                [('operator_id', '=', self.env.company.id)])
            if default_receivable:
                advance_account_id = self.env['default.receivable'].search(
                    [('operator_id', '=', self.env.company.id)]).advance_account_id.id
        return advance_account_id

    def _get_default_insurance_account_id(self):
        """ default KAM for vendor and false for customer"""
        insurance_account_id = None
        if self._context.get('default_is_customer') == True:
            default_receivable = self.env['default.receivable'].search(
                [('operator_id', '=', self.env.company.id)])
            if default_receivable:
                insurance_account_id = self.env['default.receivable'].search(
                    [('operator_id', '=', self.env.company.id)]).insurance_account_id.id

        return insurance_account_id

    def _get_default_sales_tax_liability_account_id(self):
        """ default KAM for vendor and false for customer"""
        sales_tax_liability_account_id = None
        if self._context.get('default_is_customer') == True:
            default_receivable = self.env['default.receivable'].search(
                [('operator_id', '=', self.env.company.id)])
            if default_receivable:
                sales_tax_liability_account_id = self.env['default.receivable'].search(
                    [('operator_id', '=', self.env.company.id)]).sales_tax_liability_account_id.id

        return sales_tax_liability_account_id

    def _get_default_terms_discount_account_id(self):
        """ default KAM for vendor and false for customer"""
        terms_discount_account_id = None
        if self._context.get('default_is_customer') == True:
            default_receivable = self.env['default.receivable'].search(
                [('operator_id', '=', self.env.company.id)])
            if default_receivable:
                terms_discount_account_id = self.env['default.receivable'].search(
                    [('operator_id', '=', self.env.company.id)]).terms_discount_account_id.id

        return terms_discount_account_id

    def _get_default_shipping_handling_account_id(self):
        """ default KAM for vendor and false for customer"""
        shipping_handling_account_id = None
        if self._context.get('default_is_customer') == True:
            default_receivable = self.env['default.receivable'].search(
                [('operator_id', '=', self.env.company.id)])
            if default_receivable:
                shipping_handling_account_id = self.env['default.receivable'].search(
                    [('operator_id', '=', self.env.company.id)]).s_h_account_id.id
        return shipping_handling_account_id

    property_account_receivable_id = fields.Many2one('account.account', company_dependent=True,
                                                     string="Account Receivable",
                                                     domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False)]",
                                                     help="This account will be used instead of the default one as the receivable account for the current partner",
                                                     required=True, default=_get_default_control_account_id)
    control_account_id = fields.Many2one('account.account', default=_get_default_control_account_id,
                                         domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False)]")
    sales_discount_account_id = fields.Many2one('account.account', default=_get_default_sales_discount_account_id,
                                                domain="[('internal_type', '=', 'other'),('deprecated', '=', False)]")
    advance_account_id = fields.Many2one('account.account', default=_get_default_advance_account_id,
                                         domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False)]")
    insurance_account_id = fields.Many2one('account.account', default=_get_default_insurance_account_id,
                                           domain="[('internal_type', '=', 'other'),('deprecated', '=', False)]")
    sales_tax_liability_account_id = fields.Many2one('account.account',
                                                     default=_get_default_sales_tax_liability_account_id,
                                                     domain="[('internal_type', '=', 'other'),('deprecated', '=', False)]")
    terms_discount_account_id = fields.Many2one('account.account', default=_get_default_terms_discount_account_id,
                                                domain="[('internal_type', '=', 'other'),('deprecated', '=', False)]")
    shipping_handling_account_id = fields.Many2one('account.account', default=_get_default_shipping_handling_account_id,
                                                   domain="[('internal_type', '=', 'other'),('deprecated', '=', False)]")
    card_ids = fields.One2many('res.partner.card', 'partner_id', string='Banks')
    check_ids = fields.One2many('res.partner.check', 'partner_id', string='Checks')
