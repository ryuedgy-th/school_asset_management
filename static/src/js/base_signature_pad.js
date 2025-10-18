/**
 * MYIS International School - Base Signature Pad
 * Reusable ES6 class for canvas-based signature capture
 * Supports both mouse and touch input
 *
 * @class BaseSignaturePad
 * @version 1.0.0
 * @author MYIS IT Department
 */

(function() {
    'use strict';

    /**
     * Base class for signature pad functionality
     *
     * @example
     * const signaturePad = new BaseSignaturePad({
     *   canvasId: 'signature-pad',
     *   clearButtonId: 'clear-signature',
     *   submitButtonId: 'submit-signature',
     *   tokenInputId: 'signature_token',
     *   statusMessageId: 'status-message',
     *   submitEndpoint: '/sign/student/checkout/submit',
     *   requiredFields: [
     *     { type: 'text', id: 'parent_name_input', errorMessage: 'Please enter your name' }
     *   ],
     *   requiredCheckboxes: [
     *     { id: 'consent_privacy_policy', label: 'Privacy Policy Consent' }
     *   ],
     *   collectConsents: true,
     *   onBeforeSubmit: (formData) => { ... },
     *   onSuccess: (response) => { ... }
     * });
     */
    class BaseSignaturePad {
        /**
         * Create a signature pad instance
         *
         * @param {Object} config - Configuration object
         * @param {string} config.canvasId - ID of the canvas element
         * @param {string} config.clearButtonId - ID of clear button
         * @param {string} config.submitButtonId - ID of submit button
         * @param {string} config.tokenInputId - ID of token input field
         * @param {string} config.statusMessageId - ID of status message container
         * @param {string} config.submitEndpoint - API endpoint for form submission
         * @param {Array} [config.requiredFields=[]] - Required input fields to validate
         * @param {Array} [config.requiredCheckboxes=[]] - Required checkboxes to validate
         * @param {boolean} [config.collectConsents=false] - Whether to collect PDPA consents
         * @param {Function} [config.onBeforeSubmit] - Callback before submission
         * @param {Function} [config.onSuccess] - Callback on successful submission
         * @param {Function} [config.customValidation] - Custom validation function
         * @param {boolean} [config.preventConcurrentSubmit=true] - Prevent double-click submission
         */
        constructor(config) {
            this.config = {
                requiredFields: [],
                requiredCheckboxes: [],
                collectConsents: false,
                preventConcurrentSubmit: true,
                ...config
            };

            // State
            this.isDrawing = false;
            this.hasSignature = false;
            this.lastX = 0;
            this.lastY = 0;
            this.isSubmitting = false;

            // DOM elements
            this.canvas = null;
            this.ctx = null;
            this.clearButton = null;
            this.submitButton = null;
            this.tokenInput = null;
            this.statusMessage = null;
            this.container = null;

            // Initialize
            this.init();
        }

        /**
         * Initialize the signature pad
         */
        init() {
            // Get DOM elements
            this.canvas = document.getElementById(this.config.canvasId);
            if (!this.canvas) {
                console.error(`BaseSignaturePad: Canvas not found: ${this.config.canvasId}`);
                return;
            }

            this.clearButton = document.getElementById(this.config.clearButtonId);
            this.submitButton = document.getElementById(this.config.submitButtonId);
            this.tokenInput = document.getElementById(this.config.tokenInputId);
            this.statusMessage = document.getElementById(this.config.statusMessageId);
            this.container = this.canvas.closest('.signature-pad-container');

            // Setup canvas
            this.ctx = this.canvas.getContext('2d');
            this.setupCanvas();
            this.bindEvents();

            console.log('BaseSignaturePad initialized:', {
                canvas: this.config.canvasId,
                endpoint: this.config.submitEndpoint
            });
        }

        /**
         * Setup canvas size and drawing properties
         */
        setupCanvas() {
            const resizeCanvas = () => {
                const ratio = Math.max(window.devicePixelRatio || 1, 1);
                this.canvas.width = this.canvas.offsetWidth * ratio;
                this.canvas.height = this.canvas.offsetHeight * ratio;
                this.canvas.getContext('2d').scale(ratio, ratio);
                this.ctx.strokeStyle = '#000000';
                this.ctx.lineWidth = 2;
                this.ctx.lineCap = 'round';
                this.ctx.lineJoin = 'round';
            };

            resizeCanvas();
            window.addEventListener('resize', resizeCanvas);
        }

        /**
         * Bind all event listeners
         */
        bindEvents() {
            // Mouse events
            this.canvas.addEventListener('mousedown', (e) => this.startDrawing(e));
            this.canvas.addEventListener('mousemove', (e) => this.draw(e));
            this.canvas.addEventListener('mouseup', (e) => this.stopDrawing(e));
            this.canvas.addEventListener('mouseout', (e) => this.stopDrawing(e));

            // Touch events
            this.canvas.addEventListener('touchstart', (e) => this.startDrawing(e));
            this.canvas.addEventListener('touchmove', (e) => this.draw(e));
            this.canvas.addEventListener('touchend', (e) => this.stopDrawing(e));
            this.canvas.addEventListener('touchcancel', (e) => this.stopDrawing(e));

            // Clear button
            if (this.clearButton) {
                this.clearButton.addEventListener('click', () => this.clear());
            }

            // Submit button
            if (this.submitButton) {
                this.submitButton.addEventListener('click', () => this.handleSubmit());
            }

            // Required fields (hide status message on input)
            this.config.requiredFields.forEach(field => {
                const element = document.getElementById(field.id);
                if (element) {
                    element.addEventListener('input', () => this.hideStatusMessage());
                }
            });

            // Required checkboxes (hide status message on change)
            this.config.requiredCheckboxes.forEach(checkbox => {
                const element = document.getElementById(checkbox.id);
                if (element) {
                    element.addEventListener('change', () => this.hideStatusMessage());
                }
            });
        }

        /**
         * Get coordinates relative to canvas
         *
         * @param {Event} event - Mouse or touch event
         * @returns {Object} Coordinates {x, y}
         */
        getCoordinates(event) {
            const rect = this.canvas.getBoundingClientRect();
            const clientX = event.touches ? event.touches[0].clientX : event.clientX;
            const clientY = event.touches ? event.touches[0].clientY : event.clientY;

            return {
                x: clientX - rect.left,
                y: clientY - rect.top
            };
        }

        /**
         * Start drawing
         *
         * @param {Event} event - Mouse or touch event
         */
        startDrawing(event) {
            event.preventDefault();
            this.isDrawing = true;
            const coords = this.getCoordinates(event);
            this.lastX = coords.x;
            this.lastY = coords.y;
            if (this.container) {
                this.container.classList.add('signing');
            }
        }

        /**
         * Draw line on canvas
         *
         * @param {Event} event - Mouse or touch event
         */
        draw(event) {
            if (!this.isDrawing) return;
            event.preventDefault();

            const coords = this.getCoordinates(event);

            this.ctx.beginPath();
            this.ctx.moveTo(this.lastX, this.lastY);
            this.ctx.lineTo(coords.x, coords.y);
            this.ctx.stroke();

            this.lastX = coords.x;
            this.lastY = coords.y;
            this.hasSignature = true;
        }

        /**
         * Stop drawing
         *
         * @param {Event} event - Mouse or touch event
         */
        stopDrawing(event) {
            if (!this.isDrawing) return;
            event.preventDefault();
            this.isDrawing = false;

            if (this.container) {
                this.container.classList.remove('signing');
                if (this.hasSignature) {
                    this.container.classList.add('has-signature');
                }
            }
        }

        /**
         * Clear the signature
         */
        clear() {
            // Save the current transformation matrix
            this.ctx.save();
            // Use identity matrix to clear entire canvas
            this.ctx.setTransform(1, 0, 0, 1, 0, 0);
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            // Restore the transformation
            this.ctx.restore();

            this.hasSignature = false;
            if (this.container) {
                this.container.classList.remove('has-signature');
            }
            this.hideStatusMessage();
        }

        /**
         * Show status message
         *
         * @param {string} type - Message type (success, danger, warning, info)
         * @param {string} message - Message HTML content
         */
        showStatusMessage(type, message) {
            if (!this.statusMessage) return;

            this.statusMessage.innerHTML = `
                <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                    ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `;
            this.statusMessage.style.display = 'block';
            this.statusMessage.classList.add('show');
        }

        /**
         * Hide status message
         */
        hideStatusMessage() {
            if (!this.statusMessage) return;

            this.statusMessage.style.display = 'none';
            this.statusMessage.classList.remove('show');
            this.statusMessage.innerHTML = '';
        }

        /**
         * Validate form before submission
         *
         * @returns {boolean} True if form is valid
         */
        validateForm() {
            // Validate required text fields
            for (const field of this.config.requiredFields) {
                const element = document.getElementById(field.id);
                if (!element) {
                    console.error(`Required field not found: ${field.id}`);
                    this.showStatusMessage('danger',
                        `<strong>Error:</strong> Form element missing. Please refresh the page.`);
                    return false;
                }

                const value = element.value.trim();
                if (!value) {
                    this.showStatusMessage('danger', field.errorMessage);
                    element.focus();
                    return false;
                }
            }

            // Validate signature
            if (!this.hasSignature) {
                this.showStatusMessage('danger',
                    '<strong>Error:</strong> Please provide your signature above.<br><strong>กรุณาเซ็นชื่อด้านบน</strong>');
                if (this.container) {
                    this.container.classList.add('error');
                    setTimeout(() => this.container.classList.remove('error'), 2000);
                }
                return false;
            }

            // Validate required checkboxes
            for (const checkbox of this.config.requiredCheckboxes) {
                const element = document.getElementById(checkbox.id);
                if (!element) {
                    console.error(`Consent checkbox not found: ${checkbox.id}`);
                    this.showStatusMessage('danger',
                        `<strong>Error:</strong> Required form element missing: <strong>${checkbox.label}</strong>. Please refresh the page.`);
                    return false;
                }

                if (!element.checked) {
                    this.showStatusMessage('danger',
                        `<strong>Error:</strong> Please check the required consent box: <strong>${checkbox.label}</strong>`);
                    element.focus();
                    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    return false;
                }
            }

            // Custom validation
            if (this.config.customValidation) {
                const customResult = this.config.customValidation();
                if (!customResult.valid) {
                    this.showStatusMessage('danger', customResult.errorMessage);
                    return false;
                }
            }

            return true;
        }

        /**
         * Collect form data for submission
         *
         * @returns {Object} Form data object
         */
        collectFormData() {
            const formData = {
                token: this.tokenInput ? this.tokenInput.value : '',
                signature_data: this.canvas.toDataURL('image/png').split(',')[1] // Base64 without prefix
            };

            // Collect required fields
            this.config.requiredFields.forEach(field => {
                const element = document.getElementById(field.id);
                if (element) {
                    formData[field.id] = element.value.trim();
                }
            });

            // Collect PDPA consents if enabled
            if (this.config.collectConsents) {
                const consentIds = [
                    'consent_privacy_policy',
                    'consent_digital_signature',
                    'consent_email',
                    'consent_liability'
                ];

                formData.consents = {};
                consentIds.forEach(id => {
                    const element = document.getElementById(id);
                    formData.consents[id] = element ? element.checked : false;
                });
            }

            return formData;
        }

        /**
         * Handle form submission
         */
        async handleSubmit() {
            // Prevent concurrent submissions
            if (this.config.preventConcurrentSubmit && this.isSubmitting) {
                console.log('Already submitting, ignoring duplicate request');
                return;
            }

            this.hideStatusMessage();

            // Validate form
            if (!this.validateForm()) {
                return;
            }

            // Set submitting flag
            this.isSubmitting = true;

            // Collect form data
            const formData = this.collectFormData();

            // Call onBeforeSubmit hook
            if (this.config.onBeforeSubmit) {
                this.config.onBeforeSubmit(formData);
            }

            // Disable button and show loading
            this.submitButton.disabled = true;
            this.submitButton.classList.add('loading');
            const originalText = this.submitButton.innerHTML;
            this.submitButton.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Submitting...';

            try {
                // Send to server
                const response = await fetch(this.config.submitEndpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: formData
                    })
                });

                const data = await response.json();

                // Reset submitting flag
                this.isSubmitting = false;
                this.submitButton.disabled = false;
                this.submitButton.classList.remove('loading');
                this.submitButton.innerHTML = originalText;

                // Support both JSON-RPC format and direct response
                const result = data.result || data;

                if (result && result.success) {
                    // Success
                    this.showStatusMessage('success', `
                        <strong><i class="fa fa-check-circle"></i> Success!</strong><br>
                        ${result.message || 'Your signature has been recorded successfully.'}
                    `);

                    // Call onSuccess hook
                    if (this.config.onSuccess) {
                        this.config.onSuccess(result);
                    } else {
                        // Default success behavior
                        this.disableForm();
                        setTimeout(() => window.location.reload(), 3000);
                    }
                } else {
                    // Error
                    this.handleError(result);
                }

            } catch (error) {
                console.error('Submission error:', error);

                // Reset submitting flag
                this.isSubmitting = false;
                this.submitButton.disabled = false;
                this.submitButton.classList.remove('loading');
                this.submitButton.innerHTML = originalText;

                this.showStatusMessage('danger', `
                    <strong>Error:</strong> Failed to submit signature.
                    Please check your internet connection and try again.
                `);
            }
        }

        /**
         * Handle error response
         *
         * @param {Object} response - Error response object
         */
        handleError(response) {
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
            } else if (response?.message) {
                errorMsg = response.message;
            }

            console.error('Submission error:', response);
            this.showStatusMessage('danger', `<strong>Error:</strong> ${errorMsg}`);
        }

        /**
         * Disable form after successful submission
         */
        disableForm() {
            // Disable all required fields
            this.config.requiredFields.forEach(field => {
                const element = document.getElementById(field.id);
                if (element) element.disabled = true;
            });

            // Disable all checkboxes
            this.config.requiredCheckboxes.forEach(checkbox => {
                const element = document.getElementById(checkbox.id);
                if (element) element.disabled = true;
            });

            // Disable buttons and canvas
            if (this.clearButton) this.clearButton.disabled = true;
            if (this.submitButton) this.submitButton.disabled = true;
            this.canvas.style.pointerEvents = 'none';
        }

        /**
         * Get signature as data URL
         *
         * @returns {string} Base64 encoded PNG image
         */
        toDataURL() {
            return this.canvas.toDataURL('image/png');
        }
    }

    // Export to global scope
    window.BaseSignaturePad = BaseSignaturePad;

})();
