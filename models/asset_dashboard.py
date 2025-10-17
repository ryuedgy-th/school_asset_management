# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AssetDashboard(models.TransientModel):
    """Dashboard model for asset statistics - always returns single record"""
    _name = 'asset.dashboard'
    _description = 'Asset Dashboard'

    name = fields.Char(string='Dashboard', default='Asset Dashboard')

    # Statistics computed fields
    total_assets = fields.Integer(compute='_compute_statistics', string='Total Assets')
    available_assets = fields.Integer(compute='_compute_statistics', string='Available')
    assigned_teacher = fields.Integer(compute='_compute_statistics', string='Assigned to Teachers')
    assigned_student = fields.Integer(compute='_compute_statistics', string='Assigned to Students')
    maintenance_assets = fields.Integer(compute='_compute_statistics', string='Under Maintenance/Repair')
    retired_assets = fields.Integer(compute='_compute_statistics', string='Retired')
    lost_assets = fields.Integer(compute='_compute_statistics', string='Lost')

    # Condition statistics
    excellent_condition = fields.Integer(compute='_compute_statistics', string='Excellent Condition')
    good_condition = fields.Integer(compute='_compute_statistics', string='Good Condition')
    fair_condition = fields.Integer(compute='_compute_statistics', string='Fair Condition')
    poor_condition = fields.Integer(compute='_compute_statistics', string='Poor Condition')

    # Warranty statistics
    warranty_active = fields.Integer(compute='_compute_statistics', string='Under Warranty')
    warranty_expiring = fields.Integer(compute='_compute_statistics', string='Warranty Expiring Soon')
    warranty_expired = fields.Integer(compute='_compute_statistics', string='Warranty Expired')

    # Financial
    total_asset_value = fields.Float(compute='_compute_statistics', string='Total Asset Value')
    average_age = fields.Float(compute='_compute_statistics', string='Average Age (Months)')

    # Assignment statistics
    active_teacher_assignments = fields.Integer(compute='_compute_statistics', string='Active Teacher Assignments')
    active_student_assignments = fields.Integer(compute='_compute_statistics', string='Active Student Assignments')
    overdue_returns = fields.Integer(compute='_compute_statistics', string='Overdue Returns')

    # Damage statistics
    total_damages = fields.Integer(compute='_compute_statistics', string='Total Damages Reported')
    total_damage_cost = fields.Float(compute='_compute_statistics', string='Total Damage Cost')

    @api.model
    def default_get(self, fields_list):
        """Override default_get to compute statistics on create"""
        res = super(AssetDashboard, self).default_get(fields_list)
        # Statistics will be computed automatically via compute fields
        return res

    @api.depends()
    def _compute_statistics(self):
        """Compute all dashboard statistics"""
        for dashboard in self:
            Asset = self.env['asset.asset']
            TeacherAssignment = self.env['asset.teacher.assignment']
            StudentAssignment = self.env['asset.student.assignment']

            # Asset statistics by status
            dashboard.total_assets = Asset.search_count([])
            dashboard.available_assets = Asset.search_count([('status', '=', 'available')])
            dashboard.assigned_teacher = Asset.search_count([('status', '=', 'assigned_teacher')])
            dashboard.assigned_student = Asset.search_count([('status', '=', 'assigned_student')])
            dashboard.maintenance_assets = Asset.search_count([('status', 'in', ('maintenance', 'repair'))])
            dashboard.retired_assets = Asset.search_count([('status', '=', 'retired')])
            dashboard.lost_assets = Asset.search_count([('status', '=', 'lost')])

            # Condition statistics
            dashboard.excellent_condition = Asset.search_count([('condition_rating', '=', 'excellent')])
            dashboard.good_condition = Asset.search_count([('condition_rating', '=', 'good')])
            dashboard.fair_condition = Asset.search_count([('condition_rating', '=', 'fair')])
            dashboard.poor_condition = Asset.search_count([('condition_rating', '=', 'poor')])

            # Warranty statistics
            dashboard.warranty_active = Asset.search_count([('warranty_status', '=', 'active')])
            dashboard.warranty_expiring = Asset.search_count([('is_warranty_expiring_soon', '=', True)])
            dashboard.warranty_expired = Asset.search_count([('warranty_status', '=', 'expired')])

            # Financial statistics
            assets = Asset.search([])
            dashboard.total_asset_value = sum(assets.mapped('purchase_cost'))
            dashboard.average_age = sum(assets.mapped('age_months')) / len(assets) if assets else 0

            # Assignment statistics
            dashboard.active_teacher_assignments = TeacherAssignment.search_count([('status', '=', 'active')])
            dashboard.active_student_assignments = StudentAssignment.search_count([('status', '=', 'checked_out')])
            dashboard.overdue_returns = StudentAssignment.search_count([('is_overdue', '=', True)])

            # Damage statistics
            teacher_damages = self.env['asset.assignment.line'].search_count([('damage_found', '=', True)])
            student_damages = self.env['asset.student.line'].search_count([('damage_found', '=', True)])
            dashboard.total_damages = teacher_damages + student_damages

            teacher_damage_cost = sum(self.env['asset.assignment.line'].search([('damage_found', '=', True)]).mapped('repair_cost'))
            student_damage_cost = sum(self.env['asset.student.line'].search([('damage_found', '=', True)]).mapped('repair_cost'))
            dashboard.total_damage_cost = teacher_damage_cost + student_damage_cost
