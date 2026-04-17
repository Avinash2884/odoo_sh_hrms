
{
    'name': "Recruitment Dashboard",
    'version': '1.0.0',
    "depends": [
        "hr",
        "hr_recruitment",   # ✅ MUST
        "web"
    ],
    'author': "Akshaya",
    'category': 'Human Resource',
    'summary': "Recruitment Dashboard",
    'data': [
        # "views/assest.xml",
        'views/recruitment_views.xml',
             ],
    'assets': {
        'web.assets_backend': [
            'recruitment_dashboard/static/lib/chartjs/chart.umd.js',
            'recruitment_dashboard/static/src/js/recruitment.js',
            'recruitment_dashboard/static/src/css/recruitment.css',
            'recruitment_dashboard/static/src/xml/recruitment_template.xml',
        ]},
    # 'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
