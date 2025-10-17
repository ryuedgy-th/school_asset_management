/**
 * MYIS International School - Teacher Damage Report Signature Pad
 * Canvas-based signature capture for teacher damage acknowledgment
 * Supports both mouse and touch input
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

    // Photo click handler (defined once globally)
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

    // Initialization function
    function initTeacherDamageSignaturePad() {

        const canvas = document.getElementById('signature-pad');
        const clearButton = document.getElementById('clear-signature');
        const submitButton = document.getElementById('submit-damage-signature');
        const tokenInput = document.getElementById('damage_token');
        const statusMessage = document.getElementById('status-message');
        const container = canvas && canvas.closest('.signature-pad-container');

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
            container && container.classList.add('signing');
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
            container && container.classList.remove('signing');

            if (hasSignature) {
                container && container.classList.add('has-signature');
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
                container && container.classList.remove('has-signature');
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
                showStatusMessage('danger', '<strong>Error:</strong> Please provide your signature to acknowledge the damage report.');
                container && container.classList.add('error');
                setTimeout(() => container && container.classList.remove('error'), 2000);
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

                // Check token input exists
                if (!tokenInput) {
                    showStatusMessage('danger', '<strong>Error:</strong> Token not found. Please refresh the page.');
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

                // Send to server - TEACHER ROUTE
                fetch('/sign/teacher/damage/submit', {
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
                    console.log('Raw response data:', JSON.stringify(data, null, 2));

                    submitButton.disabled = false;
                    submitButton.classList.remove('loading');
                    submitButton.innerHTML = originalText;

                    // Support both JSON-RPC format and direct response
                    const response = data.result || data;
                    console.log('Parsed response:', JSON.stringify(response, null, 2));

                    if (response && response.success) {
                        // Success
                        showStatusMessage('success', `
                            <strong><i class="fa fa-check-circle"></i> Success!</strong><br>
                            ${response.message || 'Your acknowledgment has been recorded successfully.'}
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
                        console.error('Submission error - full response:', JSON.stringify(response, null, 2));

                        let errorMsg = 'An unknown error occurred.';

                        // Check for error in various locations
                        if (response?.error) {
                            console.log('Error type:', typeof response.error);
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

                        console.error('Final error message:', errorMsg);
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
        }

        // Bind photo click handler (remove old, add new)
        console.log('Binding photo click handler');
        document.body.removeEventListener('click', window.__MYIS_TeacherDamagePhotoClickHandler__);
        document.body.addEventListener('click', window.__MYIS_TeacherDamagePhotoClickHandler__);
    }

    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTeacherDamageSignaturePad, { once: true });
    } else {
        // DOM already loaded
        initTeacherDamageSignaturePad();
    }
})();
