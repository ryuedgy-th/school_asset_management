/**
 * MYIS International School - Teacher Damage Report Signature Pad
 * Extends BaseSignaturePad for teacher damage acknowledgment
 * Supports both mouse and touch input with photo click-to-enlarge modal
 */

(function() {
    'use strict';

    // Prevent multiple initializations globally
    if (window.__MYIS_TeacherDamageSignaturePad_Initialized__) {
        console.log('TeacherDamageSignaturePad already initialized, skipping...');
        return;
    }
    window.__MYIS_TeacherDamageSignaturePad_Initialized__ = true;
    console.log('TeacherDamageSignaturePad initialized');

    /**
     * Photo click handler (defined once globally)
     * Creates a modal to enlarge damage photos
     */
    if (!window.__MYIS_TeacherDamagePhotoClickHandler__) {
        console.log('Creating TeacherDamagePhotoClickHandler');

        // Counter for debugging
        let modalCounter = 0;

        window.__MYIS_TeacherDamagePhotoClickHandler__ = function(e) {
            // Check if clicked element is a damage photo
            if (!e.target.matches('.damage-item .img-thumbnail')) {
                return;
            }

            e.preventDefault();
            e.stopPropagation();

            modalCounter++;
            console.log('Modal created #' + modalCounter);

            const clickedImg = e.target;
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.95);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                z-index: 9999;
            `;

            // Close modal function
            let escHandler;
            let isClosed = false;
            const closeModal = function() {
                if (!isClosed && document.body.contains(modal)) {
                    isClosed = true;
                    document.body.removeChild(modal);
                    if (escHandler) {
                        document.removeEventListener('keydown', escHandler);
                    }
                }
            };

            // Close button
            const closeBtn = document.createElement('button');
            closeBtn.innerHTML = '✕';
            closeBtn.style.cssText = `
                position: absolute;
                top: 20px;
                right: 30px;
                background: rgba(255, 255, 255, 0.2);
                border: 2px solid white;
                color: white;
                font-size: 36px;
                width: 50px;
                height: 50px;
                border-radius: 50%;
                cursor: pointer;
                transition: all 0.3s;
                padding: 0;
                line-height: 1;
            `;
            closeBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                closeModal();
            });
            closeBtn.addEventListener('mouseover', function() {
                this.style.background = 'rgba(255, 255, 255, 0.3)';
                this.style.transform = 'scale(1.1)';
            });
            closeBtn.addEventListener('mouseout', function() {
                this.style.background = 'rgba(255, 255, 255, 0.2)';
                this.style.transform = 'scale(1)';
            });

            // Image
            const img = document.createElement('img');
            img.src = clickedImg.src;
            img.style.cssText = 'max-width: 90%; max-height: 85%; border-radius: 8px;';

            // Help text
            const helpText = document.createElement('div');
            helpText.innerHTML = 'Click X button or press ESC to close';
            helpText.style.cssText = `
                color: white;
                margin-top: 20px;
                font-size: 14px;
                opacity: 0.8;
            `;

            modal.appendChild(closeBtn);
            modal.appendChild(img);
            modal.appendChild(helpText);
            document.body.appendChild(modal);

            // Close on ESC key
            escHandler = function(e) {
                if (e.key === 'Escape') {
                    closeModal();
                }
            };
            document.addEventListener('keydown', escHandler);
        };
    }

    /**
     * Initialization function
     */
    function initTeacherDamageSignaturePad() {
        const submitButton = document.getElementById('submit-damage-signature');
        if (!submitButton) {
            console.log('TeacherDamageSignaturePad: submit-damage-signature button not found, skipping');
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
            submitEndpoint: '/sign/teacher/damage/submit',

            // Required fields
            requiredFields: [],

            // Required checkboxes
            requiredCheckboxes: [],

            // Disable PDPA consent collection (damage reports don't need consents)
            collectConsents: false,

            // Prevent double submission
            preventConcurrentSubmit: true
        });

        // Bind photo click handler (remove old, add new)
        console.log('Binding photo click handler');
        document.body.removeEventListener('click', window.__MYIS_TeacherDamagePhotoClickHandler__);
        document.body.addEventListener('click', window.__MYIS_TeacherDamagePhotoClickHandler__);

        console.log('Teacher Damage SignaturePad initialized successfully');
    }

    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTeacherDamageSignaturePad, { once: true });
    } else {
        // DOM already loaded
        initTeacherDamageSignaturePad();
    }
})();
