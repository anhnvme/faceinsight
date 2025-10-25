/**
 * Common utilities and functions shared across all pages
 */

// ==================== String Utilities ====================

/**
 * Convert Vietnamese/Unicode text to ASCII slug (a-z + numbers allowed)
 * @param {string} text - Input text
 * @returns {string} Slugified text (a-z and 0-9 only)
 */
function slugifyName(text) {
    const normalized = text.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    return normalized.toLowerCase().replace(/[^a-z0-9]/g, '');
}

/**
 * Initialize auto-slugify name input with preview
 * @param {string} nicknameInputId - ID of nickname input element
 * @param {string} nameInputId - ID of name input element  
 * @param {string} previewId - ID of preview element
 * @returns {object} Cleanup function and state
 */
function initializeAutoSlugInput(nicknameInputId, nameInputId, previewId) {
    const nicknameInput = document.getElementById(nicknameInputId);
    const nameInput = document.getElementById(nameInputId);
    const preview = document.getElementById(previewId);
    
    if (!nicknameInput || !nameInput || !preview) {
        console.error('Auto-slug inputs not found:', { nicknameInputId, nameInputId, previewId });
        return null;
    }
    
    let isNameManuallyEdited = false;
    
    function updateNamePreview(value) {
        const original = value.trim();
        const slugified = slugifyName(original);
        
        if (!original) {
            preview.textContent = 'Nhập Nickname để tự động tạo tên, hoặc nhập tên tùy chỉnh';
            preview.style.color = '#667eea';
        } else if (slugified && slugified === original) {
            // Valid: a-z and numbers only
            preview.textContent = '✓ Tên hợp lệ: ' + original;
            preview.style.color = '#4caf50';
        } else if (slugified && slugified !== original) {
            // Will be converted
            preview.textContent = '→ Sẽ chuyển thành: ' + slugified + ' (loại bỏ dấu và ký tự đặc biệt)';
            preview.style.color = '#ff9800';
        } else {
            // Invalid: no letters at all
            preview.textContent = '⚠️ Tên phải chứa ít nhất 1 chữ cái';
            preview.style.color = '#f44336';
        }
    }
    
    // Auto-fill name when nickname changes
    const nicknameHandler = function(e) {
        const original = e.target.value;
        const slugified = slugifyName(original);
        
        // Auto-fill name only if user hasn't manually edited it
        if (!isNameManuallyEdited) {
            nameInput.value = slugified || '';
        }
        
        // Always update preview based on current name field
        updateNamePreview(nameInput.value);
    };
    
    // Mark as manually edited when user types in name field
    const nameHandler = function(e) {
        isNameManuallyEdited = true;
        updateNamePreview(e.target.value);
    };
    
    nicknameInput.addEventListener('input', nicknameHandler);
    nameInput.addEventListener('input', nameHandler);
    
    // Return cleanup and reset functions
    return {
        reset: function() {
            isNameManuallyEdited = false;
            preview.textContent = 'Nhập Nickname để tự động tạo tên, hoặc nhập tên tùy chỉnh';
            preview.style.color = '#667eea';
        },
        cleanup: function() {
            nicknameInput.removeEventListener('input', nicknameHandler);
            nameInput.removeEventListener('input', nameHandler);
        }
    };
}

// ==================== Progress Indicators ====================

/**
 * Show global progress indicator
 * @param {string} title - Progress title
 * @param {string} detail - Progress detail message
 */
function showProgress(title, detail) {
    const progress = document.getElementById('globalProgress');
    if (!progress) return;
    
    const progressTitle = document.getElementById('progressTitle');
    const progressDetail = document.getElementById('progressDetail');
    const spinner = progress.querySelector('.progress-spinner');
    
    progressTitle.textContent = title;
    progressDetail.textContent = detail;
    spinner.className = 'progress-spinner';
    spinner.style.display = 'block'; // Ensure spinner is visible
    progress.style.display = 'flex';
}

/**
 * Hide global progress indicator
 * @param {number} delay - Delay in milliseconds before hiding
 */
function hideProgress(delay = 0) {
    setTimeout(() => {
        const progress = document.getElementById('globalProgress');
        if (progress) {
            progress.style.display = 'none';
        }
    }, delay);
}

