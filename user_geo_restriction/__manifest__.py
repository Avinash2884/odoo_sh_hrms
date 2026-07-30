
{
    'name': "User Geo Restriction",
    'version': '1.0.0',
    'depends': ['base','hr_attendance','hr'],
    'summary': "User Geo Restriction",
    'author': "Unisas ITBusiness Solutions Private Limited",
    'category': 'Human Resource',
    'license': 'LGPL-3',
    'data': [
        "security/ir.model.access.csv",
        "views/geo_restriction.xml",
        "views/hr_attendance_inherit.xml",
        "views/hr_employee.xml",
    ],
    'installable': True,
    'application': True,
}
