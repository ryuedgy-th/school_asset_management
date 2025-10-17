# -*- coding: utf-8 -*-

from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
from odoo.addons.school_asset_management.models.security_helpers import SignatureSecurityHelper
import logging
import base64
from datetime import datetime

_logger = logging.getLogger(__name__)


class StudentAssignmentSignatureController(http.Controller):
    """Public controller for parent signature on student asset assignments"""

    # ========================================================================
    # CHECKOUT SIGNATURE ROUTES
    # ========================================================================

    @http.route('/sign/student/checkout/<string:token>', type='http', auth='public', website=False, sitemap=False)
    def student_checkout_signature(self, token, **kwargs):
        """
        Public page for parent to sign checkout waiver

        Args:
            token: Secure token from email link

        Returns:
            Rendered template with assignment details and signature form
        """
        try:
            # Find assignment by token
            assignment = request.env['asset.student.assignment'].sudo().search([
                ('checkout_token', '=', token),
            ], limit=1)

            if not assignment:
                return request.render('school_asset_management.signature_error_page', {
                    'error_title': _('Invalid Link'),
                    'error_message': _('This signature link is invalid or has been removed.'),
                })

            # Validate token
            validation_result = assignment._validate_token(token, token_type='checkout')

            if validation_result == 'used':
                return request.render('school_asset_management.signature_already_signed_page', {
                    'assignment': assignment,
                    'message': _('This document has already been signed on %s.') % assignment.checkout_sign_date.strftime('%Y-%m-%d %H:%M') if assignment.checkout_sign_date else _('This document has already been signed.'),
                })

            if validation_result == 'expired':
                return request.render('school_asset_management.signature_error_page', {
                    'error_title': _('Link Expired'),
                    'error_message': _('This signature link has expired. Please contact the school IT department to request a new link.'),
                })

            if validation_result != 'valid':
                return request.render('school_asset_management.signature_error_page', {
                    'error_title': _('Invalid Link'),
                    'error_message': _('This signature link is not valid.'),
                })

            # Render signature page
            return request.render('school_asset_management.checkout_signature_page', {
                'assignment': assignment,
                'token': token,
                'student_name': assignment.student_name,
                'grade_level': assignment.grade_level,
                'parent_email': assignment.parent_email,
                'checkout_date': assignment.checkout_date,
                'asset_lines': assignment.asset_line_ids,
                'terms_template': 'school_asset_management.terms_and_conditions_student_assignment',
            })

        except Exception as e:
            _logger.error('Error in checkout signature page: %s', str(e))
            return request.render('school_asset_management.signature_error_page', {
                'error_title': _('Error'),
                'error_message': _('An error occurred while loading the signature page. Please contact the school IT department.'),
            })

    @http.route('/sign/student/checkout/submit', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def submit_checkout_signature(self, token, signature_data, parent_name, **kwargs):
        """
        Save checkout signature submitted by parent

        Args:
            token: Secure token
            signature_data: Base64 encoded signature image
            parent_name: Parent/Guardian full name

        Returns:
            JSON response with success/error status
        """
        try:
            # Security: Rate limiting check
            ip_address = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR',
                                                         request.httprequest.environ.get('REMOTE_ADDR', 'Unknown'))
            security_helper = SignatureSecurityHelper(request.env)
            is_allowed, attempts_left = security_helper.check_rate_limit(ip_address, 'signature')

            if not is_allowed:
                _logger.warning('Rate limit exceeded for IP %s on checkout signature', ip_address)
                return {
                    'success': False,
                    'error': _('Too many attempts. Please try again in 1 hour.')
                }

            # Find assignment
            assignment = request.env['asset.student.assignment'].sudo().search([
                ('checkout_token', '=', token),
            ], limit=1)

            if not assignment:
                security_helper = SignatureSecurityHelper(request.env)
                security_helper.log_failed_attempt(ip_address, token, 'checkout_signature')
                # Enhanced audit logging
                request.env['asset.security.audit.log'].sudo().log_signature_attempt(
                    event_type='token_invalid',
                    signature_type='checkout',
                    ip_address=ip_address,
                    token=token,
                    error_message='Invalid checkout signature link',
                    user_agent=request.httprequest.headers.get('User-Agent')
                )
                return {'success': False, 'error': _('Invalid signature link.')}

            # Validate token
            validation_result = assignment._validate_token(token, token_type='checkout')

            if validation_result != 'valid':
                error_messages = {
                    'used': _('This document has already been signed.'),
                    'expired': _('This signature link has expired.'),
                }
                return {'success': False, 'error': error_messages.get(validation_result, _('Invalid signature link.'))}

            # Validate signature data
            if not signature_data or not parent_name:
                return {'success': False, 'error': _('Please provide your name and signature.')}

            # Security: Validate signature size (prevent DoS)
            if len(signature_data) > 200000:  # 200KB limit
                return {'success': False, 'error': _('Signature file is too large. Please try again.')}

            # Get IP address
            ip_address = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR',
                                                         request.httprequest.environ.get('REMOTE_ADDR', 'Unknown'))
            user_agent = request.httprequest.headers.get('User-Agent', 'Unknown')

            # PDPA Compliance: Log consent before saving signature
            # Get consent data from form (these should be passed from the frontend)
            consents_given = kwargs.get('consents', {})

            # Log consent records
            consent_model = request.env['asset.consent.log'].sudo()

            # Data collection consent
            if consents_given.get('consent_data_collection'):
                consent_model.log_consent(
                    consent_type='data_collection',
                    user_type='parent',
                    data_subject_name=parent_name,
                    data_subject_email=assignment.parent_email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    privacy_version=assignment.privacy_policy_version or '1.0',
                    student_assignment_id=assignment.id,
                    purpose='Asset management and borrowing records',
                    consent_method='online'
                )

            # Digital signature consent
            if consents_given.get('consent_digital_signature'):
                consent_model.log_consent(
                    consent_type='digital_signature',
                    user_type='parent',
                    data_subject_name=parent_name,
                    data_subject_email=assignment.parent_email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    privacy_version=assignment.privacy_policy_version or '1.0',
                    student_assignment_id=assignment.id,
                    purpose='Electronic signature for asset borrowing confirmation',
                    consent_method='online'
                )

            # Email communication consent
            if consents_given.get('consent_email'):
                consent_model.log_consent(
                    consent_type='email_communication',
                    user_type='parent',
                    data_subject_name=parent_name,
                    data_subject_email=assignment.parent_email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    privacy_version=assignment.privacy_policy_version or '1.0',
                    student_assignment_id=assignment.id,
                    purpose='Notifications and communications regarding asset borrowing',
                    consent_method='online'
                )

            # Liability agreement consent
            if consents_given.get('consent_liability'):
                consent_model.log_consent(
                    consent_type='damage_liability',
                    user_type='parent',
                    data_subject_name=parent_name,
                    data_subject_email=assignment.parent_email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    privacy_version=assignment.privacy_policy_version or '1.0',
                    student_assignment_id=assignment.id,
                    purpose='Acknowledgment of liability for damaged/lost assets',
                    consent_method='online'
                )

            # Save signature
            assignment._save_checkout_signature(signature_data, parent_name, ip_address)

            # Log successful signature in security audit
            request.env['asset.security.audit.log'].sudo().log_signature_attempt(
                event_type='signature_success',
                signature_type='checkout',
                ip_address=ip_address,
                token=token,
                related_model='asset.student.assignment',
                related_id=assignment.id,
                student_name=assignment.student_name,
                parent_email=assignment.parent_email,
                user_agent=user_agent
            )

            return {
                'success': True,
                'message': _('Thank you! Your signature has been recorded successfully. You will receive a confirmation email shortly.'),
            }

        except Exception as e:
            _logger.exception('Error submitting checkout signature')
            return {
                'success': False,
                'error': _('An error occurred while saving your signature. Please try again or contact the school IT department.'),
            }

    # ========================================================================
    # DAMAGE REPORT ROUTES
    # ========================================================================

    @http.route('/sign/student/damage/<string:token>', type='http', auth='public', website=False, sitemap=False)
    def student_damage_report(self, token, **kwargs):
        """
        Public page for parent to acknowledge damage report

        Args:
            token: Secure token from email link

        Returns:
            Rendered template with damage details and signature form
        """
        try:
            # Find assignment by damage token
            assignment = request.env['asset.student.assignment'].sudo().search([
                ('damage_report_token', '=', token),
            ], limit=1)

            if not assignment:
                return request.render('school_asset_management.signature_error_page', {
                    'error_title': _('Invalid Link'),
                    'error_message': _('This damage report link is invalid or has been removed.'),
                })

            # Validate token
            validation_result = assignment._validate_token(token, token_type='damage')

            if validation_result == 'used':
                return request.render('school_asset_management.signature_already_signed_page', {
                    'assignment': assignment,
                    'message': _('This damage report has already been acknowledged on %s.') % assignment.damage_acknowledge_date.strftime('%Y-%m-%d %H:%M') if assignment.damage_acknowledge_date else _('This damage report has already been acknowledged.'),
                })

            if validation_result == 'expired':
                return request.render('school_asset_management.signature_error_page', {
                    'error_title': _('Link Expired'),
                    'error_message': _('This damage report link has expired. Please contact the school IT department.'),
                })

            if validation_result != 'valid':
                return request.render('school_asset_management.signature_error_page', {
                    'error_title': _('Invalid Link'),
                    'error_message': _('This damage report link is not valid.'),
                })

            # Get damaged assets
            _logger.info('Assignment ID: %s, Student: %s', assignment.id, assignment.student_name)
            damaged_assets = assignment.asset_line_ids.filtered(lambda l: l.damage_found)
            _logger.info('Found %d damaged assets', len(damaged_assets))

            if not damaged_assets:
                _logger.warning('No damaged assets found for assignment %s', assignment.id)
                return request.render('school_asset_management.signature_error_page', {
                    'error_title': _('No Damages Found'),
                    'error_message': _('No damaged assets were found for this assignment. Please contact the school IT department.'),
                })

            # Render damage report page
            return request.render('school_asset_management.damage_report_page', {
                'assignment': assignment,
                'token': token,
                'student_name': assignment.student_name or '',
                'grade_level': assignment.grade_level or '',
                'parent_email': assignment.parent_email or '',
                'parent_name': assignment.parent_name or '',
                'damaged_assets': damaged_assets,
                'total_repair_cost': assignment.total_damage_cost or 0.0,
                'checkin_date': assignment.actual_return_date,
            })

        except Exception as e:
            _logger.exception('Error in damage report page: %s', str(e))
            return request.render('school_asset_management.signature_error_page', {
                'error_title': _('Error'),
                'error_message': _('An error occurred while loading the damage report. Please contact the school IT department.'),
            })

    @http.route('/sign/student/damage/submit', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def submit_damage_acknowledgment(self, token, signature_data, **kwargs):
        """
        Save damage acknowledgment signature

        Args:
            token: Secure token
            signature_data: Base64 encoded signature image

        Returns:
            JSON response with success/error status
        """
        try:
            # Security: Rate limiting check
            ip_address = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR',
                                                         request.httprequest.environ.get('REMOTE_ADDR', 'Unknown'))
            security_helper = SignatureSecurityHelper(request.env)
            is_allowed, attempts_left = security_helper.check_rate_limit(ip_address, 'signature')

            if not is_allowed:
                _logger.warning('Rate limit exceeded for IP %s on damage acknowledgment', ip_address)
                return {
                    'success': False,
                    'error': _('Too many attempts. Please try again in 1 hour.')
                }

            # Find assignment
            assignment = request.env['asset.student.assignment'].sudo().search([
                ('damage_report_token', '=', token),
            ], limit=1)

            if not assignment:
                security_helper = SignatureSecurityHelper(request.env)
                security_helper.log_failed_attempt(ip_address, token, 'damage_acknowledgment')
                return {'success': False, 'error': _('Invalid damage report link.')}

            # Validate token
            validation_result = assignment._validate_token(token, token_type='damage')

            if validation_result != 'valid':
                error_messages = {
                    'used': _('This damage report has already been acknowledged.'),
                    'expired': _('This damage report link has expired.'),
                }
                return {'success': False, 'error': error_messages.get(validation_result, _('Invalid damage report link.'))}

            # Validate signature data
            if not signature_data:
                return {'success': False, 'error': _('Please provide your signature to acknowledge the damage report.')}

            # Security: Validate signature size (prevent DoS)
            if len(signature_data) > 200000:  # 200KB limit
                return {'success': False, 'error': _('Signature file is too large. Please try again.')}

            # Get IP address
            ip_address = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR',
                                                         request.httprequest.environ.get('REMOTE_ADDR', 'Unknown'))

            # Save signature
            assignment._save_damage_signature(signature_data, ip_address)

            return {
                'success': True,
                'message': _('Thank you for acknowledging the damage report. You will receive a confirmation email with the damage assessment details.'),
            }

        except Exception as e:
            _logger.error('Error submitting damage acknowledgment: %s', str(e))
            return {
                'success': False,
                'error': _('An error occurred while saving your acknowledgment. Please try again or contact the school IT department.'),
            }


