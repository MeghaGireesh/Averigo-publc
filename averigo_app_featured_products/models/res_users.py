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

from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    group_featured_product = fields.Boolean(string="Featured Product",
                                            default=True)

    @api.model
    def create(self, vals_list):
        res = super(ResUsers, self).create(vals_list)
        if 'create_company' in self._context \
                and self._context['create_company']:
            # add access right for featured product
            res._add_one_access_right(
                'averigo_app_featured_products.operator_featured_product_read')
        return res

    @api.onchange('group_featured_product')
    def change_group_featured_product(self):
        """ Add or remove featured product access """
        if self.group_featured_product:
            # add group if access is added
            self._add_one_access_right(
                'averigo_app_featured_products.operator_featured_product_read')
        else:
            # remove the group is the access is disabled
            self._remove_one_access_right(
                'averigo_app_featured_products.operator_featured_product_read')
