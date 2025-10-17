# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import secrets
from datetime import datetime, timedelta


class AssetInspection(models.Model):
    """Asset Inspection Model for periodic checks"""
    _name = 'asset.inspection'
    _description = 'Asset Inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'inspection_date desc'

    name = fields.Char(
        string='Reference',
        compute='_compute_name',
        store=True,
        help='Inspection reference'
    )
    inspection_date = fields.Date(
        string='Inspection Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        help='Date of inspection'
    )
    inspection_type = fields.Selection([
        ('random', 'Random Inspection'),
        ('scheduled', 'Scheduled Maintenance'),
        ('maintenance', 'Maintenance Check'),
        ('incident', 'Incident Report'),
    ], string='Inspection Type', required=True, default='random', tracking=True,
        help='Type of inspection')

    inspector_id = fields.Many2one(
        'res.users',
        string='Inspector',
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
        help='Person conducting the inspection'
    )
    asset_id = fields.Many2one(
        'asset.asset',
        string='Asset',
        required=True,
        tracking=True,
        index=True,
        help='Asset being inspected'
    )
    related_assignment_type = fields.Selection([
        ('teacher', 'Teacher Assignment'),
        ('student', 'Student Assignment'),
    ], string='Assignment Type')
    related_teacher_assignment_id = fields.Many2one(
        'asset.teacher.assignment',
        string='Related Teacher Assignment',
        help='Link to teacher assignment if applicable'
    )
    related_student_assignment_id = fields.Many2one(
        'asset.student.assignment',
        string='Related Student Assignment',
        help='Link to student assignment if applicable'
    )

    # Condition Assessment
    condition_before = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('broken', 'Broken/Damaged'),
    ], string='Condition Before', help='Asset condition before inspection')
    condition_after = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('broken', 'Broken/Damaged'),
    ], string='Condition After', required=True, tracking=True,
        help='Asset condition after inspection')

    # Documentation
    photo_ids = fields.Many2many(
        'ir.attachment',
        'inspection_photo_rel',
        'inspection_id',
        'attachment_id',
        string='Photos',
        help='Photos taken during inspection'
    )
    checklist_ids = fields.One2many(
        'asset.inspection.checklist',
        'inspection_id',
        string='Checklist Items'
    )
    issues_found = fields.Text(
        string='Issues Found',
        help='Description of any issues found during inspection'
    )
    action_required = fields.Selection([
        ('none', 'No Action Required'),
        ('monitor', 'Monitor'),
        ('repair', 'Repair Needed'),
        ('replace', 'Replace'),
    ], string='Action Required', default='none', tracking=True,
        help='Required action based on inspection')

    # Damage Tracking (NEW)
    damage_found = fields.Boolean(
        string='Damage Found',
        default=False,
        tracking=True,
        help='Check if damage was found during inspection'
    )
    damage_description = fields.Text(
        string='Damage Description',
        help='Detailed description of damage found'
    )
    repair_cost = fields.Float(
        string='Estimated Repair Cost',
        digits='Product Price',
        tracking=True,
        help='Estimated cost to repair the damage'
    )

    # Current Custodian (at time of inspection)
    custodian_type = fields.Selection([
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('none', 'No Custodian'),
    ], string='Custodian Type', compute='_compute_custodian_info', store=True,
        help='Type of custodian at time of inspection')

    custodian_id = fields.Many2one(
        'hr.employee',
        string='Custodian (Teacher)',
        compute='_compute_custodian_info',
        store=True,
        help='Teacher custodian if asset is assigned to teacher'
    )

    student_name = fields.Char(
        string='Custodian (Student)',
        compute='_compute_custodian_info',
        store=True,
        help='Student name if asset is assigned to student'
    )

    # Damage Acknowledgment - Teacher
    teacher_damage_acknowledged = fields.Boolean(
        string='Teacher Acknowledged',
        default=False,
        readonly=True,
        help='Teacher has acknowledged the damage'
    )
    teacher_signature = fields.Binary(
        string='Teacher Signature',
        attachment=True,
        help='Teacher signature acknowledging damage'
    )
    teacher_signature_date = fields.Datetime(
        string='Teacher Signature Date',
        readonly=True
    )
    teacher_response = fields.Text(
        string='Teacher Response',
        help='Response from teacher regarding inspection findings'
    )

    # Damage Acknowledgment - Parent (for student assignments)
    parent_name = fields.Char(
        string='Parent Name',
        help='Parent/Guardian name for student assignments'
    )
    parent_email = fields.Char(
        string='Parent Email',
        help='Parent email for sending damage acknowledgment'
    )
    parent_damage_acknowledged = fields.Boolean(
        string='Parent Acknowledged',
        default=False,
        readonly=True,
        help='Parent has acknowledged the damage'
    )
    parent_signature = fields.Binary(
        string='Parent Signature',
        attachment=True,
        help='Parent signature acknowledging damage'
    )
    parent_signature_date = fields.Datetime(
        string='Parent Signature Date',
        readonly=True
    )
    parent_signature_ip = fields.Char(
        string='Parent IP Address',
        readonly=True,
        help='IP address of parent when signing'
    )

    # Token-based signature (for parent online signature)
    damage_token = fields.Char(
        string='Damage Token',
        readonly=True,
        copy=False,
        index=True,
        help='Secure token for parent signature link'
    )
    damage_token_expiry = fields.Datetime(
        string='Token Expiry',
        readonly=True,
        help='Expiry date of signature token'
    )
    damage_token_used = fields.Boolean(
        string='Token Used',
        default=False,
        readonly=True,
        help='Whether token has been used'
    )

    # Damage acknowledgment status
    damage_acknowledgment_status = fields.Selection([
        ('not_required', 'Not Required'),
        ('pending', 'Pending Acknowledgment'),
        ('acknowledged', 'Acknowledged'),
        ('expired', 'Link Expired'),
    ], string='Acknowledgment Status', compute='_compute_acknowledgment_status', store=True,
        help='Status of damage acknowledgment')

    # Signed PDF
    damage_signed_pdf_id = fields.Many2one(
        'ir.attachment',
        string='Signed Damage Report PDF',
        readonly=True,
        help='PDF report with damage acknowledgment signature'
    )

    # Damage Case (Only one per inspection)
    damage_case_id = fields.Many2one(
        'asset.damage.case',
        string='Damage Case',
        help='Damage case created from this inspection',
        compute='_compute_damage_case',
        store=True
    )

    notes = fields.Text(string='Additional Notes')

    @api.depends('asset_id', 'inspection_date', 'inspection_type')
    def _compute_name(self):
        """Generate inspection name"""
        for record in self:
            if record.asset_id and record.inspection_date:
                type_dict = dict(record._fields['inspection_type'].selection)
                type_name = type_dict.get(record.inspection_type, '')
                record.name = f"{record.asset_id.asset_code} - {type_name} - {record.inspection_date}"
            else:
                record.name = _('New Inspection')

    @api.depends('asset_id')
    def _compute_custodian_info(self):
        """Determine current custodian at time of inspection"""
        for record in self:
            if not record.asset_id:
                record.custodian_type = 'none'
                record.custodian_id = False
                record.student_name = False
                continue

            asset = record.asset_id

            # Check asset status to determine custodian
            if asset.status == 'assigned_teacher' and asset.custodian_id:
                record.custodian_type = 'teacher'
                record.custodian_id = asset.custodian_id
                record.student_name = False
            elif asset.status == 'assigned_student':
                # Find active student assignment
                student_assignment = self.env['asset.student.assignment'].search([
                    ('asset_line_ids.asset_id', '=', asset.id),
                    ('status', '=', 'checked_out')
                ], limit=1)
                if student_assignment:
                    record.custodian_type = 'student'
                    record.custodian_id = False
                    record.student_name = student_assignment.student_name
                else:
                    record.custodian_type = 'none'
                    record.custodian_id = False
                    record.student_name = False
            else:
                record.custodian_type = 'none'
                record.custodian_id = False
                record.student_name = False

    def _compute_damage_case(self):
        """Find damage case created from this inspection"""
        for record in self:
            damage_case = self.env['asset.damage.case'].search([
                ('inspection_id', '=', record.id)
            ], limit=1)
            record.damage_case_id = damage_case.id if damage_case else False

    @api.depends('damage_found', 'teacher_damage_acknowledged', 'parent_damage_acknowledged',
                 'damage_token', 'damage_token_expiry', 'damage_token_used', 'custodian_type',
                 'damage_case_id', 'damage_case_id.status')
    def _compute_acknowledgment_status(self):
        """Compute damage acknowledgment status"""
        for record in self:
            # If no damage found, not required
            if not record.damage_found:
                record.damage_acknowledgment_status = 'not_required'
                continue

            # If damage case is closed, consider as acknowledged
            if record.damage_case_id and record.damage_case_id.status == 'closed':
                record.damage_acknowledgment_status = 'acknowledged'
                continue

            # Check custodian acknowledgment
            if record.custodian_type == 'teacher' and record.teacher_damage_acknowledged:
                record.damage_acknowledgment_status = 'acknowledged'
            elif record.custodian_type == 'student' and record.parent_damage_acknowledged:
                record.damage_acknowledgment_status = 'acknowledged'
            elif record.custodian_type == 'none':
                # No custodian - if damage case exists, pending; otherwise not required
                if record.damage_case_id:
                    record.damage_acknowledgment_status = 'pending'
                else:
                    record.damage_acknowledgment_status = 'not_required'
            elif record.damage_token and record.damage_token_expiry:
                if record.damage_token_expiry < fields.Datetime.now():
                    record.damage_acknowledgment_status = 'expired'
                else:
                    record.damage_acknowledgment_status = 'pending'
            elif record.damage_found:
                record.damage_acknowledgment_status = 'pending'
            else:
                record.damage_acknowledgment_status = 'not_required'

    @api.onchange('asset_id')
    def _onchange_asset_id(self):
        """Set condition before from asset condition"""
        if self.asset_id:
            self.condition_before = self.asset_id.condition_rating

    @api.onchange('damage_found')
    def _onchange_damage_found(self):
        """Auto-set action_required to repair if damage found"""
        if self.damage_found and self.action_required == 'none':
            self.action_required = 'repair'

    def action_update_asset_condition(self):
        """Update asset condition based on inspection"""
        self.ensure_one()
        if self.condition_after:
            self.asset_id.write({
                'condition_rating': self.condition_after
            })
            self.message_post(
                body=_('Asset condition updated to: %s') % dict(
                    self._fields['condition_after'].selection
                ).get(self.condition_after)
            )

    def action_send_teacher_damage_notification(self):
        """Send damage notification to teacher for acknowledgment"""
        self.ensure_one()

        if not self.damage_found:
            raise UserError(_('No damage found to acknowledge.'))

        if self.custodian_type != 'teacher':
            raise UserError(_('Asset is not assigned to a teacher.'))

        if not self.custodian_id:
            raise UserError(_('No teacher custodian found.'))

        # Create activity for teacher to acknowledge damage
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=self.custodian_id.user_id.id,
            summary=_('Damage Found - Acknowledgment Required'),
            note=_(
                'Damage was found during inspection of asset %s:\n\n'
                'Damage: %s\n'
                'Estimated Repair Cost: %.2f\n\n'
                'Please review and acknowledge.'
            ) % (self.asset_id.asset_code, self.damage_description or 'N/A', self.repair_cost or 0.0)
        )

        self.message_post(
            body=_('Damage notification sent to %s') % self.custodian_id.name,
            subject=_('Damage Acknowledgment Requested')
        )

    def action_teacher_acknowledge_damage(self):
        """Teacher acknowledges damage in-person (IT signs)"""
        self.ensure_one()

        if not self.damage_found:
            raise UserError(_('No damage to acknowledge.'))

        if not self.teacher_signature:
            raise UserError(_('Please provide teacher signature before acknowledging.'))

        self.write({
            'teacher_damage_acknowledged': True,
            'teacher_signature_date': fields.Datetime.now(),
        })

        self.message_post(
            body=_('Teacher damage acknowledgment recorded by %s') % self.env.user.name
        )

    def action_send_parent_damage_acknowledgment(self):
        """Send online damage acknowledgment request to parent"""
        self.ensure_one()

        if not self.damage_found:
            raise UserError(_('No damage found to report.'))

        if self.custodian_type != 'student':
            raise UserError(_('Asset is not assigned to a student.'))

        if not self.parent_email:
            raise UserError(_('Parent email is required. Please add parent email first.'))

        # Generate secure token
        token = secrets.token_urlsafe(32)
        expiry = fields.Datetime.now() + timedelta(days=7)

        self.write({
            'damage_token': token,
            'damage_token_expiry': expiry,
            'damage_token_used': False,
        })

        # Send email with signature link
        template = self.env.ref('school_asset_management.email_template_inspection_damage_notification', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=False)

        self.message_post(
            body=_('Damage acknowledgment request sent to parent: %s') % self.parent_email
        )

    def action_resend_parent_damage_acknowledgment(self):
        """Resend damage acknowledgment request"""
        self.ensure_one()

        # Generate new token
        token = secrets.token_urlsafe(32)
        expiry = fields.Datetime.now() + timedelta(days=7)

        self.write({
            'damage_token': token,
            'damage_token_expiry': expiry,
            'damage_token_used': False,
        })

        # Resend email
        template = self.env.ref('school_asset_management.email_template_inspection_damage_notification', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=False)

        self.message_post(
            body=_('Damage acknowledgment request resent to parent: %s') % self.parent_email
        )

    def action_view_damage_pdf(self):
        """View signed damage report PDF"""
        self.ensure_one()

        if not self.damage_signed_pdf_id:
            raise UserError(_('No signed damage report PDF found.'))

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.damage_signed_pdf_id.id}?download=true',
            'target': 'new',
        }

    def action_copy_inspection_damage_link(self):
        """Copy inspection damage signature link to clipboard (for iPad)"""
        self.ensure_one()

        if not self.damage_token:
            raise UserError(_('No damage signature link available. Please send the damage acknowledgment first.'))

        # Get base URL
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        signature_url = f"{base_url}/sign/inspection/damage/{self.damage_token}"

        return {
            'type': 'ir.actions.client',
            'tag': 'copy_signature_link',
            'params': {
                'link': signature_url,
            },
        }

    def action_create_damage_case(self):
        """Create damage case from inspection"""
        self.ensure_one()

        if not self.damage_found:
            raise UserError(_('No damage found to create a damage case.'))

        # Prepare damage case values
        vals = {
            'damage_source': 'inspection',
            'inspection_id': self.id,
            'asset_id': self.asset_id.id,
            'damage_description': self.damage_description or self.issues_found or '',
            'damage_date': self.inspection_date,
            'reported_by': self.inspector_id.id,
            'estimated_cost': self.repair_cost or 0.0,
        }

        # Set responsible party based on custodian
        if self.custodian_type == 'teacher' and self.custodian_id:
            vals['responsible_type'] = 'teacher'
            vals['responsible_teacher_id'] = self.custodian_id.id
        elif self.custodian_type == 'student' and self.student_name:
            vals['responsible_type'] = 'student'
            vals['responsible_student_name'] = self.student_name
        else:
            vals['responsible_type'] = 'none'

        # Create damage case
        damage_case = self.env['asset.damage.case'].create(vals)

        # Copy photos if any
        if self.photo_ids:
            damage_case.write({'photo_ids': [(6, 0, self.photo_ids.ids)]})

        # Update inspection to link to the damage case
        self.write({'damage_case_id': damage_case.id})

        # Return action to open the new damage case
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'asset.damage.case',
            'res_id': damage_case.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_damage_case(self):
        """View damage case created from this inspection"""
        self.ensure_one()

        if not self.damage_case_id:
            raise UserError(_('No damage case found for this inspection.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Damage Case'),
            'res_model': 'asset.damage.case',
            'res_id': self.damage_case_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class AssetInspectionChecklist(models.Model):
    """Inspection Checklist Items"""
    _name = 'asset.inspection.checklist'
    _description = 'Asset Inspection Checklist'
    _order = 'sequence, id'

    inspection_id = fields.Many2one(
        'asset.inspection',
        string='Inspection',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    name = fields.Char(
        string='Check Item',
        required=True,
        help='Item to check'
    )
    checked = fields.Boolean(
        string='Checked',
        help='Check if item passes inspection'
    )
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('na', 'Not Applicable'),
    ], string='Result', help='Inspection result')
    notes = fields.Text(
        string='Notes',
        help='Additional notes for this item'
    )
