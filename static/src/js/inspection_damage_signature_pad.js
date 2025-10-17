/**
 * MYIS International School - Inspection Damage Signature Pad
 * Canvas-based signature capture for inspection damage acknowledgment
 * Supports both mouse and touch input
 */

(function() {
    'use strict';

    // Prevent multiple initializations globally
    if (window.__MYIS_InspectionDamageSignaturePad_Initialized__) {
        console.log('InspectionDamageSignaturePad already initialized, skipping...');
        return;
    }
    window.__MYIS_InspectionDamageSignaturePad_Initialized__ = true;

    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', function() {
        const canvas = document.getElementById('signature-pad');
        const clearButton = document.getElementById('clear-signature');
        const submitButton = document.getElementById('submit-inspection-damage-signature');
        const tokenInput = document.getElementById('inspection_damage_token');
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
                ctx.clearRect(0, 0, canvas.width, canvas.height);
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
            if (!hasSignature) {
                showStatusMessage('danger', '<strong>Error:</strong> Please provide your signature to acknowledge the inspection damage report.');
                container.classList.add('error');
                setTimeout(() => container.classList.remove('error'), 2000);
                return false;
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

            // Get data
            const token = tokenInput.value;
            const signatureData = canvas.toDataURL('image/png').split(',')[1]; // Get base64 without prefix

            // Disable button and show loading
            submitButton.disabled = true;
            submitButton.classList.add('loading');
            const originalText = submitButton.innerHTML;
            submitButton.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Submitting...';

            // Send to server
            fetch('/sign/inspection/damage/submit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        token: token,
                        signature_data: signatureData
                    }
                })
            })
            .then(response => response.json())
            .then(data => {
                submitButton.disabled = false;
                submitButton.classList.remove('loading');
                submitButton.innerHTML = originalText;

                // Support both JSON-RPC format and direct response
                const response = data.result || data;

                if (response && response.success) {
                    // Success
                    showStatusMessage('success', `
                        <strong><i class="fa fa-check-circle"></i> Success!</strong><br>
                        ${response.message || 'Your approval has been recorded successfully.'}
                    `);

                    // Disable form
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
                submitButton.disabled = false;
                submitButton.classList.remove('loading');
                submitButton.innerHTML = originalText;

                showStatusMessage('danger', `
                    <strong>Error:</strong> Failed to submit acknowledgment.
                    Please check your internet connection and try again.
                `);
            });
        });

        // Add click-to-enlarge for inspection photos
        const inspectionPhotos = document.querySelectorAll('.img-thumbnail');
        inspectionPhotos.forEach(photo => {
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
        }

    });
})();
