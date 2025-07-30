# -*- coding: utf-8 -*-
from odoo import models, fields, api

class FingerprintUser(models.Model):
    _name = 'gm.fingerprint_user'
    _description = 'Fingerprint User Mapping'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
        index=True,
        default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
    )
    fingerprint_user_id = fields.Integer(
        string='Fingerprint User ID',
        required=True,
        default=0
    )

    _sql_constraints = [
        ('fingerprint_user_id_unique', 'unique(fingerprint_user_id)', 'Fingerprint ID must be unique!')
    ]

    @api.model
    def get_employee_by_fingerprint(self, fingerprint_id):
        """Mengambil employee berdasarkan fingerprint_id"""
        user = self.search([('fingerprint_user_id', '=', fingerprint_id)], limit=1)
        return user.employee_id if user else False

    def sync_with_attendance(self):
        """Sinkronisasi data fingerprint dengan attendance log"""
        FingerprintLog = self.env['gm.fingerprint_log']
        for user in self:
            logs = FingerprintLog.search([('fingerprint_id', '=', user.fingerprint_user_id)])
            for log in logs:
                if not log.employee_id:
                    log.employee_id = user.employee_id.id
        return True
