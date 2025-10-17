# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AssetMovement(models.Model):
    """Asset Movement History for tracking location and custodian changes"""
    _name = 'asset.movement'
    _description = 'Asset Movement History'
    _order = 'movement_date desc'
    _rec_name = 'display_name'

    display_name = fields.Char(
        string='Name',
        compute='_compute_display_name',
        store=True
    )
    asset_id = fields.Many2one(
        'asset.asset',
        string='Asset',
        required=True,
        ondelete='cascade',
        index=True,
        help='Asset that was moved'
    )
    movement_date = fields.Datetime(
        string='Movement Date',
        required=True,
        default=fields.Datetime.now,
        index=True,
        help='Date and time of movement'
    )

    # Location Change
    from_location_id = fields.Many2one(
        'asset.location',
        string='From Location',
        help='Previous location'
    )
    to_location_id = fields.Many2one(
        'asset.location',
        string='To Location',
        help='New location'
    )

    # Custodian Change
    from_custodian_id = fields.Many2one(
        'hr.employee',
        string='From Custodian',
        help='Previous custodian'
    )
    to_custodian_id = fields.Many2one(
        'hr.employee',
        string='To Custodian',
        help='New custodian'
    )

    # Movement Details
    reason = fields.Selection([
        ('assignment', 'Assignment'),
        ('transfer', 'Transfer'),
        ('return', 'Return'),
        ('maintenance', 'Maintenance'),
        ('other', 'Other'),
    ], string='Reason', default='transfer', required=True,
        help='Reason for the movement')
    notes = fields.Text(
        string='Notes',
        help='Additional information about the movement'
    )
    user_id = fields.Many2one(
        'res.users',
        string='Recorded By',
        default=lambda self: self.env.user,
        required=True,
        help='User who recorded this movement'
    )

    # Related Fields for Display
    asset_code = fields.Char(
        related='asset_id.asset_code',
        string='Asset Code',
        readonly=True,
        store=True
    )
    asset_name = fields.Char(
        related='asset_id.name',
        string='Asset Name',
        readonly=True,
        store=True
    )

    @api.depends('asset_id', 'movement_date', 'reason')
    def _compute_display_name(self):
        """Compute display name for movement record"""
        for movement in self:
            if movement.asset_id and movement.movement_date:
                reason_dict = dict(movement._fields['reason'].selection)
                reason_name = reason_dict.get(movement.reason, '')
                date_str = fields.Datetime.to_string(movement.movement_date)
                movement.display_name = f"{movement.asset_id.asset_code} - {reason_name} - {date_str}"
            else:
                movement.display_name = _('New Movement')

    def name_get(self):
        """Custom name_get to display meaningful information"""
        result = []
        for movement in self:
            name = movement.display_name or _('Movement')
            result.append((movement.id, name))
        return result

    @api.model
    def create_movement(self, asset_id, from_location=None, to_location=None,
                       from_custodian=None, to_custodian=None, reason='transfer', notes=''):
        """Helper method to create movement records"""
        return self.create({
            'asset_id': asset_id,
            'from_location_id': from_location,
            'to_location_id': to_location,
            'from_custodian_id': from_custodian,
            'to_custodian_id': to_custodian,
            'reason': reason,
            'notes': notes,
        })
