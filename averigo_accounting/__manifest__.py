



{
    "name": "Averigo Accounting",
    "summary": "Averigo Accounting",
    "version": "13.0.0.1",
    "category": "",
    "website": "http://www.cybrosys.com",
    "description": """Averigo Accounting""",
    'images': [
        # 'images/screen.png'
    ],
    "author": "Cybrosys Techno Solutions Pvt Ltd.",
    "license": "LGPL-3",
    "installable": True,
    "depends": [
        'base', 'account', 'base_averigo', 'micro_market', 'averigo_purchase',
    ],
    "data": [
        'data/data.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/advance_payment.xml',
        'views/account_move_view.xml',
        'views/accounting_views.xml',
        'views/res_partner_card.xml',
        'views/res_partner_check.xml',
        'views/default_receivable.xml',
        'views/general_ledger.xml',
        'views/res_partner_views.xml',
        'views/default_payable.xml',
        'views/payable_advance_payment.xml',
        'views/misc_receipt_views.xml',
        'views/bill_payment_view.xml',
        'views/payment_view.xml',
        'views/ir_sequence.xml',
        'views/invoice_receipt.xml',
        'views/micro_market_invoice_views.xml',
        'views/report_payment_receipt_templates.xml',
        # 'views/account_journal.xml',
    ],
    "qweb": [],
}
