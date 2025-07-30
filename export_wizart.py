from odoo import models,api,fields
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta



class ExportAttendanceWizard(models.TransientModel):
    _name = 'gm.export_attendance_wizard'
    _description = 'Export Absensi Wizard'

    month = fields.Selection([
        ('01', 'Januari'),
        ('02', 'Februari'),
        ('03', 'Maret'),
        ('04', 'April'),
        ('05', 'Mei'),
        ('06', 'Juni'),
        ('07', 'Juli'),
        ('08', 'Agustus'),
        ('09', 'September'),
        ('10', 'Oktober'),
        ('11', 'November'),
        ('12', 'Desember'),
    ], string="Bulan", required=True)

    year = fields.Integer(string="Tahun", required=True, default=datetime.now().year)

    def action_export(self):
        selected_month = int(self.month)
        selected_year = self.year

        # Hitung tanggal 26 bulan lalu - 25 bulan yg dipilih
        period_start = datetime(selected_year, selected_month, 26) - relativedelta(months=1)
        period_end = datetime(selected_year, selected_month, 25) + timedelta(hours=23, minutes=59, seconds=59)

        # Panggil method di model `gm.fingerprint_log`
        logs = self.env['gm.fingerprint_log'].search([
            ('timestamp', '>=', period_start),
            ('timestamp', '<=', period_end)
        ])

        return logs.action_export_excel_wizard(period_start, period_end)
    
    
    def action_export_pdf(self):
        selected_month = int(self.month)
        selected_year = self.year

        period_start = datetime(selected_year, selected_month, 26) - relativedelta(months=1)
        period_end = datetime(selected_year, selected_month, 25, 23, 59, 59)

        logs = self.env['gm.fingerprint_log'].search([
            ('timestamp', '>=', period_start),
            ('timestamp', '<=', period_end)
        ])

        # Delegasikan ke model fingerprint_log
        return self.env['gm.fingerprint_log'].action_export_pdf_wizard(period_start, period_end)




