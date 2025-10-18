/**
 * MYIS International School - Teacher Checkout Signature Pad
 * Extends BaseSignaturePad for teacher signature capture
 * Supports both mouse and touch input with PDPA consent collection
 */

(function() {
    'use strict';

    // Prevent multiple initializations globally
    if (window.__MYIS_TeacherSignaturePad_Initialized__) {
        console.log('TeacherSignaturePad already initialized, skipping...');
        return;
    }
    window.__MYIS_TeacherSignaturePad_Initialized__ = true;

    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', function() {
        // Check if this is a teacher CHECKOUT form specifically (not damage form)
        // Teacher checkout has 'submit-signature', damage form has 'submit-damage-signature'
        const submitButton = document.getElementById('submit-signature');
        const damageSubmitButton = document.getElementById('submit-damage-signature');

        // Also check for student form elements
        const parentNameInput = document.getElementById('parent_name_input');

        console.log('TeacherSignaturePad: Button detection:', {
            submitButton: submitButton ? 'FOUND' : 'NOT FOUND',
            damageSubmitButton: damageSubmitButton ? 'FOUND' : 'NOT FOUND',
            parentNameInput: parentNameInput ? 'FOUND (Student form)' : 'NOT FOUND',
            url: window.location.pathname
        });

        // Skip if this is a student form (has parent_name_input)
        if (parentNameInput) {
            console.log('TeacherSignaturePad: This is a student form (parent_name_input found), skipping initialization');
            return;
        }

        // Skip if this is a damage form
        if (damageSubmitButton) {
            console.log('TeacherSignaturePad: This is a damage form (submit-damage-signature found), skipping initialization');
            return;
        }

        // Skip if no submit button
        if (!submitButton) {
            console.log('TeacherSignaturePad: submit-signature button not found, skipping initialization');
            return;
        }

        console.log('TeacherSignaturePad: Initializing for teacher checkout form');

        // Initialize signature pad with configuration
        new BaseSignaturePad({
            // DOM element IDs
            canvasId: 'signature-pad',
            clearButtonId: 'clear-signature',
            submitButtonId: 'submit-signature',
            tokenInputId: 'signature_token',
            statusMessageId: 'status-message',

            // API endpoint
            submitEndpoint: '/sign/teacher/checkout/submit',

            // Required fields
            requiredFields: [],

            // Required checkboxes (PDPA consents)
            requiredCheckboxes: [
                { id: 'consent_privacy_policy', label: 'Privacy Policy Consent' },
                { id: 'consent_digital_signature', label: 'Digital Signature Consent' },
                { id: 'consent_email', label: 'Email Communication Consent' },
                { id: 'consent_liability', label: 'Liability Agreement Consent' }
            ],

            // Enable PDPA consent collection
            collectConsents: true,

            // Prevent double submission
            preventConcurrentSubmit: true
        });

        console.log('Teacher Checkout SignaturePad initialized successfully');
    });
})();
