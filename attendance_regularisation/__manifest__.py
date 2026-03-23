{
    'name': "Attendance Regularization",
    'version': '1.0.0',
    'category': 'Human Resource',
    'summary': """Assigning Attendance for the Employees with Onsight Jobs""",
    'description': """Assigning Attendance for the Employees with Onsight Jobs 
    through the requests by Employees """,
    'author': 'Akshaya',
    'depends': ['hr','hr_attendance', 'hr_holidays',
                'oh_employee_creation_from_user','planning',],
    'data': [
        'security/ir.model.access.csv',
        'security/attendance_regularization_security.xml',
        # 'security/attendance_security.xml',
        'views/reg_categories_views.xml',
        'views/attendance_regularization_views.xml',
        # 'views/assets.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'attendance_regularisation/static/src/css/timeoff_css.css',
        ],
        },
    'demo': ['data/regularization_data.xml'],
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
