# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ConsentWithdrawalWizard(models.TransientModel):
    """
    Wizard for withdrawing consent (PDPA Compliance)

    Allows data subjects to withdraw their consent as required by
    PDPA Section 19 - Right to Withdraw Consent
    """
    _name = 'asset.consent.withdrawal.wizard'
    _description = 'Withdraw Consent Wizard'

    consent_log_id = fields.Many2one(
        'asset.consent.log',
        string='Consent Record',
        required=True,
        ondelete='cascade'
    )

    data_subject_name = fields.Char(
        related='consent_log_id.data_subject_name',
        string='Your Name',
        readonly=True
    )
    data_subject_email = fields.Char(
        related='consent_log_id.data_subject_email',
        string='Your Email',
        readonly=True
    )
    consent_type = fields.Selection(
        related='consent_log_id.consent_type',
        string='Consent Type',
        readonly=True
    )
    consent_date = fields.Datetime(
        related='consent_log_id.consent_date',
        string='Original Consent Date',
        readonly=True
    )

    withdrawal_reason = fields.Selection([
        ('no_longer_needed', 'No longer need the service'),
        ('privacy_concern', 'Privacy concerns'),
        ('found_alternative', 'Found alternative service'),
        ('not_satisfied', 'Not satisfied with data handling'),
        ('other', 'Other reason'),
    ], string='Reason for Withdrawal', required=True)

    withdrawal_reason_text = fields.Text(
        string='Additional Details',
        help='Please provide more details about your reason for withdrawing consent'
    )

    confirm_understanding = fields.Boolean(
        string='I understand that withdrawing consent may affect service delivery',
        required=True,
        help='Withdrawing consent may limit our ability to provide certain services'
    )

    # Consequences warning
    consequences = fields.Html(
        string='Consequences',
        compute='_compute_consequences',
        readonly=True
    )

    @api.depends('consent_type')
    def _compute_consequences(self):
        """Show consequences of withdrawing specific consent types"""
        for wizard in self:
            consequences_map = {
                'data_collection': '''
                    <div class="alert alert-warning">
                        <strong>⚠️ Important:</strong>
                        <ul>
                            <li>Your assignment records will be anonymized</li>
                            <li>You may not be able to borrow school assets in the future</li>
                            <li>Historical records will be retained for legal compliance</li>
                        </ul>
                    </div>
                ''',
                'digital_signature': '''
                    <div class="alert alert-warning">
                        <strong>⚠️ Important:</strong>
                        <ul>
                            <li>Existing signed documents will remain valid</li>
                            <li>Future transactions will require paper-based signatures</li>
                            <li>This may delay processing times</li>
                        </ul>
                    </div>
                ''',
                'email_communication': '''
                    <div class="alert alert-warning">
                        <strong>⚠️ Important:</strong>
                        <ul>
                            <li>You will no longer receive email notifications</li>
                            <li>Important updates must be collected in person</li>
                            <li>This may result in missed deadlines</li>
                        </ul>
                    </div>
                ''',
                'all': '''
                    <div class="alert alert-danger">
                        <strong>🚨 Critical:</strong>
                        <ul>
                            <li>All services requiring personal data will be terminated</li>
                            <li>You will need to return all borrowed assets immediately</li>
                            <li>Your account will be deactivated</li>
                            <li>Historical records retained only for legal compliance</li>
                        </ul>
                    </div>
                ''',
            }
            wizard.consequences = consequences_map.get(wizard.consent_type, '')

    def action_confirm_withdrawal(self):
        """Confirm and process consent withdrawal"""
        self.ensure_one()

        if not self.confirm_understanding:
            raise UserError(_('Please confirm that you understand the consequences of withdrawing consent.'))

        # Build withdrawal reason message
        reason_text = dict(self._fields['withdrawal_reason'].selection).get(self.withdrawal_reason)
        full_reason = f"{reason_text}"
        if self.withdrawal_reason_text:
            full_reason += f"\n\nDetails: {self.withdrawal_reason_text}"

        # Withdraw consent
        self.consent_log_id._withdraw_consent(reason=full_reason)

        # Log in related assignment
        if self.consent_log_id.student_assignment_id:
            self.consent_log_id.student_assignment_id.message_post(
                body=_('⚠️ Consent withdrawn by %s on %s. Reason: %s') % (
                    self.data_subject_name,
                    fields.Datetime.now().strftime('%Y-%m-%d %H:%M'),
                    reason_text
                ),
                subject=_('Consent Withdrawn')
            )
        elif self.consent_log_id.teacher_assignment_id:
            self.consent_log_id.teacher_assignment_id.message_post(
                body=_('⚠️ Consent withdrawn by %s on %s. Reason: %s') % (
                    self.data_subject_name,
                    fields.Datetime.now().strftime('%Y-%m-%d %H:%M'),
                    reason_text
                ),
                subject=_('Consent Withdrawn')
            )

        # Show confirmation message
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Consent Withdrawn'),
                'message': _('Your consent has been withdrawn successfully. You will receive a confirmation email shortly.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_cancel(self):
        """Cancel withdrawal process"""
        return {'type': 'ir.actions.act_window_close'}
