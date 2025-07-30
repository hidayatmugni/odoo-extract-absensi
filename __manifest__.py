# -*- coding: utf-8 -*-
{
    'name': 'HR Attendance',
    'summary': 'Import and process fingerprint attendance data',
    'version': '0.4',
    'category': 'Human Resources',
    'author': 'Mugni Hidayat',
    'website': 'https://www.galerimedika.com',
    'depends': ['hr_attendance'],
    'data': [
        'security/ir.model.access.csv',
        'report/absensi_report_templates.xml',
        'report/absensi_reports.xml',
        'views/attendance_import_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    # 'license': 'OPL-1',
}
