# -*- coding: utf-8 -*-

from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
from ..models.security_helpers import SignatureSecurityHelper
import logging
import base64
from datetime import datetime
from functools import wraps

_logger = logging.getLogger(__name__)


# ============================================================================
# TOKEN VALIDATION DECORATOR
# ============================================================================

def validate_signature_token(model_name, token_field='checkout_token', token_type='checkout'):
    """
    Decorator for validating signature tokens with HMAC verification.

    This decorator reduces code duplication across controller methods by:
    - Finding the assignment record by token
    - Validating token (HMAC signature, expiry, usage status)
    - Handling error cases (invalid, expired, used)
    - Injecting validated assignment into the decorated function

    Args:
        model_name (str): Model name ('asset.student.assignment' or 'asset.teacher.assignment')
        token_field (str): Field name containing the token (default: 'checkout_token')
        token_type (str): Token type for validation (default: 'checkout')

    Usage:
        @validate_signature_token('asset.student.assignment', 'checkout_token', 'checkout')
        def my_route(self, token, assignment=None, **kwargs):
            # assignment is injected by decorator
            return request.render('template', {'assignment': assignment})

    Security:
        - HMAC-SHA256 signature verification
        - Token expiration checking
        - Token reuse prevention
        - Security audit logging for failures

    Returns:
        Decorated function with assignment injection
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, token, **kwargs):
            try:
                # Find record by token
                record = request.env[model_name].sudo().search([
                    (token_field, '=', token),
                ], limit=1)

                # Token not found
                if not record:
                    _logger.warning(f'Token not found for {model_name}: {token[:16]}...')
                    return request.render('school_asset_management.signature_error_page', {
                        'error_title': _('Invalid Link'),
                        'error_message': _('This signature link is invalid or has been removed.'),
                        'error_type': 'invalid',
                    })

                # Validate token (HMAC + expiry + usage)
                validation_result = record._validate_token(token, token_type=token_type)

                # Handle validation errors
                if validation_result == 'used':
                    # Get sign date based on token type
                    sign_date_field = {
                        'checkout': 'checkout_sign_date',
                        'damage': 'damage_acknowledge_date',
                    }.get(token_type, 'checkout_sign_date')

                    sign_date = getattr(record, sign_date_field, None)
                    date_str = sign_date.strftime('%Y-%m-%d %H:%M') if sign_date else 'N/A'

                    return request.render('school_asset_management.signature_already_signed_page', {
                        'assignment': record,
                        'message': _('This document has already been signed on %s.') % date_str,
                        'error_type': 'used',
                    })

                if validation_result == 'expired':
                    return request.render('school_asset_management.signature_error_page', {
                        'error_title': _('Link Expired'),
                        'error_message': _('This signature link has expired. Please contact the school IT department to request a new link.'),
                        'error_type': 'expired',
                    })

                if validation_result == 'tampered':
                    _logger.error(f'Token tampering detected for {model_name} ID {record.id}')
                    return request.render('school_asset_management.signature_error_page', {
                        'error_title': _('Security Alert'),
                        'error_message': _('This signature link has been tampered with. Please contact the school IT department.'),
                        'error_type': 'tampered',
                    })

                if validation_result != 'valid':
                    return request.render('school_asset_management.signature_error_page', {
                        'error_title': _('Invalid Link'),
                        'error_message': _('This signature link is not valid.'),
                        'error_type': 'invalid',
                    })

                # Token is valid - inject assignment into function
                kwargs['assignment'] = record
                return func(self, token, **kwargs)

            except Exception as e:
                _logger.exception(f'Error in token validation decorator for {model_name}')
                return request.render('school_asset_management.signature_error_page', {
                    'error_title': _('Error'),
                    'error_message': _('An error occurred while loading the signature page. Please contact the school IT department.'),
                    'error_type': 'error',
                })

        return wrapper
    return decorator


def validate_signature_submission(model_name, token_field='checkout_token', token_type='checkout',
                                signature_required=True, consent_types=None):
    """
    Decorator for validating signature submissions with comprehensive security checks.

    This decorator reduces code duplication across POST submission methods by:
    - Rate limiting check
    - Token validation and security logging
    - Signature data validation
    - IP address and user agent extraction
    - Error handling with proper logging

    Args:
        model_name (str): Model name ('asset.student.assignment', 'asset.teacher.assignment', etc.)
        token_field (str): Field name containing the token (default: 'checkout_token')
        token_type (str): Token type for validation and logging (default: 'checkout')
        signature_required (bool): Whether signature_data is required (default: True)
        consent_types (list): List of consent types to process (default: None)

    Usage:
        @validate_signature_submission('asset.student.assignment', 'checkout_token', 'checkout')
        def submit_signature(self, token, signature_data, assignment=None, **kwargs):
            # assignment, ip_address, user_agent are injected by decorator
            return {'success': True, 'message': _('Signature saved successfully.')}

    Security:
        - Rate limiting with Redis
        - Token validation (HMAC + expiry + usage)
        - Signature size validation (200KB limit)
        - Security audit logging for failures
        - Failed attempt logging

    Returns:
        Decorated function with assignment, ip_address, and user_agent injection
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, token, signature_data=None, **kwargs):
            try:
                # Get IP address and user agent
                ip_address = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR',
                                                            request.httprequest.environ.get('REMOTE_ADDR', 'Unknown'))
                user_agent = request.httprequest.headers.get('User-Agent', 'Unknown')

                # Security: Rate limiting check
                security_helper = SignatureSecurityHelper(request.env)
                is_allowed, attempts_left = security_helper.check_rate_limit(ip_address, 'signature')

                if not is_allowed:
                    _logger.warning(f'Rate limit exceeded for IP {ip_address} on {token_type} signature')
                    return {
                        'success': False,
                        'error': _('Too many attempts. Please try again in 1 hour.')
                    }

                # Find record by token
                record = request.env[model_name].sudo().search([
                    (token_field, '=', token),
                ], limit=1)

                if not record:
                    security_helper.log_failed_attempt(ip_address, token, f'{token_type}_signature')
                    # Enhanced audit logging
                    request.env['asset.security.audit.log'].sudo().log_signature_attempt(
                        event_type='token_invalid',
                        signature_type=token_type,
                        ip_address=ip_address,
                        token=token,
                        error_message=f'Invalid {token_type} signature link',
                        user_agent=user_agent
                    )
                    return {'success': False, 'error': _('Invalid signature link.')}

                # Validate token
                validation_result = record._validate_token(token, token_type=token_type)

                if validation_result != 'valid':
                    error_messages = {
                        'used': _('This document has already been signed.'),
                        'expired': _('This signature link has expired.'),
                        'tampered': _('This signature link has been tampered with.')
                    }
                    return {'success': False, 'error': error_messages.get(validation_result, _('Invalid signature link.'))}

                # Validate signature data
                if signature_required and not signature_data:
                    return {'success': False, 'error': _('Please provide your signature.')}

                # Security: Validate signature size (prevent DoS)
                if signature_data and len(signature_data) > 200000:  # 200KB limit
                    return {'success': False, 'error': _('Signature file is too large. Please try again.')}

                # Inject common variables into function
                kwargs['assignment'] = record
                kwargs['ip_address'] = ip_address
                kwargs['user_agent'] = user_agent
                kwargs['security_helper'] = security_helper

                return func(self, token, signature_data, **kwargs)

            except Exception as e:
                _logger.exception(f'Error in signature submission decorator for {model_name}')
                return {
                    'success': False,
                    'error': _('An error occurred while processing your signature. Please try again or contact the school IT department.')
                }

        return wrapper
    return decorator


