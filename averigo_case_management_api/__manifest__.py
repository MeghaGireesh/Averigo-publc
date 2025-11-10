{
    'name': "Case Management Api",
    'version': '13.0.1.0',
    'author': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'summary': '',
    "description": """""",
    'depends': ['base','averigo_case_management', 'averigo_portal_case_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/sync_input.xml',
        'views/number_valid_templates.xml',
        'views/case_management_views.xml',
    ],
    'license': 'AGPL-3',
    'application': True,
    'installable': True,
    'auto_install': False,


}
