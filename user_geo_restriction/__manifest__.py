
{
    'name': "User Geo Restriction",
    'version': '1.0.0',
    'depends': ['base','hr_attendance'],
    'summary': "User Geo Restriction",
    'author': "Unisas ITBusiness Solutions Private Limited",
    'category': 'User Geo Restriction',
    'license': 'LGPL-3',
    'data': [
        "security/ir.model.access.csv",
        "views/geo_restriction.xml",
    ],
    'installable': True,
    'application': True,
}
