# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AssetLocation(models.Model):
    """Asset Location Model for tracking physical location of assets"""
    _name = 'asset.location'
    _description = 'Asset Location'
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name'

    name = fields.Char(
        string='Location Name',
        required=True,
        translate=True,
        index=True,
        help='Name of the location (e.g., Building A, Room 101)'
    )
    code = fields.Char(
        string='Location Code',
        index=True,
        help='Short code for the location (e.g., BLDG-A, RM-101)'
    )
    parent_id = fields.Many2one(
        'asset.location',
        string='Parent Location',
        index=True,
        ondelete='cascade',
        help='Parent location for hierarchical structure (Building > Floor > Room)'
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        'asset.location',
        'parent_id',
        string='Child Locations'
    )
    complete_name = fields.Char(
        'Complete Name',
        compute='_compute_complete_name',
        recursive=True,
        store=True
    )
    location_type = fields.Selection([
        ('campus', 'Campus'),
        ('building', 'Building'),
        ('floor', 'Floor'),
        ('room', 'Room'),
        ('other', 'Other'),
    ], string='Location Type', default='room', required=True,
        help='Type of location for organizational purposes')
    capacity = fields.Integer(
        string='Asset Capacity',
        help='Maximum number of assets that can be stored in this location'
    )
    description = fields.Text(
        string='Description',
        translate=True,
        help='Additional information about the location'
    )
    asset_count = fields.Integer(
        string='Asset Count',
        compute='_compute_asset_count',
        help='Number of assets currently in this location'
    )
    active = fields.Boolean(
        default=True,
        help='Set to false to hide the location without deleting it'
    )

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        """Compute the complete name with parent hierarchy"""
        for location in self:
            if location.parent_id:
                location.complete_name = f"{location.parent_id.complete_name} / {location.name}"
            else:
                location.complete_name = location.name

    @api.depends('child_ids')
    def _compute_asset_count(self):
        """Count assets in this location and all child locations"""
        for location in self:
            # Get all child location IDs including self
            child_ids = self.search([('id', 'child_of', location.id)]).ids
            location.asset_count = self.env['asset.asset'].search_count([
                ('location_id', 'in', child_ids)
            ])

    @api.constrains('parent_id')
    def _check_location_recursion(self):
        """Prevent circular references in location hierarchy"""
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive locations.'))

    @api.constrains('code')
    def _check_code_unique(self):
        """Ensure location code is unique if provided"""
        for location in self:
            if location.code:
                existing = self.search([
                    ('code', '=', location.code),
                    ('id', '!=', location.id)
                ], limit=1)
                if existing:
                    raise ValidationError(_(
                        'Location code "%s" already exists. Please use a unique code.'
                    ) % location.code)

    @api.constrains('capacity', 'asset_count')
    def _check_capacity(self):
        """Warn if asset count exceeds capacity"""
        for location in self:
            if location.capacity and location.asset_count > location.capacity:
                # This is just a warning, not blocking
                pass

    def name_get(self):
        """Return the complete name for better readability"""
        result = []
        for record in self:
            name = record.complete_name or record.name
            if record.code:
                name = f"[{record.code}] {name}"
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """Search by name or code"""
        domain = domain or []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)] + domain
        return self._search(domain, limit=limit, order=order)

    def action_view_assets(self):
        """Open assets view filtered by this location"""
        self.ensure_one()
        child_ids = self.search([('id', 'child_of', self.id)]).ids
        return {
            'name': _('Assets'),
            'type': 'ir.actions.act_window',
            'res_model': 'asset.asset',
            'view_mode': 'list,form',
            'domain': [('location_id', 'in', child_ids)],
            'context': {'default_location_id': self.id},
        }
