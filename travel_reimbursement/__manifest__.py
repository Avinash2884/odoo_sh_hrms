{
    'name': 'Travel Reimbursement',
    'version': '1.0.0',
    'category': 'Human Resource',
    'summary': 'Expenses',
    'author': 'Akshaya',
    'depends': ['hr','hr_expense'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_expense_inherit.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
