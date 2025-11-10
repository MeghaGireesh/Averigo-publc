{
    "name": "Averigo App Home Screen Images",
    "summary": "Averigo App Home ScreenImages",
    "version": "13.0.0.1",
    "category": "",
    "website": "http://www.cybrosys.com",
    "description": """Averigo App Home Screen Images""",
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
        'views/ir_image.xml'
    ],
    "qweb": [],
}
