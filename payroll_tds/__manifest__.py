{
    'name': "Payroll TDS",
    'version': '1.0.0',
    'depends': ['base', 'hr','hr_payroll','l10n_in_hr_payroll','hr_holidays'],
    'author': "Unisas ITBusiness Solutions Private Limited",
    'category': 'HRMS/Payroll',
    'summary': "Complete HRMS Payroll management with TDS, PF, ESI and automated payslip processing",    'description': """
        HRMS Payroll Management
        =======================
        
        This module extends the Human Resource and Payroll functionalities in 
        Odoo to efficiently manage employee salary processing,
        statutory compliance, and payroll reporting.
    """,
    'data': [
        'views/hr_employee_inherit.xml',
        'views/hr_employee_views_inherit.xml',
        'views/hr_leave_inherit.xml',
        'views/hr_version_inherit.xml',
        'views/hr_payslip_fnf_views.xml',
        'views/hr_payslip_views.xml',
        'report/leave_report.xml',
        'report/fnf_report.xml',
        'report/fnf_report_template.xml'

        # 'views/report_payslip_inherit.xml'
        # 'views/hr_version_inherit.xml'
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
