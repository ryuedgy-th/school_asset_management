# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrEmployeeAssetInfo(models.Model):
    """Inherit HR Employee to add asset assignment information"""
    _inherit = 'hr.employee'

    # Asset Assignment Count (Active only - not returned or cancelled)
    asset_assignment_count = fields.Integer(
        string='Asset Assignments',
        compute='_compute_asset_assignment_count',
        help='Number of currently active asset assignments (not returned or cancelled)'
    )

    # Current Assets for display in tab
    current_asset_ids = fields.Many2many(
        'asset.asset',
        string='Current Assets',
        compute='_compute_current_assets',
        help='Assets currently assigned to this employee'
    )
    current_asset_count = fields.Integer(
        string='Current Assets',
        compute='_compute_current_assets',
        help='Number of assets currently assigned'
    )

    @api.depends('name')
    def _compute_asset_assignment_count(self):
        """Compute active assignment count only (excluding returned and cancelled)"""
        for employee in self:
            # Count only active assignments (draft or checked_out)
            active_count = self.env['asset.teacher.assignment'].search_count([
                ('teacher_id', '=', employee.id),
                ('state', 'in', ['draft', 'checked_out'])
            ])
            employee.asset_assignment_count = active_count

    @api.depends('name')
    def _compute_current_assets(self):
        """Compute currently assigned assets"""
        for employee in self:
            active_assignments = self.env['asset.teacher.assignment'].search([
                ('teacher_id', '=', employee.id),
                ('state', 'in', ['draft', 'checked_out'])
            ])

            # Get all asset IDs from active assignment lines
            asset_ids = []
            for assignment in active_assignments:
                for line in assignment.asset_line_ids:
                    if line.asset_id:
                        asset_ids.append(line.asset_id.id)

            employee.current_asset_ids = [(6, 0, asset_ids)]
            employee.current_asset_count = len(asset_ids)

    def action_view_asset_assignments(self):
        """Open asset assignments for this employee"""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'school_asset_management.action_asset_teacher_assignment'
        )
        action.update({
            'name': f'Asset Assignments - {self.name}',
            'domain': [('teacher_id', '=', self.id)],
            'context': {
                'default_teacher_id': self.id,
                'search_default_teacher_id': self.id,
            },
        })
        return action
