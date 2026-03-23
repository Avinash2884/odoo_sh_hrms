

{
    'name': "Attendance Location",
    'version': '1.0.0',
    'depends': ['base', 'hr_attendance'],
    'summary': "Attendance Location",
    'author': "Unisas ITBusiness Solutions Private Limited",
    'category': 'Attendance Location',
    'license': 'LGPL-3',
    'data': [
        "security/ir.model.access.csv",
        "views/geo_restriction.xml",
    ],
    'installable': True,
    'application': True,
}