class DamageCaseApprovalController(http.Controller):
    """Public controller for manager approval signature on damage cases"""

    @http.route('/damage/approve/<string:token>', type='http', auth='public', website=False, sitemap=False)
    def damage_case_approval(self, token, **kwargs):
        """
        Public page for manager to approve/reject damage case

        Args:
            token: Secure token from email link

        Returns:
            Rendered template with damage case details and approval form
        """
        try:
            # Find damage case by token
            damage_case = request.env['asset.damage.case'].sudo().search([
                ('approval_token', '=', token),
            ], limit=1)

            if not damage_case:
                return request.render('school_asset_management.signature_error_page', {
                    'error_title': 'Invalid Link',
                    'error_message': 'This approval link is invalid or has been removed.',
                })

            # Check if already signed
            if damage_case.approval_token_used or damage_case.approval_signature:
                return request.render('school_asset_management.signature_already_signed_page', {
                    'assignment': damage_case,  # Use same template variable
                    'message': 'This damage case approval has already been signed on %s.' % damage_case.approval_signature_date.strftime('%Y-%m-%d %H:%M') if damage_case.approval_signature_date else 'This damage case approval has already been signed.',
                })

            # Check if expired
            if damage_case.approval_token_expiry and damage_case.approval_token_expiry < fields.Datetime.now():
                return request.render('school_asset_management.signature_error_page', {
                    'error_title': 'Link Expired',
                    'error_message': 'This approval link has expired. Please contact IT department to request a new link.',
                })

            # Render approval page
            return request.render('school_asset_management.damage_case_approval_page', {
                'damage_case': damage_case,
                'token': token,
                'asset_code': damage_case.asset_code or 'N/A',
                'asset_name': damage_case.asset_id.name or 'N/A',
                'damage_description': damage_case.damage_description or '',
                'estimated_cost': damage_case.estimated_cost or 0.0,
                'responsible_type': dict(damage_case._fields['responsible_type'].selection).get(damage_case.responsible_type, 'N/A') if damage_case.responsible_type else 'N/A',
                'responsible_name': damage_case.responsible_teacher_id.name if damage_case.responsible_teacher_id else damage_case.responsible_student_name or 'N/A',
                'damage_date': damage_case.damage_date,
                'reported_by': damage_case.reported_by.name if damage_case.reported_by else 'N/A',
            })

        except Exception as e:
            _logger.exception('Error in damage case approval page: %s', str(e))
            return request.render('school_asset_management.signature_error_page', {
                'error_title': 'Error',
                'error_message': 'An error occurred while loading the approval page. Please contact IT department.',
            })

    @http.route('/damage/approve/submit', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def submit_damage_case_approval(self, token, signature_data, decision, notes='', **kwargs):
        """
        Save damage case approval/rejection

        Args:
            token: Secure token
            signature_data: Base64 encoded signature image
            decision: 'approve' or 'reject'
            notes: Optional approval notes

        Returns:
            JSON response with success/error status
        """
        try:
            # Security: Rate limiting check
            ip_address = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR',
                                                         request.httprequest.environ.get('REMOTE_ADDR', 'Unknown'))
            security_helper = SignatureSecurityHelper(request.env)
            is_allowed, attempts_left = security_helper.check_rate_limit(ip_address, 'signature')

            if not is_allowed:
                _logger.warning('Rate limit exceeded for IP %s on damage case approval', ip_address)
                return {
                    'success': False,
                    'error': 'Too many attempts. Please try again in 1 hour.'
                }

            # Find damage case
            damage_case = request.env['asset.damage.case'].sudo().search([
                ('approval_token', '=', token),
            ], limit=1)

            if not damage_case:
                security_helper = SignatureSecurityHelper(request.env)
                security_helper.log_failed_attempt(ip_address, token, 'damage_approval')
                return {'success': False, 'error': 'Invalid approval link.'}

            # Check if already signed
            if damage_case.approval_token_used or damage_case.approval_signature:
                return {'success': False, 'error': 'This damage case has already been approved/rejected.'}

            # Check if expired
            if damage_case.approval_token_expiry and damage_case.approval_token_expiry < fields.Datetime.now():
                return {'success': False, 'error': 'This approval link has expired.'}

            # Validate signature data
            if not signature_data:
                return {'success': False, 'error': 'Please provide your signature.'}

            # Security: Validate signature size (prevent DoS)
            if len(signature_data) > 200000:  # 200KB limit
                return {'success': False, 'error': 'Signature file is too large. Please try again.'}

            # Validate decision
            if decision not in ('approve', 'reject'):
                return {'success': False, 'error': 'Invalid decision.'}

            # Remove data:image header if present
            if 'base64,' in signature_data:
                signature_data = signature_data.split('base64,')[1]

            # Get IP address
            ip_address = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR',
                                                         request.httprequest.environ.get('REMOTE_ADDR', 'Unknown'))

            # Save approval
            approval_status = 'approved' if decision == 'approve' else 'rejected'
            status = 'approved' if decision == 'approve' else 'rejected'

            damage_case.write({
                'approval_signature': signature_data,
                'approval_status': approval_status,
                'status': status,
                'approval_signature_date': fields.Datetime.now(),
                'approval_signature_ip': ip_address,
                'approval_token_used': True,
                'approval_date': fields.Datetime.now(),
                'approval_notes': notes,
                'approver_id': damage_case.env.user.id if not damage_case.env.user._is_public() else False,
            })

            # Generate signed PDF
            try:
                pdf_report = request.env.ref('school_asset_management.action_report_damage_case_approval')
                pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
                    pdf_report.id,
                    [damage_case.id]
                )

                # Create attachment
                pdf_attachment = request.env['ir.attachment'].sudo().create({
                    'name': f'Damage_Case_Approval_{damage_case.name}.pdf',
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': 'asset.damage.case',
                    'res_id': damage_case.id,
                    'mimetype': 'application/pdf',
                })

                damage_case.write({
                    'approval_signed_pdf_id': pdf_attachment.id,
                })

            except Exception as pdf_error:
                _logger.error('Error generating signed PDF for damage case %s: %s', damage_case.id, str(pdf_error))

            # Log message
            action_text = 'approved' if decision == 'approve' else 'rejected'
            damage_case.message_post(
                body=f'Damage case {action_text} by manager (IP: {ip_address}). Notes: {notes or "None"}',
                subject=f'Case {action_text.title()}'
            )

            message = 'Thank you for approving this damage case. The IT department will proceed with the repair.' if decision == 'approve' else 'This damage case has been rejected. The IT department will be notified.'

            return {
                'success': True,
                'message': message,
            }

        except Exception as e:
            _logger.exception('Error submitting damage case approval: %s', str(e))
            return {
                'success': False,
                'error': 'An error occurred while saving your decision. Please try again or contact IT department.',
            }


