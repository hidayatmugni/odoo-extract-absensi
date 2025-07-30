from odoo import api, models
from collections import defaultdict
from datetime import datetime, time
from odoo.exceptions import UserError
import logging


class ReportAttendancePdf(models.AbstractModel):
    _name = 'report.gm_hr_attendance.report_attendance_pdf_template_v2'
    _description = 'Attendance Report PDF'

    @api.model
    def _get_report_values(self, docids, data=None):
        _logger = logging.getLogger(__name__)

        if not data or not data.get('date_start') or not data.get('date_end'):
            raise UserError("Periode tanggal belum dikirim dari wizard.")

        date_start = datetime.strptime(data.get('date_start'), '%Y-%m-%d')
        date_end = datetime.strptime(data.get('date_end'), '%Y-%m-%d')

        logs = self.env['gm.fingerprint_log'].search([
            ('timestamp', '>=', date_start),
            ('timestamp', '<=', date_end),
        ])

        # Kelompokkan berdasarkan employee dan tanggal
        logs_grouped = defaultdict(lambda: defaultdict(list))
        for log in logs:
            if log.employee_id:
                logs_grouped[log.employee_id][log.timestamp.date()].append(log)

        attendance_rows = []

        for emp, date_logs in logs_grouped.items():
            for date, logs in sorted(date_logs.items()):
                checkins = [l.timestamp for l in logs if l.check_type == 'checkin' and l.timestamp.time() <= time(12, 0)]
                late_checkins = [l.timestamp for l in logs if l.check_type == 'checkin' and l.timestamp.time() > time(12, 0)]
                checkouts = [l.timestamp for l in logs if l.check_type == 'checkout' and l.timestamp.time() >= time(12, 0)]

                masuk_dt = min(checkins) if checkins else None
                pulang_dt = max(checkouts) if checkouts else None

                keterangan = []

                if masuk_dt:
                    if masuk_dt.time() > time(9, 15):
                        diff = datetime.combine(date, masuk_dt.time()) - datetime.combine(date, time(9, 15))
                        keterangan.append(f"Terlambat - {int(diff.total_seconds() // 60)} menit")
                else:
                    keterangan.append("Tidak ada absen masuk")

                if pulang_dt:
                    if pulang_dt.time() < time(18, 0):
                        keterangan.append("Pulang lebih awal dari 18:00")
                else:
                    keterangan.append("Tidak ada absen pulang")

                attendance_rows.append({
                    'employee': emp.name,
                    'tanggal': date.strftime('%d-%m-%Y'),
                    'check_in': masuk_dt.strftime('%H:%M:%S') if masuk_dt else '-',
                    'check_out': pulang_dt.strftime('%H:%M:%S') if pulang_dt else '-',
                    'keterangan': keterangan,
                })

        # Grupkan ulang berdasarkan nama employee
        grouped_rows = defaultdict(list)
        for row in attendance_rows:
            grouped_rows[row['employee']].append(row)

        return {
            'doc_model': 'gm.fingerprint_log',
            'grouped_rows': grouped_rows,
            'date_start': data.get('date_start'),
            'date_end': data.get('date_end'),
        }
