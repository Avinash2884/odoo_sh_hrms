
{
    'name': "Separation",
    'version': '1.0.0',
    'depends': ['base','hr','mail','approval_recruitment'],
    'summary': "Separation",
    'author': "Unisas ITBusiness Solutions Private Limited",
    'category': 'Human Resource',
    'license': 'LGPL-3',
    'data': [
        "security/separation_security.xml",
        "security/ir.model.access.csv",

        "data/mail_template_data.xml",

        "views/device_type.xml",
        "views/item_name.xml",
        "views/payroll_component.xml",
        "views/exit_interview_questions.xml",
        "views/initiate_separation.xml",

        "views/menus.xml",
    ],

    'installable': True,
    'application': True,
}