class TeacherAssignmentSignatureController(http.Controller):
    """Public controller for teacher signature on asset assignments"""

    # ========================================================================
    # TEACHER CHECKOUT SIGNATURE ROUTES
    # ========================================================================

    @http.route('/sign/teacher/checkout/<string:token>', type='http', auth='public', website=False, sitemap=False)
    def teacher_checkout_signature(self, token, **kwargs):
        """
        Public page for teacher to sign checkout waiver

        Args:
            token: Secure token from email link

        Returns:
            Rendered template with assignment details and signature form
        """
        try:
            # Find assignment by token
            assignment = request.env['asset.teacher.assignment'].sudo().search([
                ('checkout_token', '=', token),
            ], limit=1)

            if not assignment:
                return request.render('school_asset_management.signature_error_page', {
                    'error_title': _('Invalid Link'),
                    'error_message': _('This signature link is invalid or has been removed.'),
                })

            # Validate token
            validation_result = assignment._validate_token(token, token_type='checkout')

            if validation_result == 'used':
                return request.render('school_asset_management.signature_already_signed_page', {
                    'assignment': assignment,
                    'message': _('This document has already been signed on %s.') % assignment.checkout_sign_date.strftime('%Y-%m-%d %H:%M') if assignment.checkout_sign_date else _('This document has already been signed.'),
                })

            if validation_result == 'expired':
                return request.render('school_asset_management.signature_error_page', {
                    'error_title': _('Link Expired'),
                    'error_message': _('This signature link has expired. Please contact the IT department to request a new link.'),
                })

            if validation_result != 'valid':
                return request.render('school_asset_management.signature_error_page', {
                    'error_title': _('Invalid Link'),
                    'error_message': _('This signature link is not valid.'),
                })

            # Render signature page
            return request.render('school_asset_management.teacher_checkout_signature_page', {
                'assignment': assignment,
                'token': token,
                'teacher_name': assignment.teacher_id.name,
                'teacher_email': assignment.teacher_email,
                'checkout_date': assignment.checkout_date,
                'asset_lines': assignment.asset_line_ids,
                'terms_template': 'school_asset_management.terms_and_conditions_teacher_assignment',
            })

        except Exception as e:
            _logger.error('Error in teacher checkout signature page: %s', str(e))
            return request.render('school_asset_management.signature_error_page', {
                'error_title': _('Error'),
                'error_message': _('An error occurred while loading the signature page. Please contact the IT department.'),
            })

    @http.route('/sign/teacher/checkout/submit', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def submit_teacher_checkout_signature(self, token, signature_data, **kwargs):
        """
        Save checkout signature submitted by teacher

        Args:
            token: Secure token
            signature_data: Base64 encoded signature image

        Returns:
            JSON response with success/error status
        """
        try:
            # Security: Rate limiting check
            ip_address = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR',
                                                         request.httprequest.environ.get('REMOTE_ADDR', 'Unknown'))
            security_helper = SignatureSecurityHelper(request.env)
            is_allowed, attempts_left = security_helper.check_rate_limit(ip_address, 'signature')

            if not is_allowed:
                _logger.warning('Rate limit exceeded for IP %s on teacher checkout signature', ip_address)
                return {
                    'success': False,
                    'error': _('Too many attempts. Please try again in 1 hour.')
                }

            # Find assignment
            assignment = request.env['asset.teacher.assignment'].sudo().search([
                ('checkout_token', '=', token),
            ], limit=1)

            if not assignment:
                security_helper = SignatureSecurityHelper(request.env)
                security_helper.log_failed_attempt(ip_address, token, 'teacher_checkout_signature')
                # Enhanced audit logging
                request.env['asset.security.audit.log'].sudo().log_signature_attempt(
                    event_type='token_invalid',
                    signature_type='teacher_checkout',
                    ip_address=ip_address,
                    token=token,
                    error_message='Invalid teacher checkout signature link',
                    user_agent=request.httprequest.headers.get('User-Agent')
                )
                return {'success': False, 'error': _('Invalid signature link.')}

            # Validate token
            validation_result = assignment._validate_token(token, token_type='checkout')

            if validation_result != 'valid':
                error_messages = {
                    'used': _('This document has already been signed.'),
                    'expired': _('This signature link has expired.'),
                }
                return {'success': False, 'error': error_messages.get(validation_result, _('Invalid signature link.'))}

            # Validate signature data
            if not signature_data:
                return {'success': False, 'error': _('Please provide your signature.')}

            # Security: Validate signature size (prevent DoS)
            if len(signature_data) > 200000:  # 200KB limit
                return {'success': False, 'error': _('Signature file is too large. Please try again.')}

            # Get IP address
            ip_address = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR',
                                                         request.httprequest.environ.get('REMOTE_ADDR', 'Unknown'))
            user_agent = request.httprequest.headers.get('User-Agent', 'Unknown')

            # PDPA Compliance: Log consent before saving signature
            consents_given = kwargs.get('consents', {})
            consent_model = request.env['asset.consent.log'].sudo()
            teacher_name = assignment.teacher_id.name if assignment.teacher_id else 'Unknown'

            # Data collection consent
            if consents_given.get('consent_data_collection'):
                consent_model.log_consent(
                    consent_type='data_collection',
                    user_type='teacher',
                    data_subject_name=teacher_name,
                    data_subject_email=assignment.teacher_email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    privacy_version='1.0',
                    teacher_assignment_id=assignment.id,
                    purpose='Asset management and borrowing records',
                    consent_method='online'
                )

            # Digital signature consent
            if consents_given.get('consent_digital_signature'):
                consent_model.log_consent(
                    consent_type='digital_signature',
                    user_type='teacher',
                    data_subject_name=teacher_name,
                    data_subject_email=assignment.teacher_email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    privacy_version='1.0',
                    teacher_assignment_id=assignment.id,
                    purpose='Electronic signature for asset borrowing confirmation',
                    consent_method='online'
                )

            # Email communication consent
            if consents_given.get('consent_email'):
                consent_model.log_consent(
                    consent_type='email_communication',
                    user_type='teacher',
                    data_subject_name=teacher_name,
                    data_subject_email=assignment.teacher_email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    privacy_version='1.0',
                    teacher_assignment_id=assignment.id,
                    purpose='Notifications and communications regarding asset borrowing',
                    consent_method='online'
                )

            # Liability agreement consent
            if consents_given.get('consent_liability'):
                consent_model.log_consent(
                    consent_type='damage_liability',
                    user_type='teacher',
                    data_subject_name=teacher_name,
                    data_subject_email=assignment.teacher_email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    privacy_version='1.0',
                    teacher_assignment_id=assignment.id,
                    purpose='Acknowledgment of liability for damaged/lost assets',
                    consent_method='online'
                )

            # Save signature
            assignment._save_checkout_signature(signature_data, ip_address)

            # Log successful signature in security audit
            request.env['asset.security.audit.log'].sudo().log_signature_attempt(
                event_type='signature_success',
                signature_type='teacher_checkout',
                ip_address=ip_address,
                token=token,
                related_model='asset.teacher.assignment',
                related_id=assignment.id,
                teacher_name=teacher_name,
                teacher_email=assignment.teacher_email,
                user_agent=user_agent
            )

            return {
                'success': True,
                'message': _('Thank you! Your signature has been recorded successfully. You will receive a confirmation email shortly.'),
            }

        except Exception as e:
            _logger.exception('Error submitting teacher checkout signature')
            return {
                'success': False,
                'error': _('An error occurred while saving your signature. Please try again or contact the IT department.'),
            }

    # ========================================================================
    # TEACHER DAMAGE REPORT ROUTES
    # ========================================================================

    @http.route('/sign/teacher/damage/<string:token>', type='http', auth='public', website=False, sitemap=False)
    def teacher_damage_report(self, token, **kwargs):
        """
        Public page for teacher to acknowledge damage report

        Args:
            token: Secure token from email link

        Returns:
            Rendered template with damage details and signature form
        """
        try:
            # Find assignment by damage token
            assignment = request.env['asset.teacher.assignment'].sudo().search([
                ('damage_report_token', '=', token),
            ], limit=1)

            if not assignment:
                return request.render('school_asset_management.signature_error_page', {
                    'error_title': _('Invalid Link'),
                    'error_message': _('This damage report link is invalid or has been removed.'),
                })

            # Validate token
            validation_result = assignment._validate_token(token, token_type='damage')

            if validation_result == 'used':
                return request.render('school_asset_management.signature_already_signed_page', {
                    'assignment': assignment,
                    'message': _('This damage report has already been acknowledged on %s.') % assignment.damage_acknowledge_date.strftime('%Y-%m-%d %H:%M') if assignment.damage_acknowledge_date else _('This damage report has already been acknowledged.'),
                })

            if validation_result == 'expired':
                return request.render('school_asset_management.signature_error_page', {
                    'error_title': _('Link Expired'),
                    'error_message': _('This damage report link has expired. Please contact the IT department.'),
                })

            if validation_result != 'valid':
                return request.render('school_asset_management.signature_error_page', {
                    'error_title': _('Invalid Link'),
                    'error_message': _('This damage report link is not valid.'),
                })

            # Get damaged assets
            damaged_assets = assignment.asset_line_ids.filtered(lambda l: l.damage_found)

            if not damaged_assets:
                return request.render('school_asset_management.signature_error_page', {
                    'error_title': _('No Damages Found'),
                    'error_message': _('No damaged assets were found for this assignment. Please contact the IT department.'),
                })

            # Render damage report page
            return request.render('school_asset_management.teacher_damage_report_page', {
                'assignment': assignment,
                'token': token,
                'teacher_name': assignment.teacher_id.name,
                'teacher_email': assignment.teacher_email,
                'damaged_assets': damaged_assets,
                'checkin_date': assignment.actual_return_date,
            })

        except Exception as e:
            _logger.exception('Error in teacher damage report page: %s', str(e))
            return request.render('school_asset_management.signature_error_page', {
                'error_title': _('Error'),
                'error_message': _('An error occurred while loading the damage report. Please contact the IT department.'),
            })

    @http.route('/sign/teacher/damage/submit', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def submit_teacher_damage_acknowledgment(self, token, signature_data, **kwargs):
        """
        Save damage acknowledgment signature

        Args:
            token: Secure token
            signature_data: Base64 encoded signature image

        Returns:
            JSON response with success/error status
        """
        try:
            # Security: Rate limiting check
            ip_address = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR',
                                                         request.httprequest.environ.get('REMOTE_ADDR', 'Unknown'))
            security_helper = SignatureSecurityHelper(request.env)
            is_allowed, attempts_left = security_helper.check_rate_limit(ip_address, 'signature')

            if not is_allowed:
                _logger.warning('Rate limit exceeded for IP %s on teacher damage acknowledgment', ip_address)
                return {
                    'success': False,
                    'error': _('Too many attempts. Please try again in 1 hour.')
                }

            # Find assignment
            assignment = request.env['asset.teacher.assignment'].sudo().search([
                ('damage_report_token', '=', token),
            ], limit=1)

            if not assignment:
                security_helper = SignatureSecurityHelper(request.env)
                security_helper.log_failed_attempt(ip_address, token, 'teacher_damage_acknowledgment')
                return {'success': False, 'error': _('Invalid damage report link.')}

            # Validate token
            validation_result = assignment._validate_token(token, token_type='damage')

            if validation_result != 'valid':
                error_messages = {
                    'used': _('This damage report has already been acknowledged.'),
                    'expired': _('This damage report link has expired.'),
                }
                return {'success': False, 'error': error_messages.get(validation_result, _('Invalid damage report link.'))}

            # Validate signature data
            if not signature_data:
                return {'success': False, 'error': _('Please provide your signature to acknowledge the damage report.')}

            # Security: Validate signature size (prevent DoS)
            if len(signature_data) > 200000:  # 200KB limit
                return {'success': False, 'error': _('Signature file is too large. Please try again.')}

            # Get IP address
            ip_address = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR',
                                                         request.httprequest.environ.get('REMOTE_ADDR', 'Unknown'))

            # Save signature
            assignment._save_damage_signature(signature_data, ip_address)

            return {
                'success': True,
                'message': _('Thank you for acknowledging the damage report. You will receive a confirmation email with the damage assessment details.'),
            }

        except Exception as e:
            _logger.error('Error submitting teacher damage acknowledgment: %s', str(e))
            return {
                'success': False,
                'error': _('An error occurred while saving your acknowledgment. Please try again or contact the IT department.'),
            }


