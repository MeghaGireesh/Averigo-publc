{
    'name': "Activity Management Api",
    'version': '13.0.1.0',
    'author': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'summary': '',
    "description": """""",
    'depends': ['base','mail','calendar'],
    'data': [
        'security/ir.model.access.csv',
        'views/sync_data.xml',
    ],
    'license': 'AGPL-3',
    'application': True,
    'installable': True,
    'auto_install': False,
}