/**
 * Show inline status message (for settings, test pages)
 * @param {string} statusElementId - ID of status element
 * @param {string} title - Status title
 * @param {string} detail - Status detail message (optional)
 * @param {string} type - Status type: 'info', 'success', 'error'
 */
function showInlineStatus(statusElementId, title, detail = '', type = 'info') {
    const statusDiv = document.getElementById(statusElementId);
    const statusText = statusDiv ? statusDiv.querySelector('[id$="Text"]') || statusDiv : null;
    
    if (!statusDiv) {
        console.warn('Status element not found:', statusElementId);
        return;
    }
    
    // Combine title and detail
    const message = detail ? `${title} - ${detail}` : title;
    
    if (statusText && statusText !== statusDiv) {
        statusText.textContent = message;
    } else {
        statusDiv.textContent = message;
    }
    
    statusDiv.classList.remove('d-none');
    statusDiv.style.display = 'block';
    
    // Change color based on type
    if (type === 'success') {
        statusDiv.style.background = '#e8f5e9';
        statusDiv.style.borderLeftColor = '#4caf50';
    } else if (type === 'error') {
        statusDiv.style.background = '#ffebee';
        statusDiv.style.borderLeftColor = '#f44336';
    } else {
        statusDiv.style.background = '#e3f2fd';
        statusDiv.style.borderLeftColor = '#2196f3';
    }
}

/**
 * Hide inline status message
 * @param {string} statusElementId - ID of status element
 * @param {number} delay - Delay in milliseconds before hiding
 */
function hideInlineStatus(statusElementId, delay = 0) {
    setTimeout(() => {
        const statusDiv = document.getElementById(statusElementId);
        if (statusDiv) {
            statusDiv.classList.add('d-none');
            statusDiv.style.display = 'none';
        }
    }, delay);
}

/**
 * Show success message
 * @param {string} title - Success title
 * @param {string} detail - Success detail message
 * @param {boolean} autoHide - Auto hide after delay
 */
function showSuccess(title, detail, autoHide = true) {
    const progress = document.getElementById('globalProgress');
    if (!progress) return;
    
    const progressTitle = document.getElementById('progressTitle');
    const progressDetail = document.getElementById('progressDetail');
    const spinner = progress.querySelector('.progress-spinner');
    
    progressTitle.textContent = '✅ ' + title;
    progressDetail.textContent = detail;
    spinner.className = 'progress-spinner success';
    spinner.style.display = 'none'; // Hide spinner on success
    progress.style.display = 'flex';
    
    if (autoHide) {
        hideProgress(1500);
    }
}

/**
 * Show error message
 * @param {string} title - Error title
 * @param {string} detail - Error detail message
 */
function showError(title, detail) {
    const progress = document.getElementById('globalProgress');
    if (!progress) return;
    
    const progressTitle = document.getElementById('progressTitle');
    const progressDetail = document.getElementById('progressDetail');
    const spinner = progress.querySelector('.progress-spinner');
    
    progressTitle.textContent = '❌ ' + title;
    progressDetail.textContent = detail;
    spinner.className = 'progress-spinner error';
    spinner.style.display = 'none'; // Hide spinner on error
    progress.style.display = 'flex';
    
    hideProgress(2000);
}

// ==================== Modal Utilities ====================

/**
 * Close modal when clicking outside
 * @param {Event} event - Click event
 * @param {string[]} modalIds - Array of modal IDs to check
 */
function handleModalOutsideClick(event, modalIds) {
    modalIds.forEach(id => {
        const modal = document.getElementById(id);
        if (event.target === modal) {
            modal.classList.add('d-none');
        }
    });
}

// ==================== API Helpers ====================

/**
 * Make API request with error handling
 * @param {string} url - API endpoint
 * @param {object} options - Fetch options
 * @returns {Promise<object>} Response data
 */
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, options);
        const data = await response.json();
        return { success: response.ok, data, status: response.status };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

// ==================== Bounding Box Drawing ====================

