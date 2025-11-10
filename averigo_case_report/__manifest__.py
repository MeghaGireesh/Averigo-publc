{
    "name": "Case Report",
    "version": "13.0.1.0.0",
    "author": "Cybrosys Techno Solutions Pvt Ltd.",
    "website": "http://www.cybrosys.com",
    "category": "Accounting & Finance",
    "depends": ['averigo_case_management'],
    "data": [
        'security/ir.model.access.csv',
        # 'views/report_menu.xml',
        'data/data.xml',
        'views/action_manager.xml',
        # 'views/case_note_tree.xml',
        'views/case_detailed_report.xml',
        'report/case_management_report.xml'
    ],
    "qweb": [
        "static/src/xml/template.xml"
    ],
}
