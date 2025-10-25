/**
 * History page
 */

// ==================== Initialization ====================

let currentHistoryId = null;
let historyNameInputController = null; // Controller for auto-slug input in modal

document.addEventListener('DOMContentLoaded', function() {
    convertTimestampsToLocal();
    drawBoundingBoxes();
});

// ==================== Bounding Box Drawing ====================

function drawBoundingBoxes() {
    const items = document.querySelectorAll('.history-item');
    
    items.forEach(item => {
        const canvas = item.querySelector('canvas[data-bbox]');
        if (!canvas) return;
        
        const img = item.querySelector('.history-thumbnail img');
        if (!img) return;
        
        const bboxData = canvas.getAttribute('data-bbox');
        const personName = canvas.getAttribute('data-person');
        
        if (!bboxData) return;
        
        let bbox;
        try {
            bbox = JSON.parse(bboxData);
        } catch (e) {
            console.error('Failed to parse bbox:', e);
            return;
        }
        
        // Use shared function
        const isUnknown = personName.toLowerCase() === 'unknown';
        drawBoundingBox(img, bbox, {
            color: isUnknown ? '#f44336' : '#4caf50',
            lineWidth: 2,
            canvas: canvas
        });
    });
}

// ==================== Timezone Conversion ====================

function convertTimestampsToLocal() {
    const timestampElements = document.querySelectorAll('.timestamp');
    
    timestampElements.forEach(element => {
        const utcTimestamp = element.getAttribute('data-timestamp');
        if (!utcTimestamp) return;
        
        try {
            // Parse timestamp (SQLite format: YYYY-MM-DD HH:MM:SS)
            const date = new Date(utcTimestamp.replace(' ', 'T') + 'Z'); // Add 'Z' for UTC
            
            // Check if date is valid
            if (isNaN(date.getTime())) {
                console.error('Invalid date:', utcTimestamp);
                return;
            }
            
            // Calculate relative time
            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMins / 60);
            const diffDays = Math.floor(diffMins / 1440);
            
            let displayText = '';
            let relativeTime = '';
            
            // Relative time text
            if (diffMins < 1) {
                relativeTime = '(vừa xong)';
            } else if (diffMins < 60) {
                relativeTime = `(${diffMins} phút trước)`;
            } else if (diffHours < 24) {
                relativeTime = `(${diffHours} giờ trước)`;
            } else if (diffDays < 7) {
                relativeTime = `(${diffDays} ngày trước)`;
            }
            
            // Display format based on time difference
            if (diffHours < 24) {
                // Within 24 hours: show only time
                const timeString = date.toLocaleString(undefined, {
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: false
                });
                displayText = timeString;
            } else {
                // More than 24 hours: show date
                const dateString = date.toLocaleString(undefined, {
                    month: '2-digit',
                    day: '2-digit',
                    hour12: false
                });
                displayText = dateString;
            }
            
            element.textContent = displayText + (relativeTime ? ' ' + relativeTime : '');
            element.title = `UTC: ${utcTimestamp}`; // Show original UTC time on hover
        } catch (error) {
            console.error('Error converting timestamp:', error);
            // Keep original timestamp on error
        }
    });
}

// ==================== History Management ====================

async function undoRecognition(historyId) {
    const element = document.getElementById('history-' + historyId);
    if (!element) return;
    
    try {
        const result = await apiRequest(`/history/${historyId}/undo`, {
            method: 'POST'
        });
        
        if (result.success) {
            // Add fade-out animation
            element.style.transition = 'all 0.3s ease-out';
            element.style.opacity = '0';
            element.style.transform = 'translateX(-20px)';
            
            // Remove element after animation and reload
            setTimeout(() => {
                location.reload();
            }, 300);
        } else {
            alert('Lỗi: ' + (result.error || 'Không thể hoàn tác'));
        }
    } catch (error) {
        alert('Lỗi kết nối: ' + error.message);
    }
}

async function deleteHistory(historyId) {
    const element = document.getElementById('history-' + historyId);
    if (!element) return;
    
    try {
        const result = await apiRequest(`/history/${historyId}/undo`, {
            method: 'POST'
        });
        
        if (result.success) {
            // Add fade-out animation
            element.style.transition = 'all 0.3s ease-out';
            element.style.opacity = '0';
            element.style.transform = 'translateX(-20px)';
            
            // Remove element after animation and reload
            setTimeout(() => {
                location.reload();
            }, 300);
        } else {
            alert('Lỗi: ' + (result.error || 'Không thể xóa'));
        }
    } catch (error) {
        alert('Lỗi kết nối: ' + error.message);
    }
}

// ==================== Add Person from History ====================