/**
 * Draw bounding box on canvas overlay
 * @param {HTMLImageElement} imgElement - Image element to draw bbox on
 * @param {object} bbox - Bounding box data {x, y, width, height, img_width, img_height}
 * @param {object} options - Drawing options
 * @param {string} options.color - Border color (default: '#4caf50')
 * @param {number} options.lineWidth - Border width (default: 2)
 * @param {string} options.label - Label text to display (optional)
 * @param {HTMLCanvasElement} options.canvas - Existing canvas element (optional)
 * @returns {HTMLCanvasElement} Canvas element with drawn bbox
 */
function drawBoundingBox(imgElement, bbox, options = {}) {
    const {
        color = '#4caf50',
        lineWidth = 2,
        label = null,
        canvas = null
    } = options;
    
    // Get or create canvas
    let canvasElement = canvas;
    if (!canvasElement) {
        canvasElement = document.createElement('canvas');
        canvasElement.style.position = 'absolute';
        canvasElement.style.top = '0';
        canvasElement.style.left = '0';
        canvasElement.style.pointerEvents = 'none';
    }
    
    function draw() {
        const displayWidth = imgElement.offsetWidth || imgElement.clientWidth;
        const displayHeight = imgElement.offsetHeight || imgElement.clientHeight;
        
        if (!displayWidth || !displayHeight) return;
        
        canvasElement.width = displayWidth;
        canvasElement.height = displayHeight;
        canvasElement.style.width = displayWidth + 'px';
        canvasElement.style.height = displayHeight + 'px';
        
        const ctx = canvasElement.getContext('2d');
        ctx.clearRect(0, 0, displayWidth, displayHeight);
        
        const scaleX = displayWidth / bbox.img_width;
        const scaleY = displayHeight / bbox.img_height;
        
        // Draw bbox rectangle
        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;
        ctx.strokeRect(
            bbox.x * scaleX,
            bbox.y * scaleY,
            bbox.width * scaleX,
            bbox.height * scaleY
        );
        
        // Draw label if provided
        if (label) {
            const labelX = bbox.x * scaleX;
            const labelY = Math.max(0, (bbox.y * scaleY) - 35);
            
            ctx.fillStyle = color;
            ctx.font = '600 14px system-ui';
            const textWidth = ctx.measureText(label).width;
            
            // Label background
            ctx.fillRect(labelX, labelY, textWidth + 12, 28);
            
            // Label text
            ctx.fillStyle = 'white';
            ctx.fillText(label, labelX + 6, labelY + 19);
        }
    }
    
    // Draw when image loads
    if (imgElement.complete && imgElement.naturalHeight !== 0) {
        draw();
    } else {
        imgElement.addEventListener('load', draw);
    }
    
    return canvasElement;
}

// ==================== Image Preview Modal ====================

/**
 * Show image preview in modal with ESC key support
 * @param {string} imagePath - Path to image (can include 'static/' prefix)
 * @param {string} title - Modal title (optional)
 */
function showImagePreview(imagePath, title = 'Ảnh Gốc') {
    if (!imagePath) {
        alert('Không tìm thấy ảnh');
        return;
    }
    
    const modal = document.getElementById('imagePreviewModal');
    const img = document.getElementById('previewImage');
    const titleEl = document.getElementById('imagePreviewTitle');
    
    if (!modal || !img) {
        console.error('Image preview modal not found');
        return;
    }
    
    // Remove 'static/' prefix if exists and ensure it starts with /static/
    const cleanPath = imagePath.replace('static/', '');
    img.src = `/static/${cleanPath}`;
    
    if (titleEl) {
        titleEl.textContent = title;
    }
    
    modal.classList.remove('d-none');
    
    // Add ESC key listener for this modal instance
    const escHandler = function(e) {
        if (e.key === 'Escape') {
            closeImagePreview();
            document.removeEventListener('keydown', escHandler);
        }
    };
    document.addEventListener('keydown', escHandler);
}

/**
 * Close image preview modal and free memory
 */
function closeImagePreview() {
    const modal = document.getElementById('imagePreviewModal');
    const img = document.getElementById('previewImage');
    
    if (modal) {
        modal.classList.add('d-none');
    }
    
    if (img) {
        // Clear image to free memory
        img.src = '';
    }
}

// Make globally accessible
window.showImagePreview = showImagePreview;
window.closeImagePreview = closeImagePreview;

