{
    'name': "Payroll TDS",
    'version': '1.0.0',
    'depends': ['base', 'hr','approvals','hr_payroll','l10n_in_hr_payroll','hr_holidays'],
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
        'data/bereavement_leave_cron.xml',
        'data/probation_sick_leave_cron.xml',
        'data/probation_casual_leave_cron.xml',   # <-- Add this
        'data/comp_off_cron.xml',
        'data/ir_cron.xml',
        'data/monthly_cl_sl_cron.xml',
        'security/ir.model.access.csv',
        'views/hr_employee_inherit.xml',
        'views/hr_employee_views_inherit.xml',
        'views/hr_leave_inherit.xml', #Error
        'views/hr_version_inherit.xml',
        'views/hr_payslip_fnf_views.xml',
        'views/hr_payslip_views.xml',
        'views/approval_requests_views.xml',
        'views/hr_attendance_inherit.xml',
        'views/employee_salary_revision_views.xml',
        'views/hr_employee_rented_house_form.xml',
        'views/hr_employee_investment.xml',
        'views/hr_employee_salary_structure.xml',
        'views/hide_contract_salary_fields.xml',
        'views/hide_work_entry_source.xml',
        'views/salary_revision_wizard_views.xml',
        'views/hr_employee_pay_revise.xml',


        #'views/hr_salary_rule_ind_emp_data_views.xml', #Error
        'report/leave_report.xml',
        'report/fnf_report.xml',
        'report/fnf_report_template.xml',
        # 'report/tds_sheet_report.xml',

        # 'views/report_payslip_inherit.xml'
        # 'views/hr_version_inherit.xml'
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
