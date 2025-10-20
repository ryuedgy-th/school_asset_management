/**
 * MYIS International School - Damage Case Approval Signature Pad
 * Canvas-based signature capture for manager approval
 * Supports both mouse and touch input
 */

(function() {
    'use strict';

    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', function() {
        const canvas = document.getElementById('signature-pad');
        const clearButton = document.getElementById('clear-signature');
        const submitButton = document.getElementById('submit-approval');
        const tokenInput = document.getElementById('approval_token');
        const notesInput = document.getElementById('approval-notes');
        const alertMessage = document.getElementById('alert-message');
        const btnApprove = document.getElementById('btn-approve');
        const btnReject = document.getElementById('btn-reject');
        const selectedDecision = document.getElementById('selected-decision');
        const container = canvas ? canvas.closest('.signature-pad-container') : null;

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
            if (container) container.classList.add('signing');
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
            if (container) container.classList.remove('signing');

            if (hasSignature && container) {
                container.classList.add('has-signature');
            }
            checkFormValid();
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
        clearButton.addEventListener('click', function() {
            // Save the current transformation matrix
            ctx.save();
            // Use identity matrix to clear entire canvas
            ctx.setTransform(1, 0, 0, 1, 0, 0);
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            // Restore the transformation
            ctx.restore();

            hasSignature = false;
            if (container) container.classList.remove('has-signature');
            hideAlert();
            checkFormValid();
        });

        // Decision selection
        function checkFormValid() {
            const hasDecision = selectedDecision && selectedDecision.value !== '';
            submitButton.disabled = !(hasDecision && hasSignature);
        }

        if (btnApprove) {
            btnApprove.addEventListener('click', function() {
                selectedDecision.value = 'approve';
                btnApprove.classList.add('active');
                if (btnReject) btnReject.classList.remove('active');
                checkFormValid();
            });
        }

        if (btnReject) {
            btnReject.addEventListener('click', function() {
                selectedDecision.value = 'reject';
                btnReject.classList.add('active');
                if (btnApprove) btnApprove.classList.remove('active');
                checkFormValid();
            });
        }

        // Show alert message
        function showAlert(message, type) {
            alertMessage.className = `alert alert-${type}`;
            alertMessage.innerHTML = message;
            alertMessage.style.display = 'block';
            alertMessage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }

        // Hide alert message
        function hideAlert() {
            if (alertMessage) {
                alertMessage.style.display = 'none';
                alertMessage.innerHTML = '';
            }
        }

        // Submit approval
        submitButton.addEventListener('click', async function() {
            hideAlert();

            const token = tokenInput.value;
            const decision = selectedDecision.value;
            const notes = notesInput ? notesInput.value : '';
            const signatureData = canvas.toDataURL('image/png').split(',')[1]; // Get base64 without prefix

            if (!decision) {
                showAlert('<strong>Error:</strong> Please select Approve or Reject.', 'danger');
                return;
            }

            if (!hasSignature) {
                showAlert('<strong>Error:</strong> Please provide your signature.', 'danger');
                if (container) {
                    container.classList.add('error');
                    setTimeout(() => container.classList.remove('error'), 2000);
                }
                return;
            }

            // Disable submit button
            submitButton.disabled = true;
            const originalText = submitButton.innerHTML;
            submitButton.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Submitting...';

            try {
                const response = await fetch('/damage/approve/submit', {
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
                            decision: decision,
                            notes: notes,
                        },
                    }),
                });

                const result = await response.json();

                if (result.error) {
                    throw new Error(result.error.data?.message || 'Unknown error occurred');
                }

                if (result.result && result.result.success) {
                    showAlert(`<strong><i class="fa fa-check-circle"></i> Success!</strong><br>${result.result.message}`, 'success');

                    // Disable all controls
                    if (btnApprove) btnApprove.style.pointerEvents = 'none';
                    if (btnReject) btnReject.style.pointerEvents = 'none';
                    if (notesInput) notesInput.disabled = true;
                    clearButton.disabled = true;
                    canvas.style.pointerEvents = 'none';

                    // Redirect after 3 seconds
                    setTimeout(function() {
                        window.location.href = '/';
                    }, 3000);
                } else {
                    throw new Error(result.result?.error || 'Failed to submit approval');
                }

            } catch (error) {
                console.error('Error submitting approval:', error);
                showAlert(`<strong>Error:</strong> ${error.message || 'An error occurred. Please try again.'}`, 'danger');
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
            }
        });

        // Initial form validation
        checkFormValid();
    });
})();
