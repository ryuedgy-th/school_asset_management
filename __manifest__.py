# -*- coding: utf-8 -*-
{
    'name': 'Asset Management',
    'version': '19.0.1.10.0',
    'category': 'Inventory/Assets',
    'summary': 'Asset Management System for International School IT Department',
    'description': """
        School Asset Management Module
        ================================
        Complete asset management solution for educational institutions including:
        * Asset tracking with QR codes
        * Teacher and student assignments
        * Parent online signature system for student assignments
        * Asset inspection and maintenance
        * Damage case management with manager approval workflow
        * Movement history tracking
        * Warranty management
        * Comprehensive reporting
        * PDPA compliance (Thai Personal Data Protection Act)
        * Consent management and data subject rights
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
        'hr',
        'website',
        'school_student_management',  # Integration with student management system
    ],
    'external_dependencies': {
        'python': [
            'Pillow',  # Image processing for signature watermarks
            'redis',   # Distributed rate limiting in multi-worker environment
        ],
    },
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/sequence.xml',
        'data/email_template.xml',
        'data/redis_config.xml',
        'data/default_config.xml',
        'data/dsr_email_templates.xml',
        'data/dsr_scheduled_actions.xml',

        # Views - Base Models
        'views/asset_category_views.xml',
        'views/asset_location_views.xml',
        'views/asset_asset_views.xml',

        # Views - Assignments
        'views/asset_assignment_line_views.xml',
        'views/asset_teacher_assignment_views.xml',
        'views/asset_student_line_views.xml',
        'views/asset_student_assignment_views.xml',

        # Views - Inspection
        'views/asset_inspection_views.xml',

        # Views - Damage Case
        'views/asset_damage_case_views.xml',

        # Views - PDPA Compliance
        'views/asset_consent_log_views.xml',
        'views/asset_data_request_views.xml',
        'views/asset_security_audit_log_views.xml',

        # Views - HR Integration
        'views/hr_employee_views.xml',

        # Wizards
        'wizards/asset_import_wizard_views.xml',
        'wizards/teacher_checkout_wizard_views.xml',
        'wizards/teacher_checkin_wizard_views.xml',
        'wizards/student_distribution_wizard_views.xml',
        'wizards/student_collection_wizard_views.xml',
        'views/consent_withdrawal_wizard_views.xml',

        # Reports
        'reports/report_paperformat.xml',
        'reports/asset_register_template.xml',
        'reports/assignment_template.xml',
        'reports/signed_checkout_waiver.xml',
        'reports/signed_damage_report.xml',
        'reports/inspection_damage_report.xml',
        'reports/damage_case_approval_report.xml',
        'reports/teacher_checkout_waiver.xml',
        'reports/teacher_damage_report.xml',

        # Public Templates (Parent Signature & Manager Approval)
        'templates/static_terms_conditions.xml',
        'templates/privacy_consent.xml',
        'templates/privacy_consent_teacher.xml',
        'templates/checkout_signature_page.xml',
        'templates/damage_report_page.xml',
        'templates/inspection_damage_signature_page.xml',
        'templates/damage_case_approval_page.xml',
        'templates/teacher_checkout_signature_page.xml',
        'templates/teacher_damage_report_page.xml',

        # Dashboard and Menus (Must load AFTER all views that create actions)
        'views/asset_dashboard.xml',
        'views/asset_menus.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'school_asset_management/static/src/css/signature_page.css',
            # Base class must be loaded first
            'school_asset_management/static/src/js/base_signature_pad.js',
            # Specific implementations (order doesn't matter after base)
            'school_asset_management/static/src/js/signature_pad.js',
            'school_asset_management/static/src/js/damage_signature_pad.js',
            'school_asset_management/static/src/js/inspection_damage_signature_pad.js',
            'school_asset_management/static/src/js/teacher_signature_pad.js',
            'school_asset_management/static/src/js/teacher_damage_signature_pad.js',
        ],
        'web.assets_backend': [
            'school_asset_management/static/src/css/dashboard_minimal.css',
            'school_asset_management/static/src/css/consent_form_fix.css',
            'school_asset_management/static/src/js/copy_signature_link.js',
            'school_asset_management/static/src/xml/copy_link_template.xml',
        ],
    },
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
