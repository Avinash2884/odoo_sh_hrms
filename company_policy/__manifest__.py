
{
    'name': "Company Policy",
    'version': '1.0.0',
    'depends': ['base','hr','mail'],
    'summary': "Company Policy",
    'author': "Unisas ITBusiness Solutions Private Limited",
    'category': 'Human Resource',
    'license': 'LGPL-3',
    'data': [
        "security/policy_security.xml",
        "security/ir.model.access.csv",

        "views/company_policy.xml",
        "views/employee_policy.xml",
        "views/menus.xml",


    ],
    'installable': True,
    'application': True,
}
