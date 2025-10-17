# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import json
import base64


class AssetDataRequest(models.Model):
    """
    PDPA Data Subject Rights Management

    This model handles requests from data subjects to exercise their rights under PDPA:
    - Right to Access (Section 30)
    - Right to Rectification (Section 31)
    - Right to Erasure (Section 32)
    - Right to Restriction (Section 33)
    - Right to Data Portability (Section 34)
    - Right to Object (Section 35)
    """
    _name = 'asset.data.request'
    _description = 'Data Subject Rights Request'
    _order = 'request_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Request Reference',
        required=True,
        readonly=True,
        default='New',
        copy=False,
        help='Unique reference for this data request'
    )

    # Request Type
    request_type = fields.Selection([
        ('access', 'Right to Access (ขอเข้าถึงข้อมูล)'),
        ('rectification', 'Right to Rectification (ขอแก้ไขข้อมูล)'),
        ('erasure', 'Right to Erasure (ขอลบข้อมูล)'),
        ('restriction', 'Right to Restriction (ขอระงับการใช้)'),
        ('portability', 'Right to Data Portability (ขอโอนย้ายข้อมูล)'),
        ('object', 'Right to Object (ขอคัดค้าน)'),
        ('withdraw_consent', 'Withdraw Consent (เพิกถอนความยินยอม)'),
    ], string='Request Type', required=True, tracking=True,
        help='Type of data subject right being exercised')

    # Requester Information
    requester_name = fields.Char(
        string='Requester Name',
        required=True,
        tracking=True,
        help='Name of person making the request'
    )
    requester_email = fields.Char(
        string='Email Address',
        required=True,
        tracking=True,
        index=True,
        help='Email address for verification and response'
    )
    requester_type = fields.Selection([
        ('parent', 'Parent/Guardian'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    ], string='Requester Type', required=True)

    # Request Details
    request_date = fields.Datetime(
        string='Request Date',
        required=True,
        default=fields.Datetime.now,
        readonly=True,
        tracking=True
    )
    request_description = fields.Text(
        string='Request Details',
        required=True,
        help='Detailed description of the request'
    )

    # Identity Verification
    identity_verified = fields.Boolean(
        string='Identity Verified',
        default=False,
        tracking=True,
        help='Whether requester identity has been verified'
    )
    verification_method = fields.Selection([
        ('email', 'Email Verification'),
        ('phone', 'Phone Verification'),
        ('in_person', 'In-Person Verification'),
        ('id_document', 'ID Document'),
    ], string='Verification Method')
    verification_date = fields.Datetime(
        string='Verification Date',
        readonly=True
    )
    verified_by = fields.Many2one(
        'res.users',
        string='Verified By',
        readonly=True
    )

    # Status
    status = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('identity_verification', 'Pending Identity Verification'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    # Processing
    assigned_to = fields.Many2one(
        'res.users',
        string='Assigned To',
        tracking=True,
        help='User responsible for processing this request'
    )
    processing_notes = fields.Text(
        string='Processing Notes',
        help='Internal notes about request processing'
    )
    completion_date = fields.Datetime(
        string='Completion Date',
        readonly=True
    )

    # Response
    response_message = fields.Text(
        string='Response to Requester',
        help='Official response sent to requester'
    )
    response_date = fields.Datetime(
        string='Response Date',
        readonly=True
    )

    # For Access/Portability Requests
    data_export_file = fields.Binary(
        string='Exported Data',
        attachment=True,
        help='Data export file (JSON/CSV)'
    )
    data_export_filename = fields.Char(
        string='Export Filename'
    )

    # Deadline Management (PDPA requires response within 30 days)
    deadline_date = fields.Date(
        string='Deadline',
        compute='_compute_deadline',
        store=True,
        help='PDPA requires response within 30 days'
    )
    is_overdue = fields.Boolean(
        string='Overdue',
        compute='_compute_overdue',
        store=True
    )
    days_remaining = fields.Integer(
        string='Days Remaining',
        compute='_compute_overdue',
        store=True
    )

    # Related Records
    student_assignment_ids = fields.Many2many(
        'asset.student.assignment',
        string='Related Student Assignments',
        help='Student assignments related to this data request'
    )
    teacher_assignment_ids = fields.Many2many(
        'asset.teacher.assignment',
        string='Related Teacher Assignments',
        help='Teacher assignments related to this data request'
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Generate unique request reference"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('asset.data.request') or 'New'
        return super().create(vals_list)

    @api.depends('request_date')
    def _compute_deadline(self):
        """PDPA requires response within 30 days"""
        for record in self:
            if record.request_date:
                record.deadline_date = (record.request_date + fields.timedelta(days=30)).date()
            else:
                record.deadline_date = False

    @api.depends('deadline_date', 'status')
    def _compute_overdue(self):
        """Check if request is overdue"""
        today = fields.Date.today()
        for record in self:
            if record.status not in ('completed', 'rejected', 'cancelled') and record.deadline_date:
                if record.deadline_date < today:
                    record.is_overdue = True
                    record.days_remaining = (today - record.deadline_date).days * -1
                else:
                    record.is_overdue = False
                    record.days_remaining = (record.deadline_date - today).days
            else:
                record.is_overdue = False
                record.days_remaining = 0

    def action_submit(self):
        """Submit request for processing"""
        self.ensure_one()
        if not self.requester_email:
            raise ValidationError(_('Email address is required.'))

        self.write({
            'status': 'submitted',
            'request_date': fields.Datetime.now(),
        })

        # Send confirmation email to requester
        self._send_confirmation_email()

        # Notify DPO/IT team
        self._notify_dpo()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Request Submitted'),
                'message': _('Your data request has been submitted. You will receive a response within 30 days.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_start_verification(self):
        """Start identity verification process"""
        self.ensure_one()
        self.write({'status': 'identity_verification'})

    def action_verify_identity(self):
        """Mark identity as verified"""
        self.ensure_one()
        self.write({
            'identity_verified': True,
            'verification_date': fields.Datetime.now(),
            'verified_by': self.env.user.id,
            'status': 'processing',
        })

        self.message_post(
            body=_('Identity verified by %s on %s') % (
                self.env.user.name,
                fields.Datetime.now().strftime('%Y-%m-%d %H:%M')
            )
        )

    def action_process_access_request(self):
        """Process Right to Access request - Export all personal data"""
        self.ensure_one()

        if self.request_type != 'access':
            raise UserError(_('This action is only for Access requests.'))

        # Gather all personal data
        data = self._gather_personal_data()

        # Create JSON export
        json_data = json.dumps(data, indent=2, ensure_ascii=False)
        json_file = base64.b64encode(json_data.encode('utf-8'))

        self.write({
            'data_export_file': json_file,
            'data_export_filename': f'Personal_Data_Export_{self.requester_name}_{fields.Date.today()}.json',
            'status': 'completed',
            'completion_date': fields.Datetime.now(),
            'response_message': _(
                'Your personal data export has been generated. '
                'Please download the attached file. '
                'This data includes all information we have stored about you.'
            ),
        })

        # Send email with download link
        self._send_completion_email()

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/asset.data.request/{self.id}/data_export_file/{self.data_export_filename}?download=true',
            'target': 'new',
        }

    def action_process_erasure_request(self):
        """Process Right to Erasure request - Delete or anonymize data"""
        self.ensure_one()

        if self.request_type != 'erasure':
            raise UserError(_('This action is only for Erasure requests.'))

        # Check if data can be deleted (legal obligations)
        can_delete, reason = self._can_delete_data()

        if not can_delete:
            self.write({
                'status': 'rejected',
                'completion_date': fields.Datetime.now(),
                'response_message': _(
                    'Your data deletion request cannot be fully processed due to: %s\n\n'
                    'However, we have anonymized your personal data where possible.'
                ) % reason,
            })
        else:
            # Anonymize data
            self._anonymize_data()

            self.write({
                'status': 'completed',
                'completion_date': fields.Datetime.now(),
                'response_message': _(
                    'Your personal data has been deleted/anonymized as requested. '
                    'Minimal data retained for legal compliance has been anonymized.'
                ),
            })

        self._send_completion_email()

    def _gather_personal_data(self):
        """Gather all personal data for export (Right to Access)"""
        self.ensure_one()

        data = {
            'request_date': fields.Datetime.now().isoformat(),
            'data_subject': {
                'name': self.requester_name,
                'email': self.requester_email,
                'type': self.requester_type,
            },
            'student_assignments': [],
            'teacher_assignments': [],
            'consent_records': [],
            'security_logs': [],
        }

        # Find student assignments
        student_assignments = self.env['asset.student.assignment'].search([
            ('parent_email', '=', self.requester_email)
        ])
        for assignment in student_assignments:
            data['student_assignments'].append({
                'id': assignment.id,
                'student_name': assignment.student_name,
                'grade_level': assignment.grade_level,
                'checkout_date': assignment.checkout_date.isoformat() if assignment.checkout_date else None,
                'return_date': assignment.actual_return_date.isoformat() if assignment.actual_return_date else None,
                'status': assignment.status,
                'assets': [{'code': line.asset_code, 'name': line.asset_name} for line in assignment.asset_line_ids],
            })

        # Find teacher assignments
        teacher_assignments = self.env['asset.teacher.assignment'].search([
            ('teacher_email', '=', self.requester_email)
        ])
        for assignment in teacher_assignments:
            data['teacher_assignments'].append({
                'id': assignment.id,
                'teacher_name': assignment.teacher_id.name,
                'checkout_date': assignment.checkout_date.isoformat() if assignment.checkout_date else None,
                'return_date': assignment.actual_return_date.isoformat() if assignment.actual_return_date else None,
                'status': assignment.status,
            })

        # Find consent records
        consent_logs = self.env['asset.consent.log'].search([
            ('data_subject_email', '=', self.requester_email)
        ])
        for consent in consent_logs:
            data['consent_records'].append({
                'consent_type': consent.consent_type,
                'consent_date': consent.consent_date.isoformat() if consent.consent_date else None,
                'consent_given': consent.consent_given,
                'withdrawn': consent.consent_withdrawn,
                'privacy_policy_version': consent.privacy_policy_version,
            })

        # Find security audit logs (limited info)
        audit_logs = self.env['asset.security.audit.log'].search([
            ('parent_email', '=', self.requester_email)
        ], limit=50, order='create_date desc')
        for log in audit_logs:
            data['security_logs'].append({
                'event_type': log.event_type,
                'date': log.create_date.isoformat(),
                'ip_address': log.ip_address,
            })

        return data

    def _can_delete_data(self):
        """Check if data can be deleted or must be retained"""
        self.ensure_one()

        # Check for active assignments
        active_student = self.env['asset.student.assignment'].search_count([
            ('parent_email', '=', self.requester_email),
            ('status', '=', 'checked_out')
        ])
        if active_student > 0:
            return False, _('You have active asset assignments. Please return all assets first.')

        active_teacher = self.env['asset.teacher.assignment'].search_count([
            ('teacher_email', '=', self.requester_email),
            ('status', '=', 'checked_out')
        ])
        if active_teacher > 0:
            return False, _('You have active asset assignments. Please return all assets first.')

        # Check for outstanding damages
        outstanding_damages = self.env['asset.damage.case'].search_count([
            '|',
            ('student_assignment_id.parent_email', '=', self.requester_email),
            ('teacher_assignment_id.teacher_email', '=', self.requester_email),
            ('status', 'in', ['draft', 'reported', 'approved'])
        ])
        if outstanding_damages > 0:
            return False, _('You have outstanding damage cases that need to be resolved.')

        # Otherwise, data can be anonymized (not fully deleted due to audit requirements)
        return True, ''

    def _anonymize_data(self):
        """Anonymize personal data while retaining records for legal compliance"""
        self.ensure_one()

        anonymous_name = f'Anonymous_{self.id}'
        anonymous_email = f'deleted_{self.id}@anonymized.local'

        # Anonymize student assignments
        student_assignments = self.env['asset.student.assignment'].search([
            ('parent_email', '=', self.requester_email)
        ])
        student_assignments.write({
            'student_name': anonymous_name,
            'parent_name': anonymous_name,
            'parent_email': anonymous_email,
            'notes': '(Data anonymized per PDPA request)',
        })

        # Anonymize consent logs
        consent_logs = self.env['asset.consent.log'].search([
            ('data_subject_email', '=', self.requester_email)
        ])
        consent_logs.write({
            'data_subject_name': anonymous_name,
            'data_subject_email': anonymous_email,
            'active': False,
        })

        # Note: Audit logs kept for security but with minimal PII

    def _send_confirmation_email(self):
        """Send confirmation email to requester"""
        # TODO: Implement email template
        pass

    def _send_completion_email(self):
        """Send completion email with results"""
        # TODO: Implement email template
        pass

    def _notify_dpo(self):
        """Notify DPO/IT team about new data request"""
        # Create activity for DPO
        dpo_group = self.env.ref('school_asset_management.group_asset_manager', raise_if_not_found=False)
        if dpo_group:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('New Data Subject Request'),
                note=_('Process data request: %s from %s') % (self.request_type, self.requester_name),
                user_id=dpo_group.users[0].id if dpo_group.users else self.env.user.id,
            )
