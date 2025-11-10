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
from datetime import date
import datetime
import requests
from odoo.fields import Date
from odoo.tools import date_utils

from odoo.exceptions import UserError

from odoo import models, fields, api, _


class ProductTemplateUpdt(models.Model):
    """Inherited to add a button inside Action for Adding Products to Multiple Locations"""
    _inherit = 'product.template'

    def add_product_to_locations(self):
        """Function for the Adding Products to Multiple Locations"""
        products = self.env['product.product'].search([('product_tmpl_id', '=', self.ids)]).ids
        return {
            'name': _('Add Products'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(self.env.ref('add_product_multi_location.add_product_wizard_form').id, 'form')],
            'res_model': 'add.product.wizard',
            'target': 'new',
            'context': {'default_product_ids': products}
        }




