{
    'name': 'Custom Attendance & Planning',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Advanced late policies, exact worked hours, and shift templates',
    'author': "Unisas ITBusiness Solutions Private Limited",
    'depends': [
        'base',
        'hr_attendance',
        'planning',
        'approvals',
        'mail',
        'hr',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/planning_department_wizard_views.xml',
        "views/hr_attendance_view.xml",
        "views/hr_attendance_management_action.xml",
        "views/planning_role_view.xml",
        "views/hr_attendance_custom_view.xml",
        "views/hr_attendance_permission_views.xml",
        'views/hr_employee_views.xml',
        # 'views/selfie_kiosk_action.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # Your existing custom stuff
            "attendance_planning/static/src/js/late_checkout_popup.js",
            "attendance_planning/static/src/css/late_checkout.css",

            # 1. The AI Brain (Name matched perfectly to your downloaded file!)
            # 'attendance_planning/static/src/lib/face-api.js',

            # 2. The Face Register Logic
            'attendance_planning/static/src/js/face_register.js',
            # 'attendance_planning/static/src/js/selfie_kiosk.js',

            # 3. The Face Register UI
            'attendance_planning/static/src/xml/face_register.xml',
            # 'attendance_planning/static/src/xml/selfie_kiosk.xml',

            'attendance_planning/static/src/js/systray_face_patch.js',
            'attendance_planning/static/src/xml/systray_face_popup.xml',

        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
