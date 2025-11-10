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


class GeneralLedger(models.Model):
    _name = 'general.ledger'
    _inherit = 'mail.thread'
    _description = 'General Ledger'
    """Default Setup General Ledger"""

    name = fields.Char()
    restock_fee_credit_debit = fields.Boolean()
    restock_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('amount', 'Amount')], index=True, tracking=True)
    restock_fee_percent = fields.Float()
    restock_amount = fields.Float()
    display_account = fields.Many2one('account.account', domain=[('deprecated', '=', False)])
    service_charges = fields.Many2one('account.account', domain=[('deprecated', '=', False)])
    interest_earned = fields.Many2one('account.account', domain=[('deprecated', '=', False)])
    interest_paid = fields.Many2one('account.account', domain=[('deprecated', '=', False)])
    undeposited_funds = fields.Many2one('account.account', domain=[('deprecated', '=', False)])
    retained_earnings = fields.Many2one('account.account', domain=[('deprecated', '=', False)])
    journal_adjustment = fields.Many2one('account.account', domain=[('deprecated', '=', False)])
    restock_fee = fields.Many2one('account.account', domain=[('deprecated', '=', False)])
