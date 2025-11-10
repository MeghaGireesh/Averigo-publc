{
    "name": "Averigo Accounting Reports",
    "summary": "Averigo Accounting Reports ",
    "version": "13.0.0.1",
    "category": "accounting",
    "website": "http://www.cybrosys.com",
    "description": """Averigo Accounting Reports""",
    "author": "Cybrosys Techno Solutions Pvt Ltd.",
    "license": "LGPL-3",
    "installable": True,
    "depends": ['base', 'account', 'averigo_accounting_updt', 'averigo_accounting', 'averigo_reports'],
    "data": [
        'security/ir.model.access.csv',
        'views/invoice_list_view.xml',
        'views/receipt_list_view.xml',
        'views/bill_list_view.xml',
        'views/assets.xml',
        'report/invoice_list_report.xml',
        'report/receipt_list_report.xml',
        'report/bill_list_report.xml'
    ],
    "qweb": [
            'static/src/xml/One2manyReportLines.xml',
        ],
}
