# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AssetCategory(models.Model):
    """Asset Category Model for organizing assets hierarchically"""
    _name = 'asset.category'
    _description = 'Asset Category'
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name'

    name = fields.Char(
        string='Category Name',
        required=True,
        translate=True,
        index=True,
        help='Name of the asset category'
    )
    code = fields.Char(
        string='Category Code',
        index=True,
        help='Short code for the category'
    )
    parent_id = fields.Many2one(
        'asset.category',
        string='Parent Category',
        index=True,
        ondelete='cascade',
        help='Parent category for hierarchical structure'
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        'asset.category',
        'parent_id',
        string='Child Categories'
    )
    complete_name = fields.Char(
        'Complete Name',
        compute='_compute_complete_name',
        recursive=True,
        store=True
    )
    description = fields.Text(
        string='Description',
        translate=True,
        help='Detailed description of the category'
    )
    asset_count = fields.Integer(
        string='Asset Count',
        compute='_compute_asset_count',
        help='Number of assets in this category'
    )
    active = fields.Boolean(
        default=True,
        help='Set to false to hide the category without deleting it'
    )

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        """Compute the complete name with parent hierarchy"""
        for category in self:
            if category.parent_id:
                category.complete_name = f"{category.parent_id.complete_name} / {category.name}"
            else:
                category.complete_name = category.name

    @api.depends('child_ids')
    def _compute_asset_count(self):
        """Count assets in this category and all child categories"""
        for category in self:
            # Get all child category IDs including self
            child_ids = self.search([('id', 'child_of', category.id)]).ids
            category.asset_count = self.env['asset.asset'].search_count([
                ('category_id', 'in', child_ids)
            ])

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        """Prevent circular references in category hierarchy"""
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive categories.'))

    @api.constrains('code')
    def _check_code_unique(self):
        """Ensure category code is unique if provided"""
        for category in self:
            if category.code:
                existing = self.search([
                    ('code', '=', category.code),
                    ('id', '!=', category.id)
                ], limit=1)
                if existing:
                    raise ValidationError(_(
                        'Category code "%s" already exists. Please use a unique code.'
                    ) % category.code)

    def name_get(self):
        """Return the complete name for better readability"""
        result = []
        for record in self:
            name = record.complete_name or record.name
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
        """Open assets view filtered by this category"""
        self.ensure_one()
        child_ids = self.search([('id', 'child_of', self.id)]).ids
        return {
            'name': _('Assets'),
            'type': 'ir.actions.act_window',
            'res_model': 'asset.asset',
            'view_mode': 'list,form',
            'domain': [('category_id', 'in', child_ids)],
            'context': {'default_category_id': self.id},
        }
