# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import secrets
from datetime import timedelta


class AssetDamageCase(models.Model):
    """Asset Damage Case Management"""
    _name = 'asset.damage.case'
    _description = 'Asset Damage Case'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Case Number',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        help='Damage case number'
    )

    # Source Information
    damage_source = fields.Selection([
        ('inspection', 'Inspection'),
        ('checkin_teacher', 'Teacher Check-in'),
        ('checkin_student', 'Student Check-in'),
        ('manual', 'Manual Entry'),
    ], string='Damage Source', required=True, tracking=True)

    inspection_id = fields.Many2one(
        'asset.inspection',
        string='Related Inspection',
        help='Inspection where damage was found'
    )
    teacher_assignment_id = fields.Many2one(
        'asset.teacher.assignment',
        string='Related Teacher Assignment',
        help='Teacher assignment where damage was found'
    )
    student_assignment_id = fields.Many2one(
        'asset.student.assignment',
        string='Related Student Assignment',
        help='Student assignment where damage was found'
    )

    # Asset Information
    asset_id = fields.Many2one(
        'asset.asset',
        string='Asset',
        required=True,
        tracking=True,
        help='Damaged asset'
    )
    asset_code = fields.Char(
        related='asset_id.asset_code',
        string='Asset Code',
        store=True
    )

    # Damage Details
    damage_description = fields.Text(
        string='Damage Description',
        required=True,
        tracking=True,
        help='Detailed description of the damage'
    )
    damage_date = fields.Date(
        string='Damage Found Date',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    reported_by = fields.Many2one(
        'res.users',
        string='Reported By',
        default=lambda self: self.env.user,
        tracking=True
    )

    # Responsible Party
    responsible_type = fields.Selection([
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('none', 'No Custodian'),
        ('unknown', 'Unknown'),
    ], string='Responsible Party', tracking=True)

    responsible_teacher_id = fields.Many2one(
        'hr.employee',
        string='Responsible Teacher'
    )
    responsible_student_name = fields.Char(
        string='Responsible Student'
    )

    # Cost Information
    estimated_cost = fields.Float(
        string='Estimated Repair Cost',
        digits='Product Price',
        tracking=True,
        help='Estimated cost to repair'
    )
    actual_cost = fields.Float(
        string='Actual Repair Cost',
        digits='Product Price',
        tracking=True,
        help='Actual cost after repair'
    )

    # Approval Workflow
    approval_status = fields.Selection([
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Approval Status', default='pending', tracking=True)

    approver_id = fields.Many2one(
        'hr.employee',
        string='Approver',
        tracking=True,
        help='Manager/Employee to send approval request'
    )
    approver_email = fields.Char(
        string='Approver Email',
        related='approver_id.work_email',
        readonly=False,
        store=True,
        help='Email of manager to send approval request (auto-filled from employee)'
    )
    approval_date = fields.Datetime(
        string='Approval Date',
        readonly=True
    )
    approval_notes = fields.Text(
        string='Approval Notes',
        help='Notes from approver'
    )

    # Manager Online Signature (like parent signature)
    approval_signature = fields.Binary(
        string='Approval Signature',
        attachment=True,
        help='Manager digital signature'
    )
    approval_signature_date = fields.Datetime(
        string='Signature Date',
        readonly=True
    )
    approval_signature_ip = fields.Char(
        string='Signature IP Address',
        readonly=True
    )

    # Token for online signature
    approval_token = fields.Char(
        string='Approval Token',
        readonly=True,
        copy=False,
        index=True,
        help='Secure token for manager approval link'
    )
    approval_token_expiry = fields.Datetime(
        string='Token Expiry',
        readonly=True
    )
    approval_token_used = fields.Boolean(
        string='Token Used',
        default=False,
        readonly=True
    )

    # Signed approval PDF
    approval_signed_pdf_id = fields.Many2one(
        'ir.attachment',
        string='Signed Approval PDF',
        readonly=True,
        help='PDF with manager signature'
    )

    # Repair Information
    repair_decision = fields.Selection([
        ('repair', 'Repair'),
        ('replace', 'Replace'),
        ('no_action', 'No Action'),
    ], string='Repair Decision', tracking=True)

    repair_vendor = fields.Char(
        string='Repair Vendor/Service Center',
        help='Where the asset was sent for repair'
    )
    repair_sent_date = fields.Date(
        string='Sent to Repair',
        tracking=True
    )
    repair_received_date = fields.Date(
        string='Received from Repair',
        tracking=True
    )
    repair_notes = fields.Text(
        string='Repair Notes'
    )

    # Case Status
    status = fields.Selection([
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('in_repair', 'In Repair'),
        ('repaired', 'Repaired'),
        ('closed', 'Closed'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True, tracking=True)

    # Photos
    photo_ids = fields.Many2many(
        'ir.attachment',
        'damage_case_photo_rel',
        'case_id',
        'attachment_id',
        string='Damage Photos'
    )

    notes = fields.Text(string='Additional Notes')

    @api.model_create_multi
    def create(self, vals_list):
        """Generate case number on create"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('asset.damage.case') or 'New'
        return super(AssetDamageCase, self).create(vals_list)

    def action_submit_for_approval(self):
        """Submit case for approval with online signature"""
        self.ensure_one()

        if not self.damage_description:
            raise UserError(_('Please provide damage description before submitting.'))

        if not self.estimated_cost:
            raise UserError(_('Please provide estimated repair cost before submitting.'))

        if not self.approver_email:
            raise UserError(_('Please provide approver email address.'))

        # Generate secure token
        token = secrets.token_urlsafe(32)
        expiry = fields.Datetime.now() + timedelta(days=7)

        self.write({
            'status': 'pending_approval',
            'approval_status': 'pending',
            'approval_token': token,
            'approval_token_expiry': expiry,
            'approval_token_used': False,
        })

        # Send approval email with signature link
        template = self.env.ref('school_asset_management.email_template_damage_case_approval', raise_if_not_found=False)
        if template:
            # Generate mail record WITHOUT force_send, passing email_to explicitly
            mail_id = template.send_mail(
                self.id,
                force_send=False,
                email_values={'email_to': self.approver_email}
            )
            # Now send the mail
            if mail_id:
                mail = self.env['mail.mail'].sudo().browse(mail_id)
                if mail.exists():
                    mail.send()

        self.message_post(
            body=_('Case submitted for approval. Approval request sent to %s') % self.approver_email,
            subject=_('Submitted for Approval')
        )

    def action_approve(self):
        """Approve damage case"""
        self.ensure_one()

        self.write({
            'approval_status': 'approved',
            'status': 'approved',
            'approver_id': self.env.user.id,
            'approval_date': fields.Datetime.now(),
        })

        self.message_post(
            body=_('Case approved by %s') % self.env.user.name,
            subject=_('Case Approved')
        )

    def action_reject(self):
        """Reject damage case"""
        self.ensure_one()

        self.write({
            'approval_status': 'rejected',
            'status': 'rejected',
            'approver_id': self.env.user.id,
            'approval_date': fields.Datetime.now(),
        })

        self.message_post(
            body=_('Case rejected by %s. Reason: %s') % (self.env.user.name, self.approval_notes or 'No reason provided'),
            subject=_('Case Rejected')
        )

    def action_send_to_repair(self):
        """Mark as sent to repair"""
        self.ensure_one()

        if self.approval_status != 'approved':
            raise UserError(_('Case must be approved before sending to repair.'))

        if not self.repair_sent_date:
            self.repair_sent_date = fields.Date.context_today(self)

        self.write({
            'status': 'in_repair',
        })

        # Update asset status
        if self.repair_decision == 'repair':
            self.asset_id.write({'status': 'repair'})

        self.message_post(
            body=_('Asset sent to repair on %s') % self.repair_sent_date.strftime('%Y-%m-%d'),
            subject=_('Sent to Repair')
        )

    def action_receive_from_repair(self):
        """Mark as received from repair"""
        self.ensure_one()

        if self.status != 'in_repair':
            raise UserError(_('Case must be in repair status.'))

        if not self.repair_received_date:
            self.repair_received_date = fields.Date.context_today(self)

        self.write({
            'status': 'repaired',
        })

        self.message_post(
            body=_('Asset received from repair on %s') % self.repair_received_date.strftime('%Y-%m-%d'),
            subject=_('Received from Repair')
        )

    def action_close_case(self):
        """Close the damage case"""
        self.ensure_one()

        if self.status not in ('repaired', 'rejected', 'approved'):
            raise UserError(_('Case can only be closed when repaired, rejected, or approved without repair.'))

        self.write({
            'status': 'closed',
        })

        # Update asset status back to available if repaired
        if self.status == 'repaired':
            self.asset_id.write({'status': 'available'})

        # Update related inspection if exists
        if self.inspection_id:
            self.inspection_id.write({
                'action_required': 'none',
            })
            self.inspection_id.message_post(
                body=_('Damage case %s has been closed. Inspection updated: Action Required = None, Acknowledgment Status = Acknowledged.') % self.name
            )

        self.message_post(
            body=_('Case closed by %s') % self.env.user.name,
            subject=_('Case Closed')
        )

    def action_reopen_case(self):
        """Reopen closed case"""
        self.ensure_one()

        self.write({
            'status': 'approved',
        })

        # Update related inspection if exists
        if self.inspection_id:
            self.inspection_id.write({
                'action_required': 'repair',
            })
            self.inspection_id.message_post(
                body=_('Damage case %s has been reopened. Inspection updated: Action Required = Repair Needed.') % self.name
            )

        self.message_post(
            body=_('Case reopened by %s') % self.env.user.name,
            subject=_('Case Reopened')
        )

    def action_resend_approval_request(self):
        """Resend approval request email"""
        self.ensure_one()

        if self.approval_status != 'pending':
            raise UserError(_('Can only resend approval request for pending cases.'))

        # Generate new token
        token = secrets.token_urlsafe(32)
        expiry = fields.Datetime.now() + timedelta(days=7)

        self.write({
            'approval_token': token,
            'approval_token_expiry': expiry,
            'approval_token_used': False,
        })

        # Resend email
        template = self.env.ref('school_asset_management.email_template_damage_case_approval', raise_if_not_found=False)
        if template:
            # Generate mail record WITHOUT force_send, passing email_to explicitly
            mail_id = template.send_mail(
                self.id,
                force_send=False,
                email_values={'email_to': self.approver_email}
            )
            # Now send the mail
            if mail_id:
                mail = self.env['mail.mail'].sudo().browse(mail_id)
                if mail.exists():
                    mail.send()

        self.message_post(
            body=_('Approval request resent to %s') % self.approver_email
        )

    def action_copy_approval_link(self):
        """Copy approval link to clipboard (for iPad)"""
        self.ensure_one()

        if not self.approval_token:
            raise UserError(_('No approval link available. Please submit for approval first.'))

        # Get base URL
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        approval_url = f"{base_url}/damage/approve/{self.approval_token}"

        return {
            'type': 'ir.actions.client',
            'tag': 'copy_signature_link',
            'params': {
                'link': approval_url,
            },
        }

    def action_view_approval_pdf(self):
        """View signed approval PDF"""
        self.ensure_one()

        if not self.approval_signed_pdf_id:
            raise UserError(_('No signed approval PDF found.'))

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.approval_signed_pdf_id.id}?download=true',
            'target': 'new',
        }
