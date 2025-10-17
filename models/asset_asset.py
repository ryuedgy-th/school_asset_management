# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class AssetAsset(models.Model):
    """Main Asset Model for tracking school assets"""
    _name = 'asset.asset'
    _description = 'Asset'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'asset_code'
    _order = 'asset_code desc'

    # Basic Information
    asset_code = fields.Char(
        string='Asset Code',
        required=True,
        copy=False,
        index=True,
        help='Unique code for the asset'
    )
    name = fields.Char(
        string='Asset Name',
        tracking=True,
        index=True,
        help='Name or description of the asset (optional)'
    )
    category_id = fields.Many2one(
        'asset.category',
        string='Category',
        required=True,
        tracking=True,
        index=True,
        help='Asset category for classification'
    )

    # Specifications
    brand = fields.Char(
        string='Brand',
        tracking=True,
        help='Brand or manufacturer name'
    )
    model = fields.Char(
        string='Model',
        tracking=True,
        help='Model number or name'
    )
    serial_number = fields.Char(
        string='Serial Number',
        copy=False,
        tracking=True,
        index=True,
        help='Unique serial number from manufacturer'
    )

    # Purchase Information
    purchase_date = fields.Date(
        string='Purchase Date',
        tracking=True,
        help='Date when the asset was purchased'
    )
    purchase_cost = fields.Float(
        string='Purchase Cost',
        digits='Product Price',
        tracking=True,
        help='Original purchase cost'
    )
    supplier_id = fields.Many2one(
        'res.partner',
        string='Supplier',
        domain=[('supplier_rank', '>', 0)],
        tracking=True,
        help='Supplier or vendor who sold the asset'
    )

    # Warranty Information
    warranty_start_date = fields.Date(
        string='Warranty Start Date',
        tracking=True,
        help='Start date of warranty period'
    )
    warranty_end_date = fields.Date(
        string='Warranty End Date',
        tracking=True,
        help='End date of warranty period'
    )
    warranty_months = fields.Integer(
        string='Warranty Period (Months)',
        compute='_compute_warranty_months',
        store=True,
        help='Warranty duration in months'
    )
    warranty_status = fields.Selection([
        ('none', 'No Warranty'),
        ('active', 'Under Warranty'),
        ('expired', 'Warranty Expired'),
    ], string='Warranty Status', compute='_compute_warranty_status', store=True,
        help='Current warranty status')
    is_warranty_expiring_soon = fields.Boolean(
        string='Warranty Expiring Soon',
        compute='_compute_warranty_status',
        store=True,
        help='True if warranty expires within 30 days'
    )

    # Location and Assignment
    location_id = fields.Many2one(
        'asset.location',
        string='Current Location',
        tracking=True,
        index=True,
        help='Current physical location of the asset'
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        tracking=True,
        index=True,
        help='Department responsible for the asset'
    )
    custodian_id = fields.Many2one(
        'hr.employee',
        string='Custodian',
        tracking=True,
        index=True,
        help='Current person responsible for the asset'
    )

    # Status and Condition
    status = fields.Selection([
        ('available', 'Available'),
        ('assigned_teacher', 'Assigned to Teacher'),
        ('assigned_student', 'Assigned to Student'),
        ('maintenance', 'Under Maintenance'),
        ('repair', 'Under Repair'),
        ('retired', 'Retired'),
        ('lost', 'Lost'),
    ], string='Status', default='available', required=True, tracking=True,
        help='Current status of the asset')

    condition_rating = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('broken', 'Broken/Damaged'),
    ], string='Condition', default='excellent', tracking=True,
        help='Physical condition rating of the asset')

    # Additional Information
    notes = fields.Text(
        string='Notes',
        help='Additional notes or comments about the asset'
    )
    image_1920 = fields.Binary(
        string='Image',
        attachment=True,
        help='Asset image'
    )
    active = fields.Boolean(
        default=True,
        help='Set to false to archive the asset without deleting it'
    )

    # Computed Fields
    age_months = fields.Integer(
        string='Age (Months)',
        compute='_compute_age_months',
        store=True,
        help='Number of months since purchase date'
    )

    # Related Fields
    teacher_assignment_ids = fields.One2many(
        'asset.assignment.line',
        'asset_id',
        string='Teacher Assignments',
        domain=[('assignment_id.assignment_type', '=', 'teacher')]
    )
    student_assignment_ids = fields.One2many(
        'asset.student.line',
        'asset_id',
        string='Student Assignments'
    )
    inspection_ids = fields.One2many(
        'asset.inspection',
        'asset_id',
        string='Inspections'
    )
    movement_ids = fields.One2many(
        'asset.movement',
        'asset_id',
        string='Movement History'
    )

    # Counts for Smart Buttons
    assignment_count = fields.Integer(
        compute='_compute_assignment_count',
        string='Assignments'
    )
    inspection_count = fields.Integer(
        compute='_compute_inspection_count',
        string='Inspections'
    )
    movement_count = fields.Integer(
        compute='_compute_movement_count',
        string='Movements'
    )
    damage_count = fields.Integer(
        compute='_compute_damage_count',
        string='Damages',
        help='Total number of damages found from check-ins'
    )

    _sql_constraints = [
        ('asset_code_unique', 'unique(asset_code)', 'Asset code must be unique!'),
        ('serial_number_unique', 'unique(serial_number)', 'Serial number must be unique!'),
    ]

    @api.model
    def create(self, vals_list):
        """Create asset records"""
        assets = super(AssetAsset, self).create(vals_list)

        # Create initial movement record for each asset
        for asset in assets:
            if asset.location_id or asset.custodian_id:
                self.env['asset.movement'].create({
                    'asset_id': asset.id,
                    'to_location_id': asset.location_id.id if asset.location_id else False,
                    'to_custodian_id': asset.custodian_id.id if asset.custodian_id else False,
                    'reason': 'assignment',
                    'notes': 'Initial assignment',
                })

        return assets

    def write(self, vals):
        """Track location and custodian changes"""
        for asset in self:
            # Track location/custodian changes
            if 'location_id' in vals or 'custodian_id' in vals:
                self.env['asset.movement'].create({
                    'asset_id': asset.id,
                    'from_location_id': asset.location_id.id if asset.location_id else False,
                    'to_location_id': vals.get('location_id', asset.location_id.id if asset.location_id else False),
                    'from_custodian_id': asset.custodian_id.id if asset.custodian_id else False,
                    'to_custodian_id': vals.get('custodian_id', asset.custodian_id.id if asset.custodian_id else False),
                    'reason': vals.get('movement_reason', 'transfer'),
                    'notes': vals.get('movement_notes', ''),
                })

        return super(AssetAsset, self).write(vals)

    @api.depends('warranty_start_date', 'warranty_end_date')
    def _compute_warranty_months(self):
        """Calculate warranty period in months"""
        for asset in self:
            if asset.warranty_start_date and asset.warranty_end_date:
                delta = relativedelta(asset.warranty_end_date, asset.warranty_start_date)
                asset.warranty_months = delta.years * 12 + delta.months
            else:
                asset.warranty_months = 0

    @api.depends('warranty_end_date')
    def _compute_warranty_status(self):
        """Compute warranty status and expiring soon flag"""
        today = fields.Date.today()
        for asset in self:
            if not asset.warranty_end_date:
                asset.warranty_status = 'none'
                asset.is_warranty_expiring_soon = False
            elif asset.warranty_end_date < today:
                asset.warranty_status = 'expired'
                asset.is_warranty_expiring_soon = False
            else:
                asset.warranty_status = 'active'
                # Check if expiring within 30 days
                days_until_expiry = (asset.warranty_end_date - today).days
                asset.is_warranty_expiring_soon = days_until_expiry <= 30

    @api.depends('purchase_date')
    def _compute_age_months(self):
        """Calculate asset age in months"""
        today = fields.Date.today()
        for asset in self:
            if asset.purchase_date:
                delta = relativedelta(today, asset.purchase_date)
                asset.age_months = delta.years * 12 + delta.months
            else:
                asset.age_months = 0

    def _compute_assignment_count(self):
        """Count total assignments"""
        for asset in self:
            teacher_count = len(asset.teacher_assignment_ids)
            student_count = len(asset.student_assignment_ids)
            asset.assignment_count = teacher_count + student_count

    def _compute_inspection_count(self):
        """Count inspections"""
        for asset in self:
            asset.inspection_count = len(asset.inspection_ids)

    def _compute_movement_count(self):
        """Count movement records"""
        for asset in self:
            asset.movement_count = len(asset.movement_ids)

    def _compute_damage_count(self):
        """Count total damages from check-ins and inspections"""
        for asset in self:
            # Count damages from teacher assignment check-ins
            teacher_damage_count = self.env['asset.assignment.line'].search_count([
                ('asset_id', '=', asset.id),
                ('damage_found', '=', True)
            ])

            # Count damages from student assignment check-ins
            student_damage_count = self.env['asset.student.line'].search_count([
                ('asset_id', '=', asset.id),
                ('damage_found', '=', True)
            ])

            # Count damages from inspections (NEW)
            inspection_damage_count = self.env['asset.inspection'].search_count([
                ('asset_id', '=', asset.id),
                ('damage_found', '=', True)
            ])

            asset.damage_count = teacher_damage_count + student_damage_count + inspection_damage_count

    @api.constrains('warranty_start_date', 'warranty_end_date')
    def _check_warranty_dates(self):
        """Validate warranty dates"""
        for asset in self:
            if asset.warranty_start_date and asset.warranty_end_date:
                if asset.warranty_end_date < asset.warranty_start_date:
                    raise ValidationError(_(
                        'Warranty end date cannot be before warranty start date.'
                    ))

    @api.constrains('purchase_cost')
    def _check_purchase_cost(self):
        """Validate purchase cost is positive"""
        for asset in self:
            if asset.purchase_cost < 0:
                raise ValidationError(_('Purchase cost cannot be negative.'))

    def action_view_assignments(self):
        """View all assignments for this asset"""
        self.ensure_one()
        return {
            'name': _('Assignments'),
            'type': 'ir.actions.act_window',
            'res_model': 'asset.assignment.line',
            'view_mode': 'list,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id},
        }

    def action_view_inspections(self):
        """View all inspections for this asset"""
        self.ensure_one()
        return {
            'name': _('Inspections'),
            'type': 'ir.actions.act_window',
            'res_model': 'asset.inspection',
            'view_mode': 'list,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id},
        }

    def action_view_movements(self):
        """View movement history for this asset"""
        self.ensure_one()
        return {
            'name': _('Movement History'),
            'type': 'ir.actions.act_window',
            'res_model': 'asset.movement',
            'view_mode': 'list,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id},
        }

    def action_view_damages(self):
        """View all damage records for this asset"""
        self.ensure_one()

        # Get damage records from teacher assignments, student assignments, and inspections
        teacher_damage_ids = self.env['asset.assignment.line'].search([
            ('asset_id', '=', self.id),
            ('damage_found', '=', True)
        ]).ids

        student_damage_ids = self.env['asset.student.line'].search([
            ('asset_id', '=', self.id),
            ('damage_found', '=', True)
        ]).ids

        inspection_damage_ids = self.env['asset.inspection'].search([
            ('asset_id', '=', self.id),
            ('damage_found', '=', True)
        ]).ids

        # Show inspections first if available, otherwise show assignment damages
        if inspection_damage_ids:
            return {
                'name': _('Damage History - %s') % self.asset_code,
                'type': 'ir.actions.act_window',
                'res_model': 'asset.inspection',
                'view_mode': 'list,form',
                'domain': [('id', 'in', inspection_damage_ids)],
                'context': {'default_asset_id': self.id},
            }
        elif teacher_damage_ids:
            return {
                'name': _('Damage History - %s') % self.asset_code,
                'type': 'ir.actions.act_window',
                'res_model': 'asset.assignment.line',
                'view_mode': 'list,form',
                'domain': [('id', 'in', teacher_damage_ids)],
                'context': {'default_asset_id': self.id},
            }
        elif student_damage_ids:
            return {
                'name': _('Damage History - %s') % self.asset_code,
                'type': 'ir.actions.act_window',
                'res_model': 'asset.student.line',
                'view_mode': 'list,form',
                'domain': [('id', 'in', student_damage_ids)],
                'context': {'default_asset_id': self.id},
            }
        else:
            # No damages found, show inspection view (empty)
            return {
                'name': _('Damage History - %s') % self.asset_code,
                'type': 'ir.actions.act_window',
                'res_model': 'asset.inspection',
                'view_mode': 'list,form',
                'domain': [('id', '=', False)],
            }

    def action_set_available(self):
        """Set asset status to available"""
        self.write({'status': 'available'})

    def action_set_maintenance(self):
        """Set asset status to maintenance"""
        self.write({'status': 'maintenance'})

    def action_set_repair(self):
        """Set asset status to repair"""
        self.write({'status': 'repair'})

    def action_set_retired(self):
        """Set asset status to retired"""
        self.write({'status': 'retired', 'active': False})
