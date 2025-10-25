/**
 * Test recognition page
 */

// ==================== Initialization ====================

document.addEventListener('DOMContentLoaded', function() {
    initializeImageUpload();
});

// ==================== Image Upload & Recognition ====================

async function handleImageUpload(file) {
    if (!file) return;
    
    const formData = new FormData();
    formData.append('image', file);
    
    const preview = document.getElementById('preview');
    const resultDiv = document.getElementById('result');
    const uploadSection = document.getElementById('uploadSection');
    const splitContainer = document.getElementById('splitContainer');
    
    // Show initial preview in upload section
    const previewURL = URL.createObjectURL(file);
    uploadSection.innerHTML = `
        <input type="file" id="testImage" accept="image/*" style="display:none">
        <button onclick="document.getElementById('testImage').click()" class="btn btn-primary">📸 Chọn Ảnh Khác</button>
        <div style="margin-top: 1rem;">
            <img src="${previewURL}" style="max-width: 100%; max-height: 400px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
        </div>
    `;
    
    // Re-bind file input event
    document.getElementById('testImage').onchange = (e) => handleImageUpload(e.target.files[0]);
    
    // Reset split view
    preview.innerHTML = '';
    resultDiv.innerHTML = '';
    splitContainer.style.display = 'none';
    splitContainer.querySelector('.image-panel').classList.remove('slide-in-left');
    splitContainer.querySelector('.result-panel').classList.remove('slide-in-right');
    
    try {
        // Step 1: Uploading
        showInlineStatus('testStatus', '📤 Đang tải ảnh lên...', 'Preparing image for recognition...');
        await new Promise(r => setTimeout(r, 300));
        
        // Step 2: Processing
        showInlineStatus('testStatus', '🔍 Đang phân tích khuôn mặt...', 'Detecting face and extracting features...');
        
        const response = await fetch('/test/recognize', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayResults(result, preview, resultDiv, uploadSection, splitContainer);
        } else {
            showInlineStatus('testStatus', '❌ Lỗi xử lý', result.error, 'error');
            hideInlineStatus('testStatus', 3000);
        }
    } catch (error) {
        showInlineStatus('testStatus', '❌ Lỗi kết nối', error.message, 'error');
        hideInlineStatus('testStatus', 3000);
    }
}

function displayResults(result, preview, resultDiv, uploadSection, splitContainer) {
    // Hide upload section and show split screen
    uploadSection.style.display = 'none';
    splitContainer.style.display = 'flex';
    
    // Trigger animation after a brief delay
    setTimeout(() => {
        document.getElementById('imagePanel').classList.add('slide-in-left');
        document.getElementById('resultPanel').classList.add('slide-in-right');
    }, 50);
    
    // Update preview with bounding box
    if (result.bbox && result.image_url) {
        renderImageWithBoundingBox(result, preview);
    }
    
    // Display recognition results
    if (result.matched) {
        displayMatchedResult(result, resultDiv);
    } else {
        displayUnknownResult(result, resultDiv);
    }
}

function renderImageWithBoundingBox(result, preview) {
    const bbox = result.bbox;
    
    preview.innerHTML = `
        <div style="position: relative; display: inline-block; max-width: 100%;">
            <img id="resultImage" src="${result.image_url}" style="max-width: 100%; height: auto; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); display: block;">
        </div>
    `;
    
    // Use shared function to draw bbox
    const img = document.getElementById('resultImage');
    const color = result.matched ? '#4caf50' : '#f44336';
    const label = result.matched ? result.name : null;
    
    img.onload = function() {
        const canvas = drawBoundingBox(this, bbox, {
            color: color,
            lineWidth: 3,
            label: label
        });
        
        // Add glow animation
        canvas.style.boxShadow = `0 0 0 2px rgba(255,255,255,0.5), 0 0 20px ${result.matched ? 'rgba(76,175,80,0.6)' : 'rgba(244,67,54,0.6)'}`;
        canvas.style.animation = 'bboxPulse 2s ease-in-out infinite';
        
        // Append canvas to parent
        this.parentElement.appendChild(canvas);
    };
}

function displayMatchedResult(result, resultDiv) {
    showInlineStatus('testStatus', '✅ Nhận diện thành công!', `Tìm thấy kết quả khớp với ${result.name}`, 'success');
    
    const processingTimeText = result.processing_time ? 
        `${result.processing_time.total}ms (detect: ${result.processing_time.detect}ms, match: ${result.processing_time.match}ms)` : 'N/A';
    
    resultDiv.innerHTML = `
        <div class="result-success">
            <button onclick="document.getElementById('testImage').click()" class="btn btn-primary" style="margin-bottom: 1.5rem; width: 100%;">
                🔄 Test Ảnh Khác
            </button>
            <h3>✅ Kết Quả Nhận Diện</h3>
            <div class="result-info" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem;">
                ${createInfoItem('👤', 'Tên', result.name)}
                ${createInfoItem('📛', 'Nickname', result.nickname || result.name)}
                ${createInfoItem('🎯', 'Chính xác', result.score + '%')}
                ${createInfoItem('🎂', 'Tuổi', result.age || 'N/A')}
                ${createInfoItem('⚧️', 'Giới tính', result.gender || 'N/A')}
                ${createInfoItem('⚡', 'Thời gian', processingTimeText)}
            </div>
        </div>
    `;
    
    hideInlineStatus('testStatus', 2000);
}

function displayUnknownResult(result, resultDiv) {
    showInlineStatus('testStatus', '❓ Không tìm thấy khớp', 'Khuôn mặt không có trong hệ thống', 'error');
    
    const processingTimeText = result.processing_time ? 
        `${result.processing_time.total}ms (detect: ${result.processing_time.detect}ms, match: ${result.processing_time.match}ms)` : 'N/A';
    
    resultDiv.innerHTML = `
        <div class="result-unknown">
            <button onclick="document.getElementById('testImage').click()" class="btn btn-primary" style="margin-bottom: 1.5rem; width: 100%;">
                🔄 Test Ảnh Khác
            </button>
            <h3>❓ Không Nhận Diện Được</h3>
            <p style="margin-bottom: 1rem;">${result.message}</p>
            <div class="result-info" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem;">
                ${createInfoItem('🎂', 'Tuổi', result.age || 'N/A')}
                ${createInfoItem('⚧️', 'Giới tính', result.gender || 'N/A')}
                ${createInfoItem('⚡', 'Thời gian', processingTimeText)}
            </div>
        </div>
    `;
    
    hideInlineStatus('testStatus', 2000);
}

function createInfoItem(icon, label, value) {
    return `
        <div class="info-item">
            <span class="info-icon">${icon}</span>
            <div>
                <div class="info-label">${label}</div>
                <div class="info-value">${value}</div>
            </div>
        </div>
    `;
}

function initializeImageUpload() {
    const input = document.getElementById('testImage');
    if (!input) return;
    
    input.onchange = (e) => handleImageUpload(e.target.files[0]);
}