function showAddPersonModal(historyId) {
    currentHistoryId = historyId;
    const modal = document.getElementById('addPersonModal');
    modal.classList.remove('d-none');
    
    // Reset and show new person form by default
    document.getElementById('newPersonForm').classList.remove('d-none');
    document.getElementById('existingPersonForm').classList.add('d-none');
    
    // Clear input fields
    document.getElementById('newPersonName').value = '';
    document.getElementById('newPersonNickname').value = '';
    
    // Initialize auto-slug after modal is shown and elements are visible
    setTimeout(() => {
        // Cleanup old controller if exists
        if (historyNameInputController && historyNameInputController.cleanup) {
            historyNameInputController.cleanup();
        }
        // Initialize new controller
        historyNameInputController = initializeAutoSlugInput(
            'newPersonNickname',
            'newPersonName', 
            'newPersonNamePreview'
        );
    }, 100);
}

function closeAddPersonModal() {
    const modal = document.getElementById('addPersonModal');
    modal.classList.add('d-none');
    currentHistoryId = null;
    // Reset auto-slug state
    if (historyNameInputController) {
        historyNameInputController.reset();
    }
}

function showNewPersonForm() {
    document.getElementById('newPersonForm').classList.remove('d-none');
    document.getElementById('existingPersonForm').classList.add('d-none');
    
    // Toggle button styles
    const btnNewPerson = document.querySelector('button[onclick="showNewPersonForm()"]');
    const btnExistingPerson = document.querySelector('button[onclick="showExistingPersonForm()"]');
    
    if (btnNewPerson) {
        btnNewPerson.classList.add('btn-primary');
        btnNewPerson.classList.remove('btn-secondary');
    }
    if (btnExistingPerson) {
        btnExistingPerson.classList.remove('btn-primary');
        btnExistingPerson.classList.add('btn-secondary');
    }
    
    // Re-initialize auto-slug after form is shown
    setTimeout(() => {
        if (historyNameInputController && historyNameInputController.cleanup) {
            historyNameInputController.cleanup();
        }
        historyNameInputController = initializeAutoSlugInput(
            'newPersonNickname',
            'newPersonName',
            'newPersonNamePreview'
        );
    }, 50);
}

function showExistingPersonForm() {
    document.getElementById('newPersonForm').classList.add('d-none');
    document.getElementById('existingPersonForm').classList.remove('d-none');
    
    // Toggle button styles
    const btnNewPerson = document.querySelector('button[onclick="showNewPersonForm()"]');
    const btnExistingPerson = document.querySelector('button[onclick="showExistingPersonForm()"]');
    
    if (btnNewPerson) {
        btnNewPerson.classList.remove('btn-primary');
        btnNewPerson.classList.add('btn-secondary');
    }
    if (btnExistingPerson) {
        btnExistingPerson.classList.add('btn-primary');
        btnExistingPerson.classList.remove('btn-secondary');
    }
}

async function addToNewPerson() {
    const name = document.getElementById('newPersonName').value.trim();
    const nickname = document.getElementById('newPersonNickname').value.trim();
    
    if (!nickname) {
        alert('Vui lòng nhập Nickname!');
        return;
    }
    
    if (!name) {
        alert('Vui lòng nhập Tên!');
        return;
    }
    
    try {
        const result = await apiRequest(`/history/${currentHistoryId}/add_to_person`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                new_person_name: name,
                new_person_nickname: nickname
            })
        });
        
        if (result.success && result.data) {
            alert(`✅ Đã tạo người mới "${result.data.person_name}" và thêm ảnh!`);
            location.reload();
        } else {
            alert('❌ Lỗi: ' + (result.data?.error || result.error || 'Không thể thêm'));
        }
    } catch (error) {
        alert('❌ Lỗi kết nối: ' + error.message);
    }
}

async function addToExistingPerson() {
    const personId = document.getElementById('existingPersonSelect').value;
    
    if (!personId) {
        alert('Vui lòng chọn người!');
        return;
    }
    
    try {
        const result = await apiRequest(`/history/${currentHistoryId}/add_to_person`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                person_id: parseInt(personId)
            })
        });
        
        if (result.success && result.data) {
            alert(`✅ Đã thêm ảnh vào "${result.data.person_name}"!`);
            location.reload();
        } else {
            alert('❌ Lỗi: ' + (result.data?.error || result.error || 'Không thể thêm'));
        }
    } catch (error) {
        alert('❌ Lỗi kết nối: ' + error.message);
    }
}

// ==================== Image Preview ====================
// Note: showImagePreview and closeImagePreview are now in common.js with ESC key and memory cleanup

// Export for onclick handlers
window.undoRecognition = undoRecognition;
window.deleteHistory = deleteHistory;
window.showAddPersonModal = showAddPersonModal;
window.closeAddPersonModal = closeAddPersonModal;
window.showNewPersonForm = showNewPersonForm;
window.showExistingPersonForm = showExistingPersonForm;
window.addToNewPerson = addToNewPerson;
window.addToExistingPerson = addToExistingPerson;

