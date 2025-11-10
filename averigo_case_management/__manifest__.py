{
    "name": "Averigo Case Management",
    "version": "13.0.1.0.0",
    "license": "AGPL-3",
    "author": "Cybrosys Techno Solutions Pvt Ltd.",
    "website": "http://www.cybrosys.com",
    "category": "Accounting & Finance",
    "depends": ['account', 'base_averigo', 'micro_market', 'averigo_accounting', 'averigo_service_management',
                'account_asset_management',
                'averigo_security', 'hr'],
    "data": [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/mail_template.xml',
        'views/case_management.xml',
        'views/attachment_view.xml',
        'wizard/case_management.xml',
        'views/service_management.xml',
        'views/note_view.xml',
        'views/assets.xml',
        'views/hr_employee.xml',
        'views/tech_person_wizard_view.xml'
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    "content_security_policy": "default-src 'self' style-src 'self' 'unsafe-inline';",
    "external_dependencies": {"python": ["python-dateutil"]},
}
