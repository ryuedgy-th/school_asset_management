/**
 * MYIS International School - Student Checkout Signature Pad
 * Extends BaseSignaturePad for parent/student signature capture
 * Supports both mouse and touch input with PDPA consent collection
 */

(function() {
    'use strict';

    // Prevent multiple initializations globally
    if (window.__MYIS_SignaturePad_Initialized__) {
        console.log('SignaturePad already initialized, skipping...');
        return;
    }
    window.__MYIS_SignaturePad_Initialized__ = true;

    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', function() {
        // Check if this is the student/parent signature page
        const parentNameInput = document.getElementById('parent_name_input');
        if (!parentNameInput) {
            // Not a student form - skip initialization
            return;
        }

        // Initialize signature pad with configuration
        new BaseSignaturePad({
            // DOM element IDs
            canvasId: 'signature-pad',
            clearButtonId: 'clear-signature',
            submitButtonId: 'submit-signature',
            tokenInputId: 'signature_token',
            statusMessageId: 'status-message',

            // API endpoint
            submitEndpoint: '/sign/student/checkout/submit',

            // Required fields
            requiredFields: [
                {
                    id: 'parent_name_input',
                    errorMessage: '<strong>Error:</strong> Please enter your full name.<br><strong>กรุณากรอกชื่อ-นามสกุล</strong>'
                }
            ],

            // Required checkboxes (PDPA consents)
            requiredCheckboxes: [
                { id: 'consent_privacy_policy', label: 'Privacy Policy Consent (ความยินยอมนโยบายความเป็นส่วนตัว)' },
                { id: 'consent_digital_signature', label: 'Digital Signature Consent (ความยินยอมใช้ลายเซ็นดิจิทัล)' },
                { id: 'consent_email', label: 'Email Communication Consent (ความยินยอมรับอีเมล)' },
                { id: 'consent_liability', label: 'Liability Agreement Consent (ความยินยอมรับผิดชอบ)' }
            ],

            // Enable PDPA consent collection
            collectConsents: true,

            // Prevent double submission
            preventConcurrentSubmit: true
        });

        console.log('Student Checkout SignaturePad initialized successfully');
    });
})();
