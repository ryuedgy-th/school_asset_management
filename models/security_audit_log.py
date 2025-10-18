# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SecurityAuditLog(models.Model):
    """Security audit log for tracking signature attempts and security events"""
    _name = 'asset.security.audit.log'
    _description = 'Security Audit Log'
    _order = 'create_date desc'

    name = fields.Char(string='Event ID', required=True, readonly=True, default='New')
    event_type = fields.Selection([
        ('signature_success', 'Signature Success'),
        ('signature_failed', 'Signature Failed'),
        ('token_invalid', 'Invalid Token Attempt'),
        ('token_expired', 'Expired Token Attempt'),
        ('token_used', 'Used Token Attempt'),
        ('token_tampered', 'Token Tampering Detected'),
        ('rate_limit_exceeded', 'Rate Limit Exceeded'),
        ('validation_failed', 'Validation Failed'),
    ], string='Event Type', required=True, index=True)

    signature_type = fields.Selection([
        ('checkout', 'Student/Parent Checkout Signature'),
        ('damage', 'Student/Parent Damage Report Signature'),
        ('teacher_checkout', 'Teacher Checkout Signature'),
        ('teacher_damage', 'Teacher Damage Report Signature'),
        ('inspection', 'Inspection Signature'),
        ('approval', 'Manager Approval'),
    ], string='Signature Type')

    ip_address = fields.Char(string='IP Address', index=True)
    user_agent = fields.Text(string='User Agent')
    token_prefix = fields.Char(string='Token Prefix (first 8 chars)', help='For security, only first 8 characters stored')

    related_model = fields.Char(string='Related Model')
    related_id = fields.Integer(string='Related Record ID')

    student_name = fields.Char(string='Student Name')
    parent_email = fields.Char(string='Parent Email')

    teacher_name = fields.Char(string='Teacher Name')
    teacher_email = fields.Char(string='Teacher Email')

    error_message = fields.Text(string='Error Message')
    additional_info = fields.Text(string='Additional Information')

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('asset.security.audit.log') or 'New'
        return super().create(vals_list)

    @api.model
    def log_signature_attempt(self, event_type, signature_type, ip_address, token=None,
                              related_model=None, related_id=None, error_message=None, **kwargs):
        """
        Log signature-related security event

        Args:
            event_type: Type of event (signature_success, signature_failed, etc.)
            signature_type: checkout, damage, inspection, or approval
            ip_address: Client IP address
            token: Full token (only first 8 chars will be stored)
            related_model: Model name (e.g., 'asset.student.assignment')
            related_id: Record ID
            error_message: Error message if applicable
            **kwargs: Additional info (student_name, parent_email, etc.)
        """
        vals = {
            'event_type': event_type,
            'signature_type': signature_type,
            'ip_address': ip_address,
            'token_prefix': token[:8] if token else None,
            'related_model': related_model,
            'related_id': related_id,
            'error_message': error_message,
            'student_name': kwargs.get('student_name'),
            'parent_email': kwargs.get('parent_email'),
            'teacher_name': kwargs.get('teacher_name'),
            'teacher_email': kwargs.get('teacher_email'),
            'user_agent': kwargs.get('user_agent'),
            'additional_info': str(kwargs) if kwargs else None,
        }
        return self.create(vals)

    @api.model
    def log_security_event(self, event_type, ip_address, error_message=None,
                          related_model=None, related_id=None, additional_info=None, **kwargs):
        """
        Log general security event (rate limiting, validation errors, etc.)

        Args:
            event_type: Type of event (rate_limit_exceeded, validation_failed, etc.)
            ip_address: Client IP address
            error_message: Error message if applicable
            related_model: Model name
            related_id: Record ID
            additional_info: Additional information (can be dict or string)
            **kwargs: Additional fields
        """
        # Convert additional_info dict to string
        if isinstance(additional_info, dict):
            additional_info = str(additional_info)

        vals = {
            'event_type': event_type,
            'ip_address': ip_address,
            'error_message': error_message,
            'related_model': related_model,
            'related_id': related_id,
            'additional_info': additional_info,
            'user_agent': kwargs.get('user_agent'),
        }
        return self.create(vals)

    @api.model
    def get_security_stats(self, days=30):
        """
        Get security statistics for dashboard

        Args:
            days: Number of days to analyze

        Returns:
            dict: Security statistics
        """
        domain = [
            ('create_date', '>=', fields.Datetime.now() - fields.timedelta(days=days))
        ]

        total_attempts = self.search_count(domain)
        failed_attempts = self.search_count(domain + [('event_type', 'in', ['signature_failed', 'token_invalid', 'token_expired'])])
        rate_limited = self.search_count(domain + [('event_type', '=', 'rate_limit_exceeded')])

        # Top suspicious IPs (most failed attempts)
        failed_by_ip = {}
        failed_records = self.search(domain + [('event_type', 'in', ['signature_failed', 'token_invalid'])])
        for record in failed_records:
            if record.ip_address:
                failed_by_ip[record.ip_address] = failed_by_ip.get(record.ip_address, 0) + 1

        suspicious_ips = sorted(failed_by_ip.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            'total_attempts': total_attempts,
            'failed_attempts': failed_attempts,
            'success_rate': ((total_attempts - failed_attempts) / total_attempts * 100) if total_attempts > 0 else 0,
            'rate_limited_count': rate_limited,
            'suspicious_ips': suspicious_ips,
        }

    @api.model
    def cleanup_old_logs(self, days=730):
        """
        GDPR: Delete audit logs older than retention period (default 2 years)

        Args:
            days: Retention period in days (default 730 = 2 years)
        """
        cutoff_date = fields.Datetime.now() - fields.timedelta(days=days)
        old_logs = self.search([('create_date', '<', cutoff_date)])
        count = len(old_logs)
        old_logs.unlink()
        return count
