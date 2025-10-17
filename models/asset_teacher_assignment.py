# -*- coding: utf-8 -*-

import base64
import secrets
import logging
import hmac
import hashlib
from datetime import timedelta
from typing import Tuple
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class AssetTeacherAssignment(models.Model):
    """Teacher Asset Assignment Model"""
    _name = 'asset.teacher.assignment'
    _description = 'Teacher Asset Assignment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'checkout_date desc'

    name = fields.Char(
        string='Reference',
        compute='_compute_name',
        store=True,
        help='Assignment reference name'
    )
    assignment_type = fields.Selection(
        [('teacher', 'Teacher')],
        default='teacher',
        required=True,
        string='Type'
    )
    teacher_id = fields.Many2one(
        'hr.employee',
        string='Teacher',
        required=True,
        tracking=True,
        index=True,
        help='Teacher receiving the assets'
    )

    # Dates
    checkout_date = fields.Date(
        string='Checkout Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        help='Date when assets were checked out'
    )
    return_type = fields.Selection([
        ('end_of_term', 'End of Term'),
        ('end_of_year', 'End of Academic Year'),
        ('specific_date', 'Specific Date'),
        ('permanent', 'Permanent Assignment'),
    ], string='Return Type', default='end_of_term', required=True, tracking=True,
        help='When should the asset be returned')
    expected_return_date = fields.Date(
        string='Expected Return Date',
        tracking=True,
        help='Expected date for return (required if Return Type is Specific Date)'
    )
    actual_return_date = fields.Date(
        string='Actual Return Date',
        tracking=True,
        help='Actual date when assets were returned'
    )

    # Status
    status = fields.Selection([
        ('draft', 'Draft'),
        ('checked_out', 'Checked Out'),
        ('checked_in', 'Checked In'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True,
        help='Assignment status')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('checked_out', 'Checked Out'),
        ('inspected', 'Inspected'),
        ('checked_in', 'Checked In'),
    ], string='State', default='draft', tracking=True)

    # Asset Lines
    asset_line_ids = fields.One2many(
        'asset.assignment.line',
        'assignment_id',
        string='Assets',
        help='List of assets in this assignment'
    )

    # Signatures
    checkout_teacher_signature = fields.Binary(
        string='Teacher Signature (Checkout)',
        attachment=False,  # Store in database, not as attachment
        help='Teacher signature confirming asset receipt (ORIGINAL - DO NOT DISPLAY)'
    )
    checkout_teacher_signature_watermarked = fields.Binary(
        string='Teacher Signature (Watermarked)',
        compute='_compute_watermarked_signatures',
        help='Watermarked signature for display purposes only'
    )
    checkout_sign_date = fields.Datetime(
        string='Teacher Sign Date',
        readonly=True,
        help='Date and time when teacher signed'
    )
    checkout_ip_address = fields.Char(
        string='IP Address (Checkout)',
        readonly=True,
        help='IP address from which teacher signed'
    )

    # Checkout Token Management
    checkout_token = fields.Char(
        string='Checkout Token',
        readonly=True,
        copy=False,
        index=True,
        help='Unique token for checkout signature link'
    )
    checkout_token_expiry = fields.Datetime(
        string='Token Expiry',
        readonly=True,
        help='Checkout token expiration date'
    )
    checkout_token_used = fields.Boolean(
        string='Token Used',
        default=False,
        readonly=True,
        help='Whether checkout token has been used'
    )

    # Signed Checkout Document
    checkout_signed_pdf_id = fields.Many2one(
        'ir.attachment',
        string='Signed Checkout Waiver PDF',
        readonly=True,
        help='Generated PDF after teacher signs checkout waiver'
    )

    checkin_it_signature = fields.Binary(
        string='IT Signature (Check-in)',
        help='IT staff signature confirming asset return inspection'
    )
    checkin_it_user_id = fields.Many2one(
        'res.users',
        string='IT Staff (Check-in)',
        readonly=True,
        help='IT staff who inspected and signed check-in'
    )
    checkin_sign_date = fields.Datetime(
        string='IT Sign Date',
        readonly=True,
        help='Date and time when IT staff signed'
    )

    # Damage Report Token Management
    damage_report_sent = fields.Boolean(
        string='Damage Report Sent',
        default=False,
        readonly=True,
        help='Whether damage report has been sent to teacher'
    )
    damage_report_token = fields.Char(
        string='Damage Token',
        readonly=True,
        copy=False,
        index=True,
        help='Unique token for damage report signature link'
    )
    damage_report_token_expiry = fields.Datetime(
        string='Damage Token Expiry',
        readonly=True,
        help='Damage report token expiration date'
    )
    damage_report_token_used = fields.Boolean(
        string='Damage Token Used',
        default=False,
        readonly=True,
        help='Whether damage token has been used'
    )
    damage_acknowledged = fields.Boolean(
        string='Damage Acknowledged',
        default=False,
        readonly=True,
        help='Whether teacher has acknowledged damage'
    )
    damage_acknowledge_date = fields.Datetime(
        string='Acknowledgment Date',
        readonly=True,
        help='Date when teacher acknowledged damage'
    )
    damage_signature = fields.Binary(
        string='Teacher Damage Signature',
        attachment=False,  # Store in database, not as attachment
        help='Teacher signature acknowledging damage and repair costs (ORIGINAL - DO NOT DISPLAY)'
    )
    damage_signature_watermarked = fields.Binary(
        string='Teacher Damage Signature (Watermarked)',
        compute='_compute_watermarked_signatures',
        help='Watermarked signature for display purposes only'
    )
    damage_acknowledge_ip = fields.Char(
        string='IP Address (Damage)',
        readonly=True,
        help='IP address from which teacher acknowledged damage'
    )

    # Signed Damage Document
    damage_signed_pdf_id = fields.Many2one(
        'ir.attachment',
        string='Signed Damage Report PDF',
        readonly=True,
        help='Generated PDF after teacher signs damage acknowledgment'
    )

    # Additional Info
    notes = fields.Text(
        string='Notes',
        help='Additional notes or comments'
    )

    # Computed Fields
    has_damage = fields.Boolean(
        compute='_compute_has_damage',
        store=True,
        help='True if any asset line has damage found'
    )
    asset_count = fields.Integer(
        compute='_compute_asset_count',
        string='Asset Count'
    )
    is_overdue = fields.Boolean(
        compute='_compute_is_overdue',
        store=True,
        string='Overdue',
        help='True if expected return date has passed'
    )
    days_overdue = fields.Integer(
        compute='_compute_is_overdue',
        store=True,
        string='Days Overdue'
    )
    checkout_signature_status = fields.Selection([
        ('not_sent', 'Not Sent'),
        ('pending', 'Waiting for Signature'),
        ('signed', 'Signed'),
        ('expired', 'Link Expired'),
    ], compute='_compute_checkout_signature_status', string='Signature Status', store=True)
    teacher_email = fields.Char(
        related='teacher_id.work_email',
        string='Teacher Email',
        readonly=True,
        help='Teacher work email address'
    )

    # Damage Cases
    damage_case_ids = fields.One2many(
        'asset.damage.case',
        'teacher_assignment_id',
        string='Damage Cases',
        help='Damage cases created from this assignment'
    )
    damage_case_count = fields.Integer(
        string='Damage Cases',
        compute='_compute_damage_case_count',
        help='Number of damage cases created'
    )

    @api.depends('teacher_id', 'checkout_date')
    def _compute_name(self):
        """Generate assignment name"""
        for record in self:
            if record.teacher_id and record.checkout_date:
                record.name = f"{record.teacher_id.name} - {record.checkout_date}"
            else:
                record.name = _('New Assignment')

    @api.depends('asset_line_ids.damage_found')
    def _compute_has_damage(self):
        """Check if any asset has damage"""
        for record in self:
            record.has_damage = any(line.damage_found for line in record.asset_line_ids)

    @api.depends('asset_line_ids')
    def _compute_asset_count(self):
        """Count assets in assignment"""
        for record in self:
            record.asset_count = len(record.asset_line_ids)

    @api.depends('damage_case_ids')
    def _compute_damage_case_count(self):
        """Count damage cases created from this assignment"""
        for record in self:
            record.damage_case_count = len(record.damage_case_ids)

    @api.depends('expected_return_date', 'status', 'return_type')
    def _compute_is_overdue(self):
        """Check if assignment is overdue"""
        today = fields.Date.today()
        for record in self:
            # Only check overdue for specific_date type with checked_out status
            if record.status == 'checked_out' and record.return_type == 'specific_date' and record.expected_return_date:
                if record.expected_return_date < today:
                    record.is_overdue = True
                    record.days_overdue = (today - record.expected_return_date).days
                else:
                    record.is_overdue = False
                    record.days_overdue = 0
            else:
                record.is_overdue = False
                record.days_overdue = 0

    @api.depends('checkout_token', 'checkout_token_expiry', 'checkout_token_used')
    def _compute_checkout_signature_status(self):
        """Compute checkout signature status"""
        for record in self:
            if not record.checkout_token:
                record.checkout_signature_status = 'not_sent'
            elif record.checkout_token_used:
                record.checkout_signature_status = 'signed'
            elif record.checkout_token_expiry and record.checkout_token_expiry < fields.Datetime.now():
                record.checkout_signature_status = 'expired'
            else:
                record.checkout_signature_status = 'pending'

    def _compute_watermarked_signatures(self):
        """
        Generate watermarked versions of signatures for display
        SECURITY: Original signatures are protected, only watermarked versions shown to staff
        """
        from . import signature_watermark

        for record in self:
            # Watermark checkout signature
            if record.checkout_teacher_signature:
                record.checkout_teacher_signature_watermarked = signature_watermark.add_watermark_to_signature(
                    record.checkout_teacher_signature,
                    watermark_text="SCHOOL USE ONLY",
                    reference_number=record.name or '',
                    timestamp=record.checkout_sign_date
                )
            else:
                record.checkout_teacher_signature_watermarked = False

            # Watermark damage signature
            if record.damage_signature:
                record.damage_signature_watermarked = signature_watermark.add_watermark_to_signature(
                    record.damage_signature,
                    watermark_text="SCHOOL USE ONLY - DAMAGE REPORT",
                    reference_number=record.name or '',
                    timestamp=record.damage_acknowledge_date
                )
            else:
                record.damage_signature_watermarked = False

    @api.constrains('checkout_date', 'expected_return_date', 'return_type')
    def _check_dates(self):
        """Validate dates"""
        for record in self:
            # Require expected_return_date if return_type is specific_date
            if record.return_type == 'specific_date' and not record.expected_return_date:
                raise ValidationError(_(
                    'Expected Return Date is required when Return Type is "Specific Date".'
                ))
            # Validate date order
            if record.expected_return_date and record.expected_return_date < record.checkout_date:
                raise ValidationError(_(
                    'Expected return date cannot be before checkout date.'
                ))

    def action_checkout(self):
        """Process checkout - change status and update asset status"""
        self.ensure_one()
        if not self.asset_line_ids:
            raise UserError(_('Please add at least one asset before checking out.'))

        # Require teacher signature for checkout
        if not self.checkout_teacher_signature:
            raise UserError(_('Teacher signature is required for checkout.'))

        # Update asset status
        for line in self.asset_line_ids:
            line.asset_id.write({
                'status': 'assigned_teacher',
                'custodian_id': self.teacher_id.id,
            })

        self.write({
            'status': 'checked_out',
            'state': 'checked_out',
            'checkout_sign_date': fields.Datetime.now(),
        })

        # Send email notification
        self._send_checkout_email()

    def action_checkin(self):
        """Process check-in - validate and change status"""
        self.ensure_one()

        # Require IT signature for check-in
        if not self.checkin_it_signature:
            raise UserError(_('IT staff signature is required for check-in.'))

        # Check if all assets have check-in condition documented
        for line in self.asset_line_ids:
            if not line.checkin_condition:
                raise UserError(_(
                    'Please document the check-in condition for all assets.'
                ))

        # Update asset status
        for line in self.asset_line_ids:
            line.asset_id.write({
                'status': 'available',
                'custodian_id': False,
                'condition_rating': line.checkin_condition,
            })

        self.write({
            'status': 'checked_in',
            'state': 'checked_in',
            'actual_return_date': fields.Date.today(),
            'checkin_it_user_id': self.env.user.id,
            'checkin_sign_date': fields.Datetime.now(),
        })

        # Send email notification
        self._send_checkin_email()

    def action_cancel(self):
        """Cancel assignment"""
        self.ensure_one()
        if self.status == 'checked_out':
            raise UserError(_('Cannot cancel a checked-out assignment. Please check in first.'))

        self.write({'status': 'cancelled'})

    def action_view_assets(self):
        """View assets in this assignment"""
        self.ensure_one()
        asset_ids = self.asset_line_ids.mapped('asset_id').ids
        return {
            'name': _('Assets'),
            'type': 'ir.actions.act_window',
            'res_model': 'asset.asset',
            'view_mode': 'list,form',
            'domain': [('id', 'in', asset_ids)],
        }

    def action_view_damage_cases(self):
        """View damage cases created from this assignment"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Damage Cases'),
            'res_model': 'asset.damage.case',
            'domain': [('teacher_assignment_id', '=', self.id)],
            'view_mode': 'list,form',
            'context': {'default_teacher_assignment_id': self.id},
        }

    def action_create_damage_case(self):
        """Create damage case from teacher check-in with damage"""
        self.ensure_one()

        # Find damaged assets
        damaged_lines = self.asset_line_ids.filtered(lambda l: l.damage_found)
        if not damaged_lines:
            raise UserError(_('No damaged assets found in this check-in.'))

        # If only one damaged asset, create case directly
        if len(damaged_lines) == 1:
            line = damaged_lines[0]
            vals = {
                'damage_source': 'checkin_teacher',
                'teacher_assignment_id': self.id,
                'asset_id': line.asset_id.id,
                'damage_description': line.damage_description or '',
                'damage_date': self.actual_return_date or fields.Date.today(),
                'reported_by': self.checkin_it_user_id.id or self.env.user.id,
                'estimated_cost': line.repair_cost or 0.0,
                'responsible_type': 'teacher',
                'responsible_teacher_id': self.teacher_id.id,
            }

            damage_case = self.env['asset.damage.case'].create(vals)

            # Copy photos
            if line.checkin_photo_ids:
                damage_case.write({'photo_ids': [(6, 0, line.checkin_photo_ids.ids)]})

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'asset.damage.case',
                'res_id': damage_case.id,
                'view_mode': 'form',
                'target': 'current',
            }

        # Multiple damaged assets - show selection wizard or create multiple cases
        # For now, create first one and show message
        else:
            raise UserError(_(
                'Multiple damaged assets found. Please create damage cases individually from the Asset Lines tab.'
            ))

    def _send_checkout_email(self):
        """Send checkout confirmation email"""
        template = self.env.ref(
            'school_asset_management.email_template_teacher_checkout',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_checkin_email(self):
        """Send check-in confirmation email"""
        template = self.env.ref(
            'school_asset_management.email_template_teacher_checkin',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=True)

    # ========== Teacher Signature Methods ==========

    def _generate_hmac_token(self, token_type: str = 'checkout') -> Tuple[str, str]:
        """Generate HMAC-SHA256 token for signature requests.

        Args:
            token_type: Type of token ('checkout', 'damage', 'approval')

        Returns:
            Tuple[str, str]: (token, expiry_datetime)

        Security:
            - Uses HMAC-SHA256 for tamper-proof tokens
            - Secret key stored in ir.config_parameter
            - Includes record ID, timestamp, and random salt
        """
        self.ensure_one()

        # Get secret key from config (auto-generated on install)
        secret_key = self.env['ir.config_parameter'].sudo().get_param(
            'school_asset.signature_secret',
            default='fallback_secret_DO_NOT_USE_IN_PRODUCTION'
        )

        if secret_key == 'fallback_secret_DO_NOT_USE_IN_PRODUCTION':
            _logger.warning('Using fallback secret key! Generate a proper one in System Parameters.')

        # Get expiry days from config
        expiry_param_map = {
            'checkout': 'school_asset.checkout_token_expiry_days',
            'damage': 'school_asset.damage_token_expiry_days',
            'approval': 'school_asset.approval_token_expiry_days',
        }
        expiry_days = int(self.env['ir.config_parameter'].sudo().get_param(
            expiry_param_map.get(token_type, 'school_asset.checkout_token_expiry_days'),
            default='7'
        ))

        # Generate timestamp and salt
        timestamp = str(int(fields.Datetime.now().timestamp()))
        salt = secrets.token_hex(16)

        # Create message: record_id|timestamp|salt|token_type
        message = f"{self.id}|{timestamp}|{salt}|{token_type}"

        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # Token format: message.signature (URL-safe)
        token = f"{message}.{signature}"

        # Calculate expiry
        expiry = fields.Datetime.now() + timedelta(days=expiry_days)

        return token, expiry

    def _verify_hmac_token(self, token: str, token_type: str = 'checkout') -> Tuple[bool, str]:
        """Verify HMAC-SHA256 token integrity.

        Args:
            token: Token string to verify
            token_type: Expected token type

        Returns:
            Tuple[bool, str]: (is_valid, error_message)
                - is_valid: True if token is valid
                - error_message: 'valid', 'invalid', 'expired', 'used', 'tampered'
        """
        self.ensure_one()

        try:
            # Split token into message and signature
            if '.' not in token:
                return False, 'invalid'

            message, received_signature = token.rsplit('.', 1)

            # Parse message: record_id|timestamp|salt|token_type
            parts = message.split('|')
            if len(parts) != 4:
                return False, 'invalid'

            record_id, timestamp, salt, msg_token_type = parts

            # Verify record ID matches
            if int(record_id) != self.id:
                _logger.warning(f'Token record ID mismatch: expected {self.id}, got {record_id}')
                return False, 'invalid'

            # Verify token type matches
            if msg_token_type != token_type:
                _logger.warning(f'Token type mismatch: expected {token_type}, got {msg_token_type}')
                return False, 'invalid'

            # Get secret key
            secret_key = self.env['ir.config_parameter'].sudo().get_param(
                'school_asset.signature_secret',
                default='fallback_secret_DO_NOT_USE_IN_PRODUCTION'
            )

            # Calculate expected signature
            expected_signature = hmac.new(
                secret_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            # Constant-time comparison to prevent timing attacks
            if not secrets.compare_digest(received_signature, expected_signature):
                _logger.warning(f'HMAC signature verification failed for record {self.id}')
                return False, 'tampered'

            return True, 'valid'

        except Exception as e:
            _logger.error(f'Error verifying HMAC token: {e}')
            return False, 'invalid'

    def action_send_checkout_signature_request(self):
        """Generate HMAC token and send checkout signature request email to teacher"""
        self.ensure_one()
        if not self.teacher_email:
            raise UserError(_('Teacher email is required to send signature request.'))

        # Generate HMAC token (7 days expiry)
        token, expiry = self._generate_hmac_token('checkout')

        self.write({
            'checkout_token': token,
            'checkout_token_expiry': expiry,
            'checkout_token_used': False,
        })

        # Send email
        template = self.env.ref(
            'school_asset_management.email_template_teacher_checkout_signature_request',
            raise_if_not_found=False
        )
        if template:
            mail_id = template.send_mail(
                self.id,
                force_send=False,
                email_values={'email_to': self.teacher_email}
            )
            if mail_id:
                mail = self.env['mail.mail'].sudo().browse(mail_id)
                if mail.exists():
                    mail.send()

            self.message_post(
                body=_('Checkout signature request sent to %s') % self.teacher_email
            )
        else:
            raise UserError(_('Email template not found. Please contact administrator.'))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Signature Request Sent'),
                'message': _('Email sent to %s. Link expires in 7 days.') % self.teacher_email,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_resend_checkout_signature_request(self):
        """Resend checkout signature request with new token"""
        return self.action_send_checkout_signature_request()

    def action_send_damage_report(self):
        """Generate HMAC token and send damage report email to teacher"""
        self.ensure_one()
        if not self.has_damage:
            raise UserError(_('No damage found. Cannot send damage report.'))
        if not self.teacher_email:
            raise UserError(_('Teacher email is required to send damage report.'))

        # Generate HMAC token (3 days expiry - shorter for damage reports)
        token, expiry = self._generate_hmac_token('damage')

        self.write({
            'damage_report_token': token,
            'damage_report_token_expiry': expiry,
            'damage_report_token_used': False,
            'damage_report_sent': True,
        })

        # Send email
        template = self.env.ref(
            'school_asset_management.email_template_teacher_damage_report',
            raise_if_not_found=False
        )
        if template:
            mail_id = template.send_mail(
                self.id,
                force_send=False,
                email_values={'email_to': self.teacher_email}
            )
            if mail_id:
                mail = self.env['mail.mail'].sudo().browse(mail_id)
                if mail.exists():
                    mail.send()

            self.message_post(
                body=_('⚠️ Damage report sent to %s') % self.teacher_email
            )
        else:
            raise UserError(_('Email template not found. Please contact administrator.'))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Damage Report Sent'),
                'message': _('Email sent to %s. Link expires in 7 days.') % self.teacher_email,
                'type': 'warning',
                'sticky': False,
            }
        }

    def action_resend_damage_report(self):
        """Resend damage report with new token"""
        return self.action_send_damage_report()

    def action_view_checkout_pdf(self):
        """View signed checkout waiver PDF"""
        self.ensure_one()
        if not self.checkout_signed_pdf_id:
            raise UserError(_('Signed checkout waiver PDF not found.'))

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % self.checkout_signed_pdf_id.id,
            'target': 'new',
        }

    def action_view_damage_pdf(self):
        """View signed damage report PDF"""
        self.ensure_one()
        if not self.damage_signed_pdf_id:
            raise UserError(_('Signed damage report PDF not found.'))

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % self.damage_signed_pdf_id.id,
            'target': 'new',
        }

    def action_copy_checkout_link(self):
        """Copy checkout signature link to clipboard"""
        self.ensure_one()
        if not self.checkout_token:
            raise UserError(_('Please send signature request first to generate link.'))

        # Get base URL
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        link = f"{base_url}/sign/teacher/checkout/{self.checkout_token}"
        expiry = self.checkout_token_expiry.strftime('%Y-%m-%d %H:%M') if self.checkout_token_expiry else 'N/A'

        # Return client action to auto-copy to clipboard
        return {
            'type': 'ir.actions.client',
            'tag': 'copy_signature_link',
            'params': {
                'link': link,
                'expiry': expiry,
            }
        }

    def action_copy_damage_link(self):
        """Copy damage report link to clipboard"""
        self.ensure_one()
        if not self.damage_report_token:
            raise UserError(_('Please send damage report first to generate link.'))

        # Get base URL
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        link = f"{base_url}/sign/teacher/damage/{self.damage_report_token}"
        expiry = self.damage_report_token_expiry.strftime('%Y-%m-%d %H:%M') if self.damage_report_token_expiry else 'N/A'

        # Return client action to auto-copy to clipboard
        return {
            'type': 'ir.actions.client',
            'tag': 'copy_signature_link',
            'params': {
                'link': link,
                'expiry': expiry,
            }
        }

    # ========== Helper Methods (Token Validation & Signature Saving) ==========

    def _validate_token(self, token, token_type='checkout'):
        """Validate token - check HMAC signature, expiration, and usage status.

        Security:
            - HMAC-SHA256 signature verification
            - Constant-time comparison to prevent timing attacks
            - Checks expiration time
            - Prevents token reuse

        Args:
            token: Token string to validate
            token_type: 'checkout' or 'damage'

        Returns:
            str: 'valid', 'used', 'expired', 'tampered', or 'invalid'
        """
        self.ensure_one()

        if token_type == 'checkout':
            stored_token = self.checkout_token
            token_used = self.checkout_token_used
            token_expiry = self.checkout_token_expiry
        else:  # damage
            stored_token = self.damage_report_token
            token_used = self.damage_report_token_used
            token_expiry = self.damage_report_token_expiry

        # Check if token exists and matches (constant-time comparison)
        if not stored_token or not secrets.compare_digest(stored_token, token):
            _logger.warning(f'Token mismatch for {token_type} on record {self.id}')
            return 'invalid'

        # Check if already used
        if token_used:
            _logger.warning(f'Token already used for {token_type} on record {self.id}')
            return 'used'

        # Check expiration
        if token_expiry and token_expiry < fields.Datetime.now():
            _logger.warning(f'Token expired for {token_type} on record {self.id}')
            return 'expired'

        # Verify HMAC signature integrity
        is_valid_hmac, hmac_error = self._verify_hmac_token(token, token_type)
        if not is_valid_hmac:
            _logger.warning(f'HMAC verification failed: {hmac_error} for {token_type} on record {self.id}')
            # Log security event
            self.env['security_audit_log'].sudo().create({
                'event_type': f'token_{hmac_error}',
                'details': f'Token {hmac_error} for {token_type} signature on record {self.id}',
                'severity': 'warning',
            })
            return hmac_error

        return 'valid'

    def _save_checkout_signature(self, signature_data, ip_address):
        """Save checkout signature and generate PDF"""
        self.ensure_one()

        try:
            # Save signature and mark token as used in ONE operation to avoid race conditions
            self.write({
                'checkout_teacher_signature': signature_data,
                'checkout_sign_date': fields.Datetime.now(),
                'checkout_ip_address': ip_address,
                'checkout_token_used': True,
            })

            # Flush to database to ensure data is committed before PDF generation
            self.flush_recordset()

            # Generate PDF
            pdf_content = self._generate_checkout_waiver_pdf()

            # Send confirmation email
            template = self.env.ref(
                'school_asset_management.email_template_teacher_checkout_confirmation',
                raise_if_not_found=False
            )
            if template:
                mail_id = template.send_mail(
                    self.id,
                    force_send=False,
                    email_values={'email_to': self.teacher_email}
                )
                if mail_id:
                    mail = self.env['mail.mail'].sudo().browse(mail_id)
                    if mail.exists():
                        mail.send()

            # Log in chatter
            self.message_post(
                body=_('✅ Teacher signature received from %s on %s (IP: %s)') % (
                    self.teacher_id.name,
                    self.checkout_sign_date.strftime('%Y-%m-%d %H:%M:%S'),
                    ip_address
                )
            )
        except Exception as e:
            # Rollback signature if PDF generation fails
            self.write({
                'checkout_teacher_signature': False,
                'checkout_sign_date': False,
                'checkout_ip_address': False,
            })
            raise

    def _save_damage_signature(self, signature_data, ip_address):
        """Save damage signature and generate PDF"""
        self.ensure_one()

        # Save signature - Binary field expects base64 string
        self.write({
            'damage_signature': signature_data,
            'damage_acknowledged': True,
            'damage_acknowledge_date': fields.Datetime.now(),
            'damage_acknowledge_ip': ip_address,
        })

        # Flush to database to ensure data is committed before PDF generation
        self.flush_recordset()

        try:
            # Generate PDF
            pdf_content = self._generate_damage_report_pdf()

            # Send confirmation email
            template = self.env.ref(
                'school_asset_management.email_template_teacher_damage_acknowledgment',
                raise_if_not_found=False
            )
            if template:
                mail_id = template.send_mail(
                    self.id,
                    force_send=False,
                    email_values={'email_to': self.teacher_email}
                )
                if mail_id:
                    mail = self.env['mail.mail'].sudo().browse(mail_id)
                    if mail.exists():
                        mail.send()

            # Mark token as used only after successful PDF generation
            self.write({'damage_report_token_used': True})

            # Log in chatter
            self.message_post(
                body=_('⚠️ Damage acknowledged by %s on %s (IP: %s)') % (
                    self.teacher_id.name,
                    self.damage_acknowledge_date.strftime('%Y-%m-%d %H:%M:%S'),
                    ip_address
                )
            )
        except Exception as e:
            # Rollback signature if PDF generation fails
            self.write({
                'damage_signature': False,
                'damage_acknowledged': False,
                'damage_acknowledge_date': False,
                'damage_acknowledge_ip': False,
            })
            raise

    def _generate_checkout_waiver_pdf(self):
        """Generate signed checkout waiver PDF and attach to record"""
        self.ensure_one()

        # Delete old PDF attachment if exists
        if self.checkout_signed_pdf_id:
            self.checkout_signed_pdf_id.sudo().unlink()

        # Generate PDF using report
        report_action = self.env.ref('school_asset_management.action_report_teacher_checkout_waiver')
        pdf_content, _ = report_action.sudo()._render_qweb_pdf('school_asset_management.report_teacher_checkout_waiver', res_ids=self.ids)

        # Create attachment
        attachment = self.env['ir.attachment'].sudo().create({
            'name': f'Teacher_Checkout_Waiver_{self.name}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        self.write({'checkout_signed_pdf_id': attachment.id})

        return pdf_content

    def _generate_damage_report_pdf(self):
        """Generate signed damage report PDF and attach to record"""
        self.ensure_one()

        # Delete old PDF attachment if exists
        if self.damage_signed_pdf_id:
            self.damage_signed_pdf_id.sudo().unlink()

        # Generate PDF using report
        report_action = self.env.ref('school_asset_management.action_report_teacher_damage_acknowledgment')
        pdf_content, _ = report_action.sudo()._render_qweb_pdf('school_asset_management.report_teacher_damage_acknowledgment', res_ids=self.ids)

        # Create attachment
        attachment = self.env['ir.attachment'].sudo().create({
            'name': f'Teacher_Damage_Report_{self.name}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        self.write({'damage_signed_pdf_id': attachment.id})

        return pdf_content


class AssetAssignmentLine(models.Model):
    """Asset Assignment Line"""
    _name = 'asset.assignment.line'
    _description = 'Asset Assignment Line'
    _order = 'id'

    assignment_id = fields.Many2one(
        'asset.teacher.assignment',
        string='Assignment',
        required=True,
        ondelete='cascade',
        index=True
    )
    asset_id = fields.Many2one(
        'asset.asset',
        string='Asset',
        required=True,
        domain=[('status', '=', 'available')],
        index=True
    )

    # Checkout Information
    checkout_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('broken', 'Broken/Damaged'),
    ], string='Checkout Condition', help='Asset condition at checkout')
    checkout_notes = fields.Text(string='Checkout Notes')
    checkout_photo_ids = fields.Many2many(
        'ir.attachment',
        'asset_line_checkout_photo_rel',
        'line_id',
        'attachment_id',
        string='Checkout Photos'
    )

    # Check-in Information
    checkin_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('broken', 'Broken/Damaged'),
    ], string='Check-in Condition', help='Asset condition at check-in')
    checkin_notes = fields.Text(string='Check-in Notes')
    checkin_photo_ids = fields.Many2many(
        'ir.attachment',
        'asset_line_checkin_photo_rel',
        'line_id',
        'attachment_id',
        string='Check-in Photos'
    )

    # Damage Information
    damage_found = fields.Boolean(
        string='Damage Found',
        help='Check if damage was found during check-in'
    )
    damage_description = fields.Text(string='Damage Description')
    repair_cost = fields.Float(
        string='Repair Cost',
        digits='Product Price'
    )

    # Related Fields for Display
    asset_code = fields.Char(related='asset_id.asset_code', string='Asset Code', readonly=True)
    asset_name = fields.Char(related='asset_id.name', string='Asset Name', readonly=True)
    asset_category = fields.Char(related='asset_id.category_id.name', string='Category', readonly=True)

    @api.onchange('checkin_condition', 'checkout_condition')
    def _onchange_condition(self):
        """Auto-flag damage if condition worsened"""
        if self.checkin_condition and self.checkout_condition:
            condition_order = {'excellent': 4, 'good': 3, 'fair': 2, 'poor': 1}
            checkout_val = condition_order.get(self.checkout_condition, 0)
            checkin_val = condition_order.get(self.checkin_condition, 0)

            if checkin_val < checkout_val:
                self.damage_found = True
