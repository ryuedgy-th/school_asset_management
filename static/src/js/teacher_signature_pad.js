/**
 * MYIS International School - Teacher Signature Pad
 * Canvas-based signature capture for teacher checkout waiver
 * Supports both mouse and touch input
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

        const canvas = document.getElementById('signature-pad');
        if (!canvas) {
            console.error('TeacherSignaturePad: Signature canvas not found');
            return;
        }

        console.log('TeacherSignaturePad: Initializing for teacher checkout form');

        const clearButton = document.getElementById('clear-signature');
        const agreementCheckbox = document.getElementById('agreement_checkbox');
        const tokenInput = document.getElementById('signature_token');
        const statusMessage = document.getElementById('status-message');
        const container = canvas.closest('.signature-pad-container');

        // Validate critical elements
        if (!tokenInput) {
            console.error('Token input not found');
            return;
        }
        if (!statusMessage) {
            console.error('Status message element not found');
            return;
        }

        // Get 2D context
        const ctx = canvas.getContext('2d');

        // Set canvas size
        function resizeCanvas() {
            const ratio = Math.max(window.devicePixelRatio || 1, 1);
            canvas.width = canvas.offsetWidth * ratio;
            canvas.height = canvas.offsetHeight * ratio;
            canvas.getContext('2d').scale(ratio, ratio);
            ctx.strokeStyle = '#000000';
            ctx.lineWidth = 2;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
        }

        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);

        // Drawing state
        let isDrawing = false;
        let hasSignature = false;
        let lastX = 0;
        let lastY = 0;

        // Get coordinates relative to canvas
        function getCoordinates(event) {
            const rect = canvas.getBoundingClientRect();
            const clientX = event.touches ? event.touches[0].clientX : event.clientX;
            const clientY = event.touches ? event.touches[0].clientY : event.clientY;

            return {
                x: clientX - rect.left,
                y: clientY - rect.top
            };
        }

        // Start drawing
        function startDrawing(event) {
            event.preventDefault();
            isDrawing = true;
            const coords = getCoordinates(event);
            lastX = coords.x;
            lastY = coords.y;
            container.classList.add('signing');
        }

        // Draw line
        function draw(event) {
            if (!isDrawing) return;
            event.preventDefault();

            const coords = getCoordinates(event);

            ctx.beginPath();
            ctx.moveTo(lastX, lastY);
            ctx.lineTo(coords.x, coords.y);
            ctx.stroke();

            lastX = coords.x;
            lastY = coords.y;
            hasSignature = true;
        }

        // Stop drawing
        function stopDrawing(event) {
            if (!isDrawing) return;
            event.preventDefault();
            isDrawing = false;
            container.classList.remove('signing');

            if (hasSignature) {
                container.classList.add('has-signature');
            }
        }

        // Mouse events
        canvas.addEventListener('mousedown', startDrawing);
        canvas.addEventListener('mousemove', draw);
        canvas.addEventListener('mouseup', stopDrawing);
        canvas.addEventListener('mouseout', stopDrawing);

        // Touch events
        canvas.addEventListener('touchstart', startDrawing);
        canvas.addEventListener('touchmove', draw);
        canvas.addEventListener('touchend', stopDrawing);
        canvas.addEventListener('touchcancel', stopDrawing);

        // Clear signature
        if (clearButton) {
            clearButton.addEventListener('click', function() {
                // Save the current transformation matrix
                ctx.save();
                // Use identity matrix to clear entire canvas
                ctx.setTransform(1, 0, 0, 1, 0, 0);
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                // Restore the transformation
                ctx.restore();

                hasSignature = false;
                container.classList.remove('has-signature');
                hideStatusMessage();
            });
        }

        // Show status message
        function showStatusMessage(type, message) {
            statusMessage.innerHTML = `
                <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                    ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `;
            statusMessage.style.display = 'block';
            statusMessage.classList.add('show');
        }

        // Hide status message
        function hideStatusMessage() {
            if (statusMessage) {
                statusMessage.style.display = 'none';
                statusMessage.classList.remove('show');
                statusMessage.innerHTML = '';
            }
        }

        // Validate form
        function validateForm() {
            // Check agreement checkbox
            if (agreementCheckbox && !agreementCheckbox.checked) {
                showStatusMessage('danger', '<strong>Error:</strong> Please acknowledge that you have read and agree to the terms and conditions.');
                agreementCheckbox.focus();
                return false;
            }

            // Check signature
            if (!hasSignature) {
                showStatusMessage('danger', '<strong>Error:</strong> Please provide your signature above.');
                container.classList.add('error');
                setTimeout(() => container.classList.remove('error'), 2000);
                return false;
            }

            // PDPA: Validate all required consent checkboxes
            const consentCheckboxes = [
                { id: 'consent_privacy_policy', label: 'Privacy Policy Consent' },
                { id: 'consent_digital_signature', label: 'Digital Signature Consent' },
                { id: 'consent_email', label: 'Email Communication Consent' },
                { id: 'consent_liability', label: 'Liability Agreement Consent' }
            ];

            for (const checkbox of consentCheckboxes) {
                const element = document.getElementById(checkbox.id);
                // Check if element exists
                if (!element) {
                    console.error(`Consent checkbox not found: ${checkbox.id}`);
                    showStatusMessage('danger', `<strong>Error:</strong> Required form element missing: <strong>${checkbox.label}</strong>. Please refresh the page.`);
                    return false;
                }
                // Check if element is checked
                if (!element.checked) {
                    showStatusMessage('danger', `<strong>Error:</strong> Please check the required consent box: <strong>${checkbox.label}</strong>`);
                    element.focus();
                    // Scroll to checkbox
                    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    return false;
                }
            }

            return true;
        }

        // Submit signature
        if (submitButton) {
            submitButton.addEventListener('click', function() {
                hideStatusMessage();

                // Validate
                if (!validateForm()) {
                    return;
                }

                // Check token input exists
                if (!tokenInput || !tokenInput.value) {
                    showStatusMessage('danger', '<strong>Error:</strong> Token not found. Please refresh the page.');
                    return;
                }

                // Get data
                const token = tokenInput.value;
                const signatureData = canvas.toDataURL('image/png').split(',')[1]; // Get base64 without prefix

                // PDPA: Collect consent data
                const consents = {
                    consent_privacy_policy: document.getElementById('consent_privacy_policy')?.checked || false,
                    consent_digital_signature: document.getElementById('consent_digital_signature')?.checked || false,
                    consent_email: document.getElementById('consent_email')?.checked || false,
                    consent_liability: document.getElementById('consent_liability')?.checked || false
                };

                // Disable button and show loading
                submitButton.disabled = true;
                submitButton.classList.add('loading');
                const originalText = submitButton.innerHTML;
                submitButton.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Submitting...';

                // Send to server
                fetch('/sign/teacher/checkout/submit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: {
                            token: token,
                            signature_data: signatureData,
                            consents: consents
                        }
                    })
                })
                .then(response => response.json())
                .then(data => {
                    console.log('TeacherSignaturePad - Raw response data:', JSON.stringify(data, null, 2));

                    submitButton.disabled = false;
                    submitButton.classList.remove('loading');
                    submitButton.innerHTML = originalText;

                    // Support both JSON-RPC format and direct response
                    const response = data.result || data;
                    console.log('TeacherSignaturePad - Parsed response:', JSON.stringify(response, null, 2));

                    if (response && response.success) {
                        // Success
                        showStatusMessage('success', `
                            <strong><i class="fa fa-check-circle"></i> Success!</strong><br>
                            ${response.message || 'Your signature has been recorded successfully.'}
                        `);

                        // Disable form
                        if (agreementCheckbox) agreementCheckbox.disabled = true;
                        clearButton.disabled = true;
                        submitButton.disabled = true;
                        canvas.style.pointerEvents = 'none';

                        // Redirect after 3 seconds
                        setTimeout(() => {
                            window.location.reload();
                        }, 3000);

                    } else {
                        // Error - handle various error formats
                        console.error('TeacherSignaturePad - Submission error - full response:', JSON.stringify(response, null, 2));

                        let errorMsg = 'An unknown error occurred.';

                        // Check for error in various locations
                        if (response?.error) {
                            console.log('TeacherSignaturePad - Error type:', typeof response.error);
                            if (typeof response.error === 'string') {
                                errorMsg = response.error;
                            } else if (response.error.message) {
                                errorMsg = response.error.message;
                            } else if (response.error.data && response.error.data.message) {
                                errorMsg = response.error.data.message;
                            } else {
                                errorMsg = JSON.stringify(response.error);
                            }
                        } else if (response?.message) {
                            errorMsg = response.message;
                        }

                        console.error('TeacherSignaturePad - Final error message:', errorMsg);
                        showStatusMessage('danger', `<strong>Error:</strong> ${errorMsg}`);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    submitButton.disabled = false;
                    submitButton.classList.remove('loading');
                    submitButton.innerHTML = originalText;

                    showStatusMessage('danger', `
                        <strong>Error:</strong> Failed to submit signature.
                        Please check your internet connection and try again.
                    `);
                });
            });
        }

        // Enable submit button when checkbox is checked
        if (agreementCheckbox) {
            agreementCheckbox.addEventListener('change', function() {
                hideStatusMessage();
            });
        }

    });
})();
