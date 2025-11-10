{
    "name": "Account Payment Widget Amount",
    "summary": "Extends the payment widget to be able to choose the payment "
               "amount",
    'version': '13.0.1.0',
    'category': 'Accounting/Payment',
    'author': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    "description": """""",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": ['account_move_line_auto_reconcile_hook'],
    "data": [
        'views/account.xml',
    ],
    'qweb': [
        "static/src/xml/account_payment.xml",
    ],
}
