/**
 * Dashboard page - Person management
 */

let currentPersonId = null;
let nameInputController = null; // Controller for auto-slug input

// ==================== Initialization ====================

document.addEventListener('DOMContentLoaded', function() {
    nameInputController = initializeAutoSlugInput('nicknameInput', 'nameInput', 'namePreview');
    initializeAddPersonForm();
    initializeEditPersonForm();
    initializeImageInput();
    initializeModalHandlers();
});

// ==================== Modal Management ====================

function showAddPersonModal() {
    // Reset auto-slug state when opening modal
    if (nameInputController) {
        nameInputController.reset();
    }
    document.getElementById('addPersonModal').classList.remove('d-none');
}

function closeModal() {
    const modal = document.getElementById('addPersonModal');
    const form = document.getElementById('addPersonForm');
    modal.classList.add('d-none');
    form.reset();
    // Reset auto-slug state when closing
    if (nameInputController) {
        nameInputController.reset();
    }
}

function closeEditModal() {
    const modal = document.getElementById('editPersonModal');
    const form = document.getElementById('editPersonForm');
    modal.classList.add('d-none');
    form.reset();
}

function initializeModalHandlers() {
    window.onclick = function(event) {
        handleModalOutsideClick(event, ['addPersonModal', 'editPersonModal']);
    };
}

// ==================== Person Management ====================

function initializeAddPersonForm() {
    const form = document.getElementById('addPersonForm');
    if (!form) return;
    
    form.onsubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        
        const originalName = formData.get('name');
        
        showProgress('Đang thêm người...', 'Vui lòng chờ trong giây lát');
        
        const result = await apiRequest('/person/add', {
            method: 'POST',
            body: formData
        });
        
        if (result.success && result.data.success) {
            const finalName = result.data.name_slug;
            let msg = `Đã thêm "${finalName}"`;
            
            // Notify if name was auto-incremented due to duplicate
            if (finalName !== originalName) {
                msg += ` (tên gốc "${originalName}" đã tồn tại, tự động đổi thành "${finalName}")`;
            }
            
            showSuccess('Thành công!', msg, false);
            setTimeout(() => location.reload(), 2000);
        } else {
            showError('Lỗi', result.data?.error || result.error);
        }
    };
}

function editPerson(id, name, nickname) {
    document.getElementById('editPersonId').value = id;
    document.getElementById('editName').value = name;
    document.getElementById('editNickname').value = nickname;
    document.getElementById('editPersonModal').classList.remove('d-none');
}

function initializeEditPersonForm() {
    const form = document.getElementById('editPersonForm');
    if (!form) return;
    
    form.onsubmit = async (e) => {
        e.preventDefault();
        const personId = document.getElementById('editPersonId').value;
        const formData = new FormData(e.target);
        
        showProgress('Đang cập nhật...', 'Vui lòng chờ');
        
        const result = await apiRequest(`/person/${personId}/edit`, {
            method: 'POST',
            body: formData
        });
        
        if (result.success && result.data.success) {
            showSuccess('Thành công!', 'Đã cập nhật thông tin', false);
            setTimeout(() => location.reload(), 1500);
        } else {
            showError('Lỗi', result.data?.error || result.error);
        }
    };
}

async function deletePerson(id) {
    const card = document.getElementById('person-' + id);
    
    showProgress('Đang xóa...', 'Đang xóa người và tất cả ảnh liên quan');
    
    const result = await apiRequest(`/person/${id}/delete`, {
        method: 'POST'
    });
    
    if (result.success && result.data.success) {
        showSuccess('Đã xóa!', 'Người đã được xóa thành công');
        
        // Fade out animation
        card.style.transition = 'all 0.3s ease-out';
        card.style.opacity = '0';
        card.style.transform = 'scale(0.9)';
        
        setTimeout(() => {
            card.remove();
            hideProgress();
        }, 1500);
    } else {
        showError('Lỗi', result.data?.error || result.error);
    }
}

// ==================== Image Management ====================

function addImage(personId) {
    currentPersonId = personId;
    document.getElementById('imageInput').click();
}

