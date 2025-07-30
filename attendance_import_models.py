# -*- coding: utf-8 -*-
import os
from datetime import datetime
from collections import defaultdict
from odoo import models, fields, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class GMAttendanceImport(models.TransientModel):
    _name = 'gm.attendance_import'
    _description = 'Import Fingerprint Log'

    def action_import_absen(self):
        folder_path = '/odoo/absen/'
        if not os.path.isdir(folder_path):
            raise UserError(_('Folder tidak ditemukan: %s') % folder_path)

        FingerprintUser = self.env['gm.fingerprint_user']
        FingerprintLog = self.env['gm.fingerprint_log']
        raw_logs = defaultdict(list)

        csv_files = [f for f in os.listdir(folder_path) if f.startswith('absen-') and f.endswith('.csv')]
        if not csv_files:
            raise UserError(_('Tidak ada file absen-xxx.csv ditemukan di %s') % folder_path)

        for filename in csv_files:
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                for line in csvfile:
                    line = line.strip()
                    if not line:
                        continue
                    row = line.split()
                    if len(row) < 3:
                        continue
                    fingerprint_id = row[0]
                    timestamp_str = f"{row[1]} {row[2]}"
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        date_str = timestamp.date().isoformat()
                        key = (fingerprint_id, date_str)
                        raw_logs[key].append(timestamp)
                    except Exception:
                        continue

        for (fid, date), timestamps in raw_logs.items():
            timestamps.sort()
            user_map = FingerprintUser.search([('fingerprint_user_id', '=', int(fid))], limit=1)
            if not user_map:
                continue
            employee = user_map.employee_id

            checkin, checkout = None, None
            for ts in timestamps:
                if not checkin and ts.time() < datetime.strptime('10:00:00', '%H:%M:%S').time():
                    checkin = ts
                elif not checkout:
                    checkout = ts

            warnings = []
            if len(timestamps) == 1:
                warnings.append('Absen hanya 1x')
            elif len(timestamps) > 2:
                warnings.append('Absen > 2x')

            if checkin and checkin.time() > datetime.strptime('09:10:00', '%H:%M:%S').time():
                warnings.append('Terlambat')

            if checkout and checkout.time() > datetime.strptime('19:30:00', '%H:%M:%S').time():
                warnings.append('Lembur')

            if checkout and checkout.time() < datetime.strptime('18:00:00', '%H:%M:%S').time():
                warnings.append('Pulang sebelum jam 18:00')

            if checkin:
                FingerprintLog.create({
                    'fingerprint_id': fid,
                    'timestamp': checkin,
                    'check_type': 'checkin',
                    'employee_id': employee.id if employee else False,
                    'warning': '; '.join(warnings),
                })

            if checkout and checkout != checkin:
                FingerprintLog.create({
                    'fingerprint_id': fid,
                    'timestamp': checkout,
                    'check_type': 'checkout',
                    'employee_id': employee.id if employee else False,
                    'warning': '; '.join(warnings),
                })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Berhasil'),
                'message': _('Import fingerprint selesai. Silakan cek menu Fingerprint Logs.'),
                'sticky': False,
            }
        }
