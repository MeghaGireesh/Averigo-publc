{
    "name": "Averigo App Home Featured Products",
    "summary": "Averigo Special Products",
    "version": "13.0.0.1",
    "category": "",
    "website": "http://www.cybrosys.com",
    "description": """Averigo Special Products""",
    'images': [
        # 'images/screen.png'
    ],
    "author": "Cybrosys Techno Solutions Pvt Ltd.",
    "license": "LGPL-3",
    "installable": True,
    "depends": [
        'base', 'web', 'contacts', 'base_averigo', 'micro_market', 'webservice_image'
    ],
    "data": [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/featured_products.xml',
        'views/res_users_view.xml',
        'data/send_notification.xml',
    ],
    "qweb": [],
}
