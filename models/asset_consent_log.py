# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AssetConsentLog(models.Model):
    """
    PDPA Compliance: Consent Management Log

    This model tracks all consent records for personal data collection and processing
    as required by PDPA (Personal Data Protection Act) Section 19

    Records:
    - Data collection consent
    - Digital signature consent
    - Email communication consent
    - Marketing consent (if applicable)
    """
    _name = 'asset.consent.log'
    _description = 'PDPA Consent Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'consent_date desc'
    _rec_name = 'consent_reference'

    consent_reference = fields.Char(
        string='Consent Reference',
        required=True,
        readonly=True,
        default='New',
        copy=False,
        help='Unique reference for this consent record'
    )

    # Consent Type
    consent_type = fields.Selection([
        ('data_collection', 'Personal Data Collection'),
        ('digital_signature', 'Digital Signature'),
        ('email_communication', 'Email Communication'),
        ('damage_liability', 'Damage Liability Agreement'),
        ('all', 'All of the Above'),
    ], string='Consent Type', required=True, index=True,
        help='Type of consent given by data subject')

    # Data Subject Information
    user_type = fields.Selection([
        ('parent', 'Parent/Guardian'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    ], string='User Type', required=True, index=True,
        help='Type of data subject giving consent')

    # Related Records
    student_assignment_id = fields.Many2one(
        'asset.student.assignment',
        string='Student Assignment',
        ondelete='cascade',
        index=True,
        help='Related student assignment if applicable'
    )
    teacher_assignment_id = fields.Many2one(
        'asset.teacher.assignment',
        string='Teacher Assignment',
        ondelete='cascade',
        index=True,
        help='Related teacher assignment if applicable'
    )

    # Personal Information (for tracking purposes only)
    data_subject_name = fields.Char(
        string='Data Subject Name',
        required=True,
        index=True,
        help='Name of person giving consent'
    )
    data_subject_email = fields.Char(
        string='Email Address',
        required=True,
        index=True,
        help='Email address of data subject'
    )

    # Consent Details
    consent_given = fields.Boolean(
        string='Consent Given',
        default=True,
        required=True,
        help='Whether consent was given (True) or withdrawn (False)'
    )
    consent_date = fields.Datetime(
        string='Consent Date/Time',
        required=True,
        default=fields.Datetime.now,
        index=True,
        help='Date and time when consent was given'
    )
    consent_method = fields.Selection([
        ('online', 'Online Form'),
        ('paper', 'Paper Form'),
        ('verbal', 'Verbal (Recorded)'),
        ('automatic', 'Automatic (System Generated)'),
    ], string='Consent Method', default='online', required=True,
        help='How was consent obtained')

    # Privacy Policy Version
    privacy_policy_version = fields.Char(
        string='Privacy Policy Version',
        required=True,
        default='1.0',
        help='Version of privacy policy that user consented to'
    )
    terms_version = fields.Char(
        string='Terms & Conditions Version',
        default='1.0',
        help='Version of terms and conditions'
    )

    # Audit Trail
    ip_address = fields.Char(
        string='IP Address',
        help='IP address from which consent was given'
    )
    user_agent = fields.Text(
        string='User Agent',
        help='Browser/device information'
    )

    # Withdrawal Information
    consent_withdrawn = fields.Boolean(
        string='Consent Withdrawn',
        default=False,
        help='Whether consent has been withdrawn'
    )
    withdrawal_date = fields.Datetime(
        string='Withdrawal Date',
        readonly=True,
        help='Date when consent was withdrawn'
    )
    withdrawal_reason = fields.Text(
        string='Withdrawal Reason',
        help='Reason for withdrawing consent'
    )

    # Expiration
    consent_expiry_date = fields.Date(
        string='Consent Expiry Date',
        help='Date when consent expires (if applicable)'
    )
    is_expired = fields.Boolean(
        string='Expired',
        compute='_compute_is_expired',
        store=True,
        help='Whether this consent has expired'
    )

    # PDPA Specific Fields
    purpose_of_collection = fields.Text(
        string='Purpose of Data Collection',
        help='Specific purpose for which personal data is collected'
    )
    data_categories = fields.Text(
        string='Data Categories',
        default='Name, Email, Digital Signature, IP Address',
        help='Categories of personal data being collected'
    )

    # Notes
    notes = fields.Text(
        string='Additional Notes',
        help='Any additional information about this consent'
    )

    # Active/Inactive
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether this consent is currently active'
    )

    # Computed Fields
    is_valid = fields.Boolean(
        string='Valid Consent',
        compute='_compute_is_valid',
        store=True,
        help='Whether this consent is currently valid'
    )
    legal_basis = fields.Char(
        string='Legal Basis',
        default='Consent (PDPA Section 19)',
        help='Legal basis for processing personal data'
    )
    retention_period_years = fields.Integer(
        string='Retention Period (Years)',
        default=7,
        help='Number of years to retain consent records'
    )
    consent_evidence = fields.Text(
        string='Consent Evidence',
        help='Evidence that consent was given (e.g., screenshot, form data)'
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Generate unique consent reference number"""
        for vals in vals_list:
            if vals.get('consent_reference', 'New') == 'New':
                vals['consent_reference'] = self.env['ir.sequence'].next_by_code('asset.consent.log') or 'New'
        return super().create(vals_list)

    @api.depends('consent_expiry_date', 'consent_withdrawn')
    def _compute_is_expired(self):
        """Check if consent has expired"""
        today = fields.Date.today()
        for record in self:
            if record.consent_withdrawn:
                record.is_expired = True
            elif record.consent_expiry_date and record.consent_expiry_date < today:
                record.is_expired = True
            else:
                record.is_expired = False

    @api.depends('consent_given', 'consent_withdrawn', 'is_expired')
    def _compute_is_valid(self):
        """Check if consent is currently valid"""
        for record in self:
            record.is_valid = (record.consent_given and
                              not record.consent_withdrawn and
                              not record.is_expired)

    def action_withdraw_consent(self):
        """
        Withdraw consent - PDPA Right to Withdraw Consent

        This allows data subjects to withdraw their consent at any time
        as required by PDPA Section 19
        """
        self.ensure_one()

        if self.consent_withdrawn:
            raise ValidationError(_('Consent has already been withdrawn.'))

        return {
            'name': _('Withdraw Consent'),
            'type': 'ir.actions.act_window',
            'res_model': 'asset.consent.withdrawal.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_consent_log_id': self.id,
            }
        }

    def _withdraw_consent(self, reason=''):
        """Internal method to withdraw consent"""
        self.ensure_one()
        self.write({
            'consent_withdrawn': True,
            'consent_given': False,
            'withdrawal_date': fields.Datetime.now(),
            'withdrawal_reason': reason,
            'active': False,
        })

    @api.model
    def log_consent(self, consent_type, user_type, data_subject_name, data_subject_email,
                    ip_address=None, user_agent=None, privacy_version='1.0',
                    student_assignment_id=None, teacher_assignment_id=None,
                    purpose='', consent_method='online'):
        """
        Helper method to create consent log entry

        Args:
            consent_type: Type of consent (data_collection, digital_signature, etc.)
            user_type: Type of user (parent, teacher, student)
            data_subject_name: Name of person giving consent
            data_subject_email: Email address
            ip_address: IP address (optional)
            user_agent: Browser/device info (optional)
            privacy_version: Privacy policy version
            student_assignment_id: Related student assignment (optional)
            teacher_assignment_id: Related teacher assignment (optional)
            purpose: Purpose of data collection
            consent_method: How consent was obtained

        Returns:
            Created consent log record
        """
        vals = {
            'consent_type': consent_type,
            'user_type': user_type,
            'data_subject_name': data_subject_name,
            'data_subject_email': data_subject_email,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'privacy_policy_version': privacy_version,
            'student_assignment_id': student_assignment_id,
            'teacher_assignment_id': teacher_assignment_id,
            'purpose_of_collection': purpose,
            'consent_method': consent_method,
            'consent_given': True,
        }

        return self.create(vals)

    @api.model
    def get_active_consent(self, email, consent_type):
        """
        Get active consent for a data subject

        Args:
            email: Email address of data subject
            consent_type: Type of consent to check

        Returns:
            Active consent record or False
        """
        return self.search([
            ('data_subject_email', '=', email),
            ('consent_type', '=', consent_type),
            ('consent_given', '=', True),
            ('consent_withdrawn', '=', False),
            ('active', '=', True),
        ], limit=1, order='consent_date desc')

    @api.model
    def has_valid_consent(self, email, consent_type):
        """
        Check if data subject has given valid consent

        Args:
            email: Email address of data subject
            consent_type: Type of consent to check

        Returns:
            Boolean: True if valid consent exists
        """
        consent = self.get_active_consent(email, consent_type)
        if consent and not consent.is_expired:
            return True
        return False

    @api.model
    def get_consent_history(self, email):
        """
        Get full consent history for a data subject
        This is required for PDPA compliance (Right to Access)

        Args:
            email: Email address of data subject

        Returns:
            Recordset of all consent records
        """
        return self.search([
            ('data_subject_email', '=', email)
        ], order='consent_date desc')

    @api.model
    def cleanup_expired_consents(self, days=365):
        """
        Archive expired consent records older than specified days

        PDPA Compliance: Data minimization principle
        We keep consent logs for audit purposes but archive old ones

        Args:
            days: Number of days after which to archive expired consents
        """
        cutoff_date = fields.Date.today() - fields.timedelta(days=days)
        expired_consents = self.search([
            ('consent_expiry_date', '<', cutoff_date),
            ('active', '=', True),
        ])

        count = len(expired_consents)
        expired_consents.write({'active': False})

        return count
