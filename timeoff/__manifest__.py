
{
    'name': "Timeoff-Inherit",
    'version': '1.0.0',
    'depends': ['base','hr','mail','hr_holidays'],
    'summary': "TimeOff-Inherit",
    'author': "Unisas ITBusiness Solutions Private Limited",
    'category': 'Human Resource',
    'license': 'LGPL-3',
    'data': [
        "views/hr_leave_inherit.xml",
        "report/leave_report.xml",
    ],
    'installable': True,
    'application': True,
}
