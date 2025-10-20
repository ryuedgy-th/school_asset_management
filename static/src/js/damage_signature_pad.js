/**
 * MYIS International School - Student Damage Report Signature Pad
 * Extends BaseSignaturePad for damage acknowledgment
 * Supports both mouse and touch input with photo click-to-enlarge
 */

(function() {
    'use strict';

    // Prevent multiple initializations globally
    if (window.__MYIS_DamageSignaturePad_Initialized__) {
        console.log('DamageSignaturePad already initialized, skipping...');
        return;
    }
    window.__MYIS_DamageSignaturePad_Initialized__ = true;

    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', function() {
        // Check if submit button exists (unique to this form)
        const submitButton = document.getElementById('submit-damage-signature');
        if (!submitButton) {
            // Not a damage signature form - skip initialization
            return;
        }

        // Initialize signature pad with configuration
        new BaseSignaturePad({
            // DOM element IDs
            canvasId: 'signature-pad',
            clearButtonId: 'clear-signature',
            submitButtonId: 'submit-damage-signature',
            tokenInputId: 'damage_token',
            statusMessageId: 'status-message',

            // API endpoint
            submitEndpoint: '/sign/student/damage/submit',

            // Required fields
            requiredFields: [],

            // Required checkboxes
            requiredCheckboxes: [],

            // Disable PDPA consent collection (damage reports don't need consents)
            collectConsents: false,

            // Prevent double submission
            preventConcurrentSubmit: true
        });

        // Add click-to-enlarge for damage photos
        const damagePhotos = document.querySelectorAll('.damage-item .img-thumbnail');
        damagePhotos.forEach(photo => {
            photo.addEventListener('click', function() {
                const modal = document.createElement('div');
                modal.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.9);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 9999;
                    cursor: pointer;
                `;

                const img = document.createElement('img');
                img.src = this.src;
                img.style.cssText = 'max-width: 90%; max-height: 90%; border-radius: 8px;';

                modal.appendChild(img);
                document.body.appendChild(modal);

                modal.addEventListener('click', function() {
                    document.body.removeChild(modal);
                });
            });
        });

        console.log('Student Damage SignaturePad initialized successfully');
    });
})();
