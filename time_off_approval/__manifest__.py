{
    'name': 'Time Off Approval',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Time Off Approval Form',
    'author': 'Akshaya',
    'depends': ['hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/weekend_work_approval.xml',
        'views/weekend_work_approval_management.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