class StudentAssignmentSignatureController(http.Controller):
    """Public controller for parent signature on student asset assignments"""

    # ========================================================================
    # CHECKOUT SIGNATURE ROUTES
    # ========================================================================

    @http.route('/sign/student/checkout/<string:token>', type='http', auth='public', website=False, sitemap=False)
    @validate_signature_token('asset.student.assignment', 'checkout_token', 'checkout')
    def student_checkout_signature(self, token, assignment=None, **kwargs):
        """
        Public page for parent to sign checkout waiver

        Args:
            token: Secure token from email link
            assignment: Injected by decorator after token validation

        Returns:
            Rendered template with assignment details and signature form
        """
        # Render signature page (validation handled by decorator)
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

    @http.route('/sign/student/checkout/submit', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    @validate_signature_submission('asset.student.assignment', 'checkout_token', 'checkout')
    def submit_checkout_signature(self, token, signature_data, parent_name, assignment=None,
                                 ip_address=None, user_agent=None, security_helper=None, **kwargs):
        """
        Save checkout signature submitted by parent

        Args:
            token: Secure token
            signature_data: Base64 encoded signature image
            parent_name: Parent/Guardian full name
            assignment: Injected by decorator after token validation
            ip_address: Injected by decorator
            user_agent: Injected by decorator
            security_helper: Injected by decorator

        Returns:
            JSON response with success/error status
        """
        try:
            # Validate parent name
            if not parent_name:
                return {'success': False, 'error': _('Please provide your name and signature.')}

            # PDPA Compliance: Log consent before saving signature
            consents_given = kwargs.get('consents', {})
            consent_model = request.env['asset.consent.log'].sudo()

            # Log various consent types
            consent_mappings = {
                'consent_data_collection': ('data_collection', 'Asset management and borrowing records'),
                'consent_digital_signature': ('digital_signature', 'Electronic signature for asset borrowing confirmation'),
                'consent_email': ('email_communication', 'Notifications and communications regarding asset borrowing'),
                'consent_liability': ('damage_liability', 'Acknowledgment of liability for damaged/lost assets'),
            }

            for consent_key, (consent_type, purpose) in consent_mappings.items():
                if consents_given.get(consent_key):
                    consent_model.log_consent(
                        consent_type=consent_type,
                        user_type='parent',
                        data_subject_name=parent_name,
                        data_subject_email=assignment.parent_email,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        privacy_version=assignment.privacy_policy_version or '1.0',
                        student_assignment_id=assignment.id,
                        purpose=purpose,
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
    @validate_signature_token('asset.student.assignment', 'damage_report_token', 'damage')
    def student_damage_report(self, token, assignment=None, **kwargs):
        """
        Public page for parent to acknowledge damage report

        Args:
            token: Secure token from email link
            assignment: Injected by decorator after token validation

        Returns:
            Rendered template with damage details and signature form
        """
        # Token validation handled by decorator
        # Get damaged assets
        damaged_assets = assignment.asset_line_ids.filtered(lambda l: l.damage_found)

        if not damaged_assets:
            _logger.warning('No damaged assets found for assignment %s', assignment.id)
            return request.render('school_asset_management.signature_error_page', {
                'error_title': _('No Damages Found'),
                'error_message': _('No damaged assets were found for this assignment. Please contact the school IT department.'),
                'error_type': 'invalid',
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

    @http.route('/sign/student/damage/submit', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    @validate_signature_submission('asset.student.assignment', 'damage_report_token', 'damage')
    def submit_damage_acknowledgment(self, token, signature_data, assignment=None,
                                    ip_address=None, **kwargs):
        """
        Save damage acknowledgment signature

        Args:
            token: Secure token
            signature_data: Base64 encoded signature image
            assignment: Injected by decorator after token validation
            ip_address: Injected by decorator

        Returns:
            JSON response with success/error status
        """
        try:
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
    @validate_signature_token('asset.damage.case', 'approval_token', 'approval')
    def damage_case_approval(self, token, assignment=None, **kwargs):
        """
        Public page for manager to approve/reject damage case

        Args:
            token: Secure token from email link
            assignment: Injected by decorator (damage_case record)

        Returns:
            Rendered template with damage case details and approval form
        """
        # Token validation handled by decorator
        # assignment here is actually the damage_case record
        damage_case = assignment

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

    @http.route('/damage/approve/submit', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    @validate_signature_submission('asset.damage.case', 'approval_token', 'approval', signature_required=True)
    def submit_damage_case_approval(self, token, signature_data, decision, notes='', assignment=None,
                                    ip_address=None, **kwargs):
        """
        Save damage case approval/rejection

        Args:
            token: Secure token
            signature_data: Base64 encoded signature image
            decision: 'approve' or 'reject'
            notes: Optional approval notes
            assignment: Injected by decorator (damage_case record)
            ip_address: Injected by decorator

        Returns:
            JSON response with success/error status
        """
        try:
            # Validate decision
            if decision not in ('approve', 'reject'):
                return {'success': False, 'error': 'Invalid decision.'}

            # Remove data:image header if present
            if 'base64,' in signature_data:
                signature_data = signature_data.split('base64,')[1]

            # Save approval
            approval_status = 'approved' if decision == 'approve' else 'rejected'
            status = 'approved' if decision == 'approve' else 'rejected'

            assignment.write({
                'approval_signature': signature_data,
                'approval_status': approval_status,
                'status': status,
                'approval_signature_date': fields.Datetime.now(),
                'approval_signature_ip': ip_address,
                'approval_token_used': True,
                'approval_date': fields.Datetime.now(),
                'approval_notes': notes,
                'approver_id': assignment.env.user.id if not assignment.env.user._is_public() else False,
            })

            # Generate signed PDF
            try:
                pdf_report = request.env.ref('school_asset_management.action_report_damage_case_approval')
                pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
                    pdf_report.id,
                    [assignment.id]
                )

                # Create attachment
                pdf_attachment = request.env['ir.attachment'].sudo().create({
                    'name': f'Damage_Case_Approval_{assignment.name}.pdf',
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': 'asset.damage.case',
                    'res_id': assignment.id,
                    'mimetype': 'application/pdf',
                })

                assignment.write({
                    'approval_signed_pdf_id': pdf_attachment.id,
                })

            except Exception as pdf_error:
                _logger.error('Error generating signed PDF for damage case %s: %s', assignment.id, str(pdf_error))

            # Log message
            action_text = 'approved' if decision == 'approve' else 'rejected'
            assignment.message_post(
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
    @validate_signature_token('asset.teacher.assignment', 'checkout_token', 'checkout')
    def teacher_checkout_signature(self, token, assignment=None, **kwargs):
        """
        Public page for teacher to sign checkout waiver

        Args:
            token: Secure token from email link
            assignment: Injected by decorator after token validation

        Returns:
            Rendered template with assignment details and signature form
        """
        # Token validation handled by decorator
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

    @http.route('/sign/teacher/checkout/submit', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    @validate_signature_submission('asset.teacher.assignment', 'checkout_token', 'checkout')
    def submit_teacher_checkout_signature(self, token, signature_data, assignment=None,
                                         ip_address=None, user_agent=None, security_helper=None, **kwargs):
        """
        Save checkout signature submitted by teacher

        Args:
            token: Secure token
            signature_data: Base64 encoded signature image
            assignment: Injected by decorator after token validation
            ip_address: Injected by decorator
            user_agent: Injected by decorator
            security_helper: Injected by decorator

        Returns:
            JSON response with success/error status
        """
        try:
            # PDPA Compliance: Log consent before saving signature
            consents_given = kwargs.get('consents', {})
            consent_model = request.env['asset.consent.log'].sudo()
            teacher_name = assignment.teacher_id.name if assignment.teacher_id else 'Unknown'

            # Log various consent types
            consent_mappings = {
                'consent_data_collection': ('data_collection', 'Asset management and borrowing records'),
                'consent_digital_signature': ('digital_signature', 'Electronic signature for asset borrowing confirmation'),
                'consent_email': ('email_communication', 'Notifications and communications regarding asset borrowing'),
                'consent_liability': ('damage_liability', 'Acknowledgment of liability for damaged/lost assets'),
            }

            for consent_key, (consent_type, purpose) in consent_mappings.items():
                if consents_given.get(consent_key):
                    consent_model.log_consent(
                        consent_type=consent_type,
                        user_type='teacher',
                        data_subject_name=teacher_name,
                        data_subject_email=assignment.teacher_email,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        privacy_version='1.0',
                        teacher_assignment_id=assignment.id,
                        purpose=purpose,
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
    @validate_signature_token('asset.teacher.assignment', 'damage_report_token', 'damage')
    def teacher_damage_report(self, token, assignment=None, **kwargs):
        """
        Public page for teacher to acknowledge damage report

        Args:
            token: Secure token from email link
            assignment: Injected by decorator after token validation

        Returns:
            Rendered template with damage details and signature form
        """
        # Token validation handled by decorator
        # Get damaged assets
        damaged_assets = assignment.asset_line_ids.filtered(lambda l: l.damage_found)

        if not damaged_assets:
            return request.render('school_asset_management.signature_error_page', {
                'error_title': _('No Damages Found'),
                'error_message': _('No damaged assets were found for this assignment. Please contact the IT department.'),
                'error_type': 'invalid',
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

    @http.route('/sign/teacher/damage/submit', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    @validate_signature_submission('asset.teacher.assignment', 'damage_report_token', 'damage')
    def submit_teacher_damage_acknowledgment(self, token, signature_data, assignment=None,
                                            ip_address=None, **kwargs):
        """
        Save damage acknowledgment signature

        Args:
            token: Secure token
            signature_data: Base64 encoded signature image
            assignment: Injected by decorator after token validation
            ip_address: Injected by decorator

        Returns:
            JSON response with success/error status
        """
        try:
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
    @validate_signature_token('asset.inspection', 'damage_token', 'damage')
    def inspection_damage_signature(self, token, assignment=None, **kwargs):
        """
        Public page for parent to sign inspection damage acknowledgment

        Args:
            token: Secure token from email link
            assignment: Injected by decorator (inspection record)

        Returns:
            Rendered template with inspection damage details and signature form
        """
        # Token validation handled by decorator
        # assignment here is actually the inspection record
        inspection = assignment

        # Check if damage was found for student custodian
        if not inspection.damage_found or inspection.custodian_type != 'student':
            return request.render('school_asset_management.signature_error_page', {
                'error_title': _('Invalid Link'),
                'error_message': _('This damage acknowledgment link is not valid.'),
                'error_type': 'invalid',
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

    @http.route('/sign/inspection/damage/submit', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    @validate_signature_submission('asset.inspection', 'damage_token', 'damage')
    def submit_inspection_damage_acknowledgment(self, token, signature_data, assignment=None,
                                               ip_address=None, **kwargs):
        """
        Save inspection damage acknowledgment signature

        Args:
            token: Secure token
            signature_data: Base64 encoded signature image
            assignment: Injected by decorator (inspection record)
            ip_address: Injected by decorator

        Returns:
            JSON response with success/error status
        """
        try:
            # Check if already signed
            if assignment.damage_token_used or assignment.parent_damage_acknowledged:
                return {'success': False, 'error': _('This damage report has already been acknowledged.')}

            # Check if expired
            if assignment.damage_token_expiry and assignment.damage_token_expiry < fields.Datetime.now():
                return {'success': False, 'error': _('This damage acknowledgment link has expired.')}

            # Remove data:image header if present
            if 'base64,' in signature_data:
                signature_data = signature_data.split('base64,')[1]

            # Save signature
            assignment.write({
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
                    [assignment.id]
                )

                # Create attachment
                pdf_attachment = request.env['ir.attachment'].sudo().create({
                    'name': f'Inspection_Damage_Report_{assignment.asset_id.asset_code}_{assignment.inspection_date}.pdf',
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': 'asset.inspection',
                    'res_id': assignment.id,
                    'mimetype': 'application/pdf',
                })

                assignment.write({
                    'damage_signed_pdf_id': pdf_attachment.id,
                })

            except Exception as pdf_error:
                _logger.error('Error generating signed PDF for inspection %s: %s', assignment.id, str(pdf_error))

            # Log message
            assignment.message_post(
                body='Parent damage acknowledgment received from %s (IP: %s)' % (assignment.parent_name, ip_address),
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