class InspectionDamageSignatureController(http.Controller):
    """Public controller for parent signature on inspection damage reports"""

    @http.route('/sign/inspection/damage/<string:token>', type='http', auth='public', website=False, sitemap=False)
    def inspection_damage_signature(self, token, **kwargs):
        """
        Public page for parent to sign inspection damage acknowledgment

        Args:
            token: Secure token from email link

        Returns:
            Rendered template with inspection damage details and signature form
        """
        try:
            # Find inspection by token
            inspection = request.env['asset.inspection'].sudo().search([
                ('damage_token', '=', token),
            ], limit=1)

            if not inspection:
                return request.render('school_asset_management.signature_error_page', {
                    'error_title': _('Invalid Link'),
                    'error_message': _('This signature link is invalid or has been removed.'),
                })

            # Check if already signed
            if inspection.damage_token_used or inspection.parent_damage_acknowledged:
                return request.render('school_asset_management.signature_already_signed_page', {
                    'assignment': inspection,  # Use same template variable name
                    'message': _('This damage report has already been acknowledged on %s.') % inspection.parent_signature_date.strftime('%Y-%m-%d %H:%M') if inspection.parent_signature_date else _('This damage report has already been acknowledged.'),
                })

            # Check if expired
            if inspection.damage_token_expiry and inspection.damage_token_expiry < fields.Datetime.now():
                return request.render('school_asset_management.signature_error_page', {
                    'error_title': _('Link Expired'),
                    'error_message': _('This signature link has expired. Please contact the school IT department to request a new link.'),
                })

            # Check if damage was found for student custodian
            if not inspection.damage_found or inspection.custodian_type != 'student':
                return request.render('school_asset_management.signature_error_page', {
                    'error_title': _('Invalid Link'),
                    'error_message': _('This damage acknowledgment link is not valid.'),
                })

            # Render signature page
            return request.render('school_asset_management.inspection_damage_signature_page', {
                'inspection': inspection,
                'token': token,
                'student_name': inspection.student_name or '',
                'parent_name': inspection.parent_name or '',
                'parent_email': inspection.parent_email or '',
                'asset_code': inspection.asset_id.asset_code,
                'asset_name': inspection.asset_id.name or 'N/A',
                'inspection_date': inspection.inspection_date,
                'damage_description': inspection.damage_description or '',
                'repair_cost': inspection.repair_cost or 0.0,
                'condition_before': dict(inspection._fields['condition_before'].selection).get(inspection.condition_before, 'N/A') if inspection.condition_before else 'N/A',
                'condition_after': dict(inspection._fields['condition_after'].selection).get(inspection.condition_after, 'N/A'),
                'inspection_type': dict(inspection._fields['inspection_type'].selection).get(inspection.inspection_type, 'N/A'),
                'inspector_name': inspection.inspector_id.name,
            })

        except Exception as e:
            _logger.exception('Error in inspection damage signature page: %s', str(e))
            return request.render('school_asset_management.signature_error_page', {
                'error_title': _('Error'),
                'error_message': _('An error occurred while loading the signature page. Please contact the school IT department.'),
            })

    @http.route('/sign/inspection/damage/submit', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def submit_inspection_damage_acknowledgment(self, token, signature_data, **kwargs):
        """
        Save inspection damage acknowledgment signature

        Args:
            token: Secure token
            signature_data: Base64 encoded signature image

        Returns:
            JSON response with success/error status
        """
        try:
            # Security: Rate limiting check
            ip_address = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR',
                                                         request.httprequest.environ.get('REMOTE_ADDR', 'Unknown'))
            security_helper = SignatureSecurityHelper(request.env)
            is_allowed, attempts_left = security_helper.check_rate_limit(ip_address, 'signature')

            if not is_allowed:
                _logger.warning('Rate limit exceeded for IP %s on inspection damage acknowledgment', ip_address)
                return {
                    'success': False,
                    'error': _('Too many attempts. Please try again in 1 hour.')
                }

            # Find inspection
            inspection = request.env['asset.inspection'].sudo().search([
                ('damage_token', '=', token),
            ], limit=1)

            if not inspection:
                security_helper = SignatureSecurityHelper(request.env)
                security_helper.log_failed_attempt(ip_address, token, 'inspection_damage')
                return {'success': False, 'error': _('Invalid damage acknowledgment link.')}

            # Check if already signed
            if inspection.damage_token_used or inspection.parent_damage_acknowledged:
                return {'success': False, 'error': _('This damage report has already been acknowledged.')}

            # Check if expired
            if inspection.damage_token_expiry and inspection.damage_token_expiry < fields.Datetime.now():
                return {'success': False, 'error': _('This damage acknowledgment link has expired.')}

            # Validate signature data
            if not signature_data:
                return {'success': False, 'error': _('Please provide your signature to acknowledge the damage report.')}

            # Security: Validate signature size (prevent DoS)
            if len(signature_data) > 200000:  # 200KB limit
                return {'success': False, 'error': _('Signature file is too large. Please try again.')}

            # Remove data:image header if present
            if 'base64,' in signature_data:
                signature_data = signature_data.split('base64,')[1]

            # Get IP address
            ip_address = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR',
                                                         request.httprequest.environ.get('REMOTE_ADDR', 'Unknown'))

            # Save signature
            inspection.write({
                'parent_signature': signature_data,
                'parent_damage_acknowledged': True,
                'parent_signature_date': fields.Datetime.now(),
                'parent_signature_ip': ip_address,
                'damage_token_used': True,
            })

            # Generate signed PDF
            try:
                pdf_report = request.env.ref('school_asset_management.action_report_inspection_damage')
                pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
                    pdf_report.id,
                    [inspection.id]
                )

                # Create attachment
                pdf_attachment = request.env['ir.attachment'].sudo().create({
                    'name': f'Inspection_Damage_Report_{inspection.asset_id.asset_code}_{inspection.inspection_date}.pdf',
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': 'asset.inspection',
                    'res_id': inspection.id,
                    'mimetype': 'application/pdf',
                })

                inspection.write({
                    'damage_signed_pdf_id': pdf_attachment.id,
                })

            except Exception as pdf_error:
                _logger.error('Error generating signed PDF for inspection %s: %s', inspection.id, str(pdf_error))

            # Log message
            inspection.message_post(
                body='Parent damage acknowledgment received from %s (IP: %s)' % (inspection.parent_name, ip_address),
                subject='Damage Acknowledged'
            )

            return {
                'success': True,
                'message': 'Thank you for acknowledging the damage report. You will receive a confirmation email with the signed damage assessment.',
            }

        except Exception as e:
            _logger.exception('Error submitting inspection damage acknowledgment: %s', str(e))
            return {
                'success': False,
                'error': 'An error occurred while saving your acknowledgment. Please try again or contact the school IT department.',
            }
