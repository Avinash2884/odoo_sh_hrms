{
    'name': 'Employees From User',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Automatically creates employee while creating user',
    'description': "This module facilitates the automatic creation of "
                   "employee records when users are being created.",
    'author': 'Akshaya',
    'depends': ['hr'],
    'data': [
        'views/res_users_views.xml'
    ],
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