function initializeImageInput() {
    const input = document.getElementById('imageInput');
    if (!input) return;
    
    input.onchange = async (e) => {
        const files = Array.from(e.target.files);
        if (files.length === 0) return;
        
        const statusIcon = document.getElementById(`upload-status-${currentPersonId}`);
        
        // Show loading indicator
        if (statusIcon) {
            statusIcon.textContent = '⏳';
            statusIcon.title = `Đang thêm ${files.length} ảnh...`;
        }
        
        let successCount = 0;
        let errorCount = 0;
        let errors = [];
        
        // Upload each file sequentially
        for (let i = 0; i < files.length; i++) {
            const formData = new FormData();
            formData.append('image', files[i]);
            
            const result = await apiRequest(`/person/${currentPersonId}/add_image`, {
                method: 'POST',
                body: formData
            });
            
            if (result.success && result.data.success) {
                successCount++;
            } else {
                errorCount++;
                errors.push(result.data?.error || result.error);
            }
            
            // Update progress
            if (statusIcon) {
                statusIcon.textContent = '⏳';
                statusIcon.title = `Đã thêm ${successCount + errorCount}/${files.length} ảnh...`;
            }
        }
        
        // Show inline result without modal
        if (statusIcon) {
            if (errorCount === 0) {
                // All success - green checkmark
                statusIcon.textContent = '✅';
                statusIcon.title = `Đã thêm ${successCount} ảnh thành công`;
                statusIcon.style.color = '#4caf50';
            } else if (successCount > 0) {
                // Partial success - warning
                statusIcon.textContent = '⚠️';
                statusIcon.title = `Thêm được ${successCount}/${files.length} ảnh`;
                statusIcon.style.color = '#ff9800';
            } else {
                // All failed - red X
                statusIcon.textContent = '❌';
                statusIcon.title = errors[0] || 'Không thể thêm ảnh';
                statusIcon.style.color = '#f44336';
            }
            
            // Clear icon after 3 seconds and reload
            setTimeout(() => {
                statusIcon.textContent = '';
                location.reload();
            }, 3000);
        } else {
            // Fallback if no status icon found
            setTimeout(() => location.reload(), 1500);
        }
        
        e.target.value = '';
    };
}

async function deleteImage(personId, imageId) {
    const result = await apiRequest(`/person/${personId}/delete_image/${imageId}`, {
        method: 'POST'
    });
    
    if (result.success && result.data.success) {
        // Reload immediately without showing success modal
        location.reload();
    } else {
        showError('Lỗi', result.data?.error || result.error);
    }
}

// ==================== Storage Management ====================

async function refreshStorage() {
    const totalEl = document.getElementById('storageTotal');
    const modelsEl = document.getElementById('storageModels');
    const dataEl = document.getElementById('storageData');
    
    if (!totalEl) return;
    
    // Show loading state
    const originalTotal = totalEl.textContent;
    const originalModels = modelsEl ? modelsEl.textContent : '';
    const originalData = dataEl ? dataEl.textContent : '';
    
    totalEl.textContent = '⏳ Calculating...';
    totalEl.style.opacity = '0.6';
    
    try {
        const result = await apiRequest('/api/storage', {
            method: 'GET'
        });
        
        if (result.success && result.data.success) {
            const data = result.data;
            
            // Update values with animation
            totalEl.textContent = data.total;
            if (modelsEl) modelsEl.textContent = data.models;
            if (dataEl) dataEl.textContent = data.data;
            
            // Flash green to indicate success
            totalEl.style.color = '#4caf50';
            totalEl.style.opacity = '1';
            
            // Reset color after 1 second
            setTimeout(() => {
                totalEl.style.color = '';
            }, 1000);
        } else {
            // Restore original values on error
            totalEl.textContent = originalTotal;
            if (modelsEl) modelsEl.textContent = originalModels;
            if (dataEl) dataEl.textContent = originalData;
            
            // Flash red to indicate error
            totalEl.style.color = '#f44336';
            totalEl.style.opacity = '1';
            
            setTimeout(() => {
                totalEl.style.color = '';
            }, 1000);
        }
    } catch (error) {
        // Restore original values on error
        totalEl.textContent = originalTotal;
        if (modelsEl) modelsEl.textContent = originalModels;
        if (dataEl) dataEl.textContent = originalData;
        
        // Flash red to indicate error
        totalEl.style.color = '#f44336';
        totalEl.style.opacity = '1';
        
        setTimeout(() => {
            totalEl.style.color = '';
        }, 1000);
    }
}

// Make functions globally accessible
window.showAddPersonModal = showAddPersonModal;
window.closeModal = closeModal;
window.closeEditModal = closeEditModal;
window.editPerson = editPerson;
window.deletePerson = deletePerson;
window.addImage = addImage;
window.deleteImage = deleteImage;
window.refreshStorage = refreshStorage;
