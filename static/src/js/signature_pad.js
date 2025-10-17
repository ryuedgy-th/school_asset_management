/**
 * MYIS International School - Signature Pad
 * Canvas-based signature capture for checkout waiver
 * Supports both mouse and touch input
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

        const canvas = document.getElementById('signature-pad');
        const clearButton = document.getElementById('clear-signature');
        const submitButton = document.getElementById('submit-signature');
        const tokenInput = document.getElementById('signature_token');
        const statusMessage = document.getElementById('status-message');
        const container = canvas.closest('.signature-pad-container');

        if (!canvas) {
            console.error('Signature canvas not found');
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
            // Check if parentNameInput exists
            if (!parentNameInput) {
                console.error('Parent name input not found');
                showStatusMessage('danger', '<strong>Error:</strong> Form element missing. Please refresh the page.');
                return false;
            }

            const parentName = parentNameInput.value.trim();

            if (!parentName) {
                showStatusMessage('danger', '<strong>Error:</strong> Please enter your full name.<br><strong>กรุณากรอกชื่อ-นามสกุล</strong>');
                parentNameInput.focus();
                return false;
            }

            if (!hasSignature) {
                showStatusMessage('danger', '<strong>Error:</strong> Please provide your signature above.<br><strong>กรุณาเซ็นชื่อด้านบน</strong>');
                container.classList.add('error');
                setTimeout(() => container.classList.remove('error'), 2000);
                return false;
            }

            // PDPA: Validate all required consent checkboxes
            const consentCheckboxes = [
                { id: 'consent_privacy_policy', label: 'Privacy Policy Consent (ความยินยอมนโยบายความเป็นส่วนตัว)' },
                { id: 'consent_digital_signature', label: 'Digital Signature Consent (ความยินยอมใช้ลายเซ็นดิจิทัล)' },
                { id: 'consent_email', label: 'Email Communication Consent (ความยินยอมรับอีเมล)' },
                { id: 'consent_liability', label: 'Liability Agreement Consent (ความยินยอมรับผิดชอบ)' }
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

        // Prevent concurrent submissions
        let isSubmitting = false;

        // Submit signature
        if (submitButton) {
            submitButton.addEventListener('click', function() {
            // Prevent double-click / concurrent submission
            if (isSubmitting) {
                console.log('Already submitting, ignoring duplicate request');
                return;
            }

            hideStatusMessage();

            // Validate
            if (!validateForm()) {
                return;
            }

            // Set submitting flag
            isSubmitting = true;

            // Get data
            const parentName = parentNameInput.value.trim();
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
            fetch('/sign/student/checkout/submit', {
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
                        parent_name: parentName,
                        consents: consents
                    }
                })
            })
            .then(response => response.json())
            .then(data => {
                // Reset submitting flag
                isSubmitting = false;
                submitButton.disabled = false;
                submitButton.classList.remove('loading');
                submitButton.innerHTML = originalText;

                // Support both JSON-RPC format and direct response
                const response = data.result || data;

                if (response && response.success) {
                    // Success
                    showStatusMessage('success', `
                        <strong><i class="fa fa-check-circle"></i> Success!</strong><br>
                        ${response.message || 'Your signature has been recorded successfully.'}
                    `);

                    // Disable form
                    parentNameInput.disabled = true;
                    clearButton.disabled = true;
                    submitButton.disabled = true;
                    canvas.style.pointerEvents = 'none';

                    // Redirect after 3 seconds
                    setTimeout(() => {
                        window.location.reload();
                    }, 3000);

                } else {
                    // Error - handle various error formats
                    let errorMsg = 'An unknown error occurred.';
                    if (response?.error) {
                        if (typeof response.error === 'string') {
                            errorMsg = response.error;
                        } else if (response.error.message) {
                            errorMsg = response.error.message;
                        } else if (response.error.data && response.error.data.message) {
                            errorMsg = response.error.data.message;
                        } else {
                            errorMsg = JSON.stringify(response.error);
                        }
                    }
                    console.error('Submission error:', response);
                    showStatusMessage('danger', `<strong>Error:</strong> ${errorMsg}`);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                // Reset submitting flag on error
                isSubmitting = false;
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

        // Enable submit button when name is entered
        if (parentNameInput) {
            parentNameInput.addEventListener('input', function() {
                hideStatusMessage();
            });
        }

    });
})();
