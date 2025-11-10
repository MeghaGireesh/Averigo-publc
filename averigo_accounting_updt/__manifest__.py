# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Alvin @ cybrosys,(odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
{
    "name": "Averigo Accounting Updates",
    "summary": "Averigo Accounting Updates",
    "version": "13.0.0.2",
    "category": "",
    "website": "http://www.cybrosys.com",
    "description": """Averigo Accounting Updates""",
    'images': [
        # 'images/screen.png'
    ],
    "author": "Cybrosys Techno Solutions Pvt Ltd.",
    "license": "LGPL-3",
    "installable": True,
    "depends": [
        'base', 'account', 'averigo_accounting', 'averigo_credit_memo_updt', 'averigo_cp_code'
    ],
    "data": [
        'security/ir.model.access.csv',
        'report/bill_payment_report.xml',
        'report/bill_payment_report_template.xml',
        'report/payment_receipt_report.xml',
        'report/payment_receipt_report_template.xml',
        'report/advance_payment_report.xml',
        'report/advance_payment_report_template.xml',
        'data/data.xml',
        'views/register_payment_views_inherit.xml',
        'views/invoice_receipt_views_inherit.xml',
        'views/bill_payment_view_inherit.xml',
        'views/account_move_inherit_views.xml',
        'views/res_partner.xml',
        'views/advance_payment.xml',
        'views/default_receivable_inherit.xml',
        'views/default_receivable.xml',
        'views/assets.xml',
        'views/advance_payment_lines_view.xml'

    ],
    "qweb": [
        'static/src/xml/account_payment.xml',
        'static/src/xml/button.xml',
    ],
}
