# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import base64
from dateutil.relativedelta import relativedelta
import io
import xlsxwriter
from collections import defaultdict
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging


class FingerprintLog(models.Model):
    _name = 'gm.fingerprint_log'
    _description = 'Fingerprint Attendance Log'

    fingerprint_id = fields.Integer(string='Fingerprint ID', required=True)
    timestamp = fields.Datetime(string='Timestamp', required=True)
    check_type = fields.Selection(
        [('checkin', 'Check In'), ('checkout', 'Check Out')],
        string='Check Type',
        required=True
    )
    employee_id = fields.Many2one('hr.employee', string='Employee')
    warning = fields.Char(string='Warning')

    @api.model
    def create(self, vals):
        # Hindari duplikat berdasarkan fingerprint_id dan timestamp detik presisi
        existing = self.search([
            ('fingerprint_id', '=', vals.get('fingerprint_id')),
            ('timestamp', '=', vals.get('timestamp'))
        ], limit=1)
        if existing:
            return existing
        return super().create(vals)

    # print excel
    def action_export_excel(self, period_start=None, period_end=None):
        if not self:
            raise UserError("Tidak ada data yang dipilih.")

        if not period_start or not period_end:
            # Mode default (tanpa wizard): ambil dari data terakhir
            latest_date = max(log.timestamp for log in self)
            period_end = datetime(latest_date.year, latest_date.month, 25)
            period_start = period_end - relativedelta(months=1) + timedelta(days=1)

        # Filter log berdasarkan periode
        filtered_logs = self.filtered(
            lambda l: l.timestamp.date() >= period_start.date() and l.timestamp.date() <= period_end.date()
        )
        if not filtered_logs:
            raise UserError("Tidak ada data fingerprint untuk periode %s - %s" % (
                period_start.strftime('%d-%m-%Y'), period_end.strftime('%d-%m-%Y')))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Styles
        bold = workbook.add_format({'bold': True})
        title = workbook.add_format({'align': 'center','bold': True, 'font_size' : '18px'})
        header_info = workbook.add_format({'align': 'center','bold': True, 'border': 1})
        header_format = workbook.add_format({'align': 'center','bold': True, 'bg_color': '#D9D9D9', 'border': 1})
        cell_format = workbook.add_format({'border': 1,'align': 'center'})
        center = workbook.add_format({'align': 'center', 'border': 1})
        left = workbook.add_format({'align': 'left', 'border': 1})

        format_red = workbook.add_format({'align': 'left', 'border': 1, 'bg_color': '#FFC7CE'})    # Terlambat
        format_yellow = workbook.add_format({'align': 'left', 'border': 1, 'bg_color': '#FFEB9C'}) # Absen 1x atau Pulang awal
        format_default = workbook.add_format({'align': 'left', 'border': 1})                       # Default



        logs_by_employee = defaultdict(list)
        for log in filtered_logs:
            if log.employee_id:
                logs_by_employee[log.employee_id].append(log)

        for emp, logs in logs_by_employee.items():
            sheet = workbook.add_worksheet(emp.name[:31])

            sheet.set_paper(9)         # A4
            sheet.fit_to_pages(1, 0)   # Fit semua kolom ke 1 halaman lebar (tinggi bebas)
            sheet.center_horizontally()
            sheet.set_margins(left=0.2, right=0.2, top=0.5, bottom=0.5)  # Optional: margin tipis

            row = 0

            sheet.set_column("A:A", 20)
            sheet.set_column("B:B", 15)
            sheet.set_column("C:C", 15)
            sheet.set_column("D:D", 40)

            # Header
            sheet.set_row(0, 50) 
            sheet.set_row(2, 40) 
            sheet.set_row(4, 20) 
            sheet.set_row(5, 20) 
            sheet.set_row(6, 20) 
            sheet.set_row(7, 20) 

            sheet.merge_range(row, 0,row, 3, 'Absensi', title)
            row += 1
            nama_bulan = {
                1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
                5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
                9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
            }

            periode_str = f"{period_start.day} {nama_bulan[period_start.month]} {period_start.year}           s/d            {period_end.day} {nama_bulan[period_end.month]} {period_end.year}"
            row += 1
            sheet.merge_range(row, 0,row, 3, periode_str, title)
            # sheet.write(row, 1, periode_str, title)
            # sheet.write(row, 0, period_start.strftime('%Y-%m-%d'))
            # sheet.write(row, 3, period_end.strftime('%Y-%m-%d'))
            row += 2

            # Info Pegawai
            sheet.merge_range(row, 0,row, 1, 'Nama :', header_info)
            sheet.merge_range(row, 2,row, 3, emp.name, header_info)
            row += 1

            checkin_days = set()
            terlambat = 0
            lembur = 0
            log_by_day = defaultdict(list)

            for log in logs:
                date = log.timestamp.date()
                log_by_day[date].append(log)
                if log.check_type in ('checkin', 'checkout'):
                    checkin_days.add(date)

            for date, items in log_by_day.items():
                masuk_list = [l.timestamp for l in items if l.check_type == 'checkin']
                if masuk_list and min(masuk_list).time() > datetime.strptime("09:15:00", "%H:%M:%S").time():
                    terlambat += 1

                pulang_list = [l.timestamp for l in items if l.check_type == 'checkout']
                if pulang_list and max(pulang_list).time() > datetime.strptime("19:00:00", "%H:%M:%S").time():
                    lembur += 1

            sheet.merge_range(row, 0,row, 1, 'Masuk :', header_info)
            sheet.merge_range(row, 2,row, 3, f'{len(checkin_days)} Hari', header_info)
            # sheet.write(row, 1, f'{len(checkin_days)} Hari')
            row += 1

            sheet.merge_range(row, 0,row, 1, 'Terlambat :', header_info)
            sheet.merge_range(row, 2,row, 3, f'{terlambat} Hari', header_info)
            row += 1

            sheet.merge_range(row, 0,row, 1, 'Lembur :', header_info)
            sheet.merge_range(row, 2,row, 3, f'{lembur} Hari',header_info)
            row += 2

            # Table header
            sheet.write(row, 0, "Tanggal", header_format)
            sheet.write(row, 1, "Masuk", header_format)
            sheet.write(row, 2, "Pulang", header_format)
            sheet.write(row, 3, "Keterangan", header_format)
            row += 1

            for date in sorted(log_by_day):
                masuk_dt = None
                pulang_dt = None

                masuk_str = ''
                pulang_str = ''
                ket = ''
                logs_today = log_by_day[date]

                checkins_all = [l.timestamp for l in logs_today if l.check_type == 'checkin']
                checkins = [t for t in checkins_all if t.time() <= datetime.strptime("12:00:00", "%H:%M:%S").time()]
                checkouts = [l.timestamp for l in logs_today if l.check_type == 'checkout' and l.timestamp.time() >= datetime.strptime("12:00:00", "%H:%M:%S").time()]
                invalid_checkins = [t for t in checkins_all if t.time() > datetime.strptime("12:00:00", "%H:%M:%S").time()]

                ket_list = []

                if checkins:
                    masuk_dt = min(checkins)
                    masuk_str = masuk_dt.strftime('%H:%M:%S')
                if invalid_checkins:
                    ket_list.append('Absen masuk di atas jam 12:00')
                if checkouts:
                    pulang_dt = max(checkouts)
                    pulang_str = pulang_dt.strftime('%H:%M:%S')



                if masuk_dt:
                    jam_batas = datetime.combine(masuk_dt.date(), datetime.strptime("09:15:00", "%H:%M:%S").time())
                    if masuk_dt > jam_batas:
                        selisih_menit = int((masuk_dt - jam_batas).total_seconds() // 60)
                        ket_list.append(f'Terlambat - {selisih_menit} menit')
                else:
                    ket_list.append('Tidak ada absen masuk')

                if pulang_dt:
                    if pulang_dt.time() < datetime.strptime("18:00:00", "%H:%M:%S").time():
                        ket_list.append('Pulang lebih awal dari 18:00')
                else:
                    ket_list.append('Tidak ada absen pulang')

                # if not masuk_dt or not pulang_dt:
                #     ket_list.append('Absen hanya 1x')

                
                ket = '; '.join(ket_list)

                # Tentukan format warna berdasarkan isi keterangan
                if 'Terlambat' in ket:
                    ket_format = format_red
                elif 'Absen hanya 1x' in ket or 'Pulang lebih awal' in ket:
                    ket_format = format_yellow
                else:
                    ket_format = format_default

                sheet.write(row, 0, date.strftime('%Y-%m-%d'), cell_format)
                sheet.write(row, 1, masuk_str, center)
                sheet.write(row, 2, pulang_str, center)
                sheet.write(row, 3, ket, ket_format)

                row += 1

                _logger = logging.getLogger(__name__)
                _logger.info(f'{date} | {emp.name} | Keterangan: {ket}')
                _logger.info(f'Date: {date}, Masuk: {masuk_dt}, Pulang: {pulang_dt}, Ket: {ket_list}')



        

        workbook.close()
        output.seek(0)
        content = base64.b64encode(output.read())

        attachment = self.env['ir.attachment'].create({
            'name': f'Absensi_{period_start.strftime("%Y%m")}.xlsx',
            'type': 'binary',
            'datas': content,
            'res_model': 'gm.fingerprint_log',
            'res_id': self.ids[0],
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }
    
    def action_export_excel_wizard(self, period_start, period_end):
        # Cari log berdasarkan tanggal dari wizard
        logs = self.env['gm.fingerprint_log'].search([
            ('timestamp', '>=', period_start),
            ('timestamp', '<=', period_end)
        ])
        if not logs:
            raise UserError("Tidak ada data fingerprint untuk periode yang dipilih.")

        return logs.action_export_excel(period_start=period_start, period_end=period_end)
    
    # def action_export_pdf_wizard(self, date_start, date_end):
    #     return self.env.ref('gm_hr_attendance.action_report_absensi_fingerprint_v2').report_action(
    #         docids=[],  # Jangan pakai logs di sini
    #         data={
    #             'date_start': date_start.strftime('%Y-%m-%d'),
    #             'date_end': date_end.strftime('%Y-%m-%d'),
    #         }
    #     )
    
    def action_export_pdf_wizard(self, date_start, date_end):
        logs = self.env['gm.fingerprint_log'].search([
            ('timestamp', '>=', date_start),
            ('timestamp', '<=', date_end),
        ])

        if not logs:
            raise UserError("Tidak ada data fingerprint pada rentang tanggal yang dipilih.")

        return self.env.ref('gm_hr_attendance.action_report_absensi_fingerprint_v2').report_action(
            docids=[],  # Jangan pakai logs di sini
            data={
                'date_start': date_start.strftime('%Y-%m-%d'),
                'date_end': date_end.strftime('%Y-%m-%d'),
            }
        )

  





