/**
 * Settings page
 */

// ==================== Initialization ====================

document.addEventListener('DOMContentLoaded', function() {
    initializeMQTTForm();
    initializeTestConnectionButton();
});

// ==================== Model Management ====================

function initializeMQTTForm() {
    const form = document.getElementById('mqttForm');
    if (!form) return;
    
    form.onsubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = {};
        formData.forEach((value, key) => {
            data[key] = value;
        });
        
        try {
            showProgress('⚙️ Đang lưu cấu hình...', 'Updating settings...');
            
            const result = await apiRequest('/settings/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            if (result.success) {
                showSuccess('✅ Thành công', 'Cài đặt đã được lưu');
            } else {
                showError('❌ Lỗi', result.error || 'Không thể lưu cấu hình');
            }
        } catch (error) {
            showError('❌ Lỗi kết nối', error.message);
        }
    };
}

function initializeTestConnectionButton() {
    const btn = document.getElementById('testMQTT');
    if (btn) {
        btn.onclick = testMqtt;
    }
}

async function testMqtt() {
    const formData = new FormData(document.getElementById('mqttForm'));
    const data = {};
    formData.forEach((value, key) => {
        data[key] = value;
    });
    
    const statusIcon = document.getElementById('mqttTestStatus');
    const statusMessage = document.getElementById('mqttTestMessage');
    
    // Show loading
    statusIcon.textContent = '⏳';
    statusMessage.textContent = 'Đang kiểm tra...';
    statusMessage.style.color = '#666';
    
    try {
        const result = await apiRequest('/settings/test_mqtt', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (result.success) {
            // Show success icon
            statusIcon.textContent = '✅';
            statusMessage.textContent = 'Kết nối thành công!';
            statusMessage.style.color = '#4caf50';
            
            // Clear after 3 seconds
            setTimeout(() => {
                statusIcon.textContent = '';
                statusMessage.textContent = '';
            }, 3000);
        } else {
            // Show error icon
            statusIcon.textContent = '❌';
            statusMessage.textContent = result.error || 'Không thể kết nối MQTT';
            statusMessage.style.color = '#f44336';
            
            // Clear after 5 seconds (longer for errors)
            setTimeout(() => {
                statusIcon.textContent = '';
                statusMessage.textContent = '';
            }, 5000);
        }
    } catch (error) {
        // Show error icon
        statusIcon.textContent = '❌';
        statusMessage.textContent = 'Lỗi: ' + error.message;
        statusMessage.style.color = '#f44336';
        
        // Clear after 5 seconds
        setTimeout(() => {
            statusIcon.textContent = '';
            statusMessage.textContent = '';
        }, 5000);
    }
}

// ==================== Model Management ====================

async function changeModel(modelName) {
    try {
        // Step 1: Load model
        showInlineStatus('modelStatus', '🔄 Đang tải model...', 'Đang load model mới, vui lòng chờ...');
        
        const result = await apiRequest('/settings/change_model', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ model_name: modelName })
        });
        
        if (result.success && result.data.success) {
            // Step 2: Retrain with progress
            showInlineStatus('modelStatus', '✨ Model đã load!', 'Đang chuẩn bị train lại toàn bộ embedding...');
            await retrainAll(false); // Show progress (not silent)
            
            // Step 3: Success
            showInlineStatus('modelStatus', '✅ Hoàn tất!', 'Đã đổi model và train lại thành công. Trang sẽ tự động reload...', 'success');
            setTimeout(() => location.reload(), 2000);
        } else {
            showInlineStatus('modelStatus', '❌ Lỗi', result.data?.error || result.error || 'Không thể đổi model', 'error');
            hideInlineStatus('modelStatus', 3000);
        }
    } catch (error) {
        showInlineStatus('modelStatus', '❌ Lỗi', error.message, 'error');
        hideInlineStatus('modelStatus', 3000);
    }
}

async function retrainAll(silent = false) {
    try {
        if (!silent) {
            showInlineStatus('modelStatus', '🔄 Đang train lại...', 'Đang đếm số lượng ảnh...');
            // Show progress bar
            const progressBarContainer = document.getElementById('progressBarContainer');
            const progressBar = document.getElementById('progressBar');
            if (progressBarContainer) progressBarContainer.style.display = 'block';
            if (progressBar) progressBar.style.width = '0%';
        }
        
        // Start retrain in background
        const retrainPromise = apiRequest('/settings/retrain', {
            method: 'POST'
        });
        
        // Poll for progress
        if (!silent) {
            let progressInterval = null;
            
            progressInterval = setInterval(async () => {
                try {
                    const progressResult = await apiRequest('/api/retrain-progress', {
                        method: 'GET'
                    });
                    
                    if (progressResult.success && progressResult.data) {
                        const data = progressResult.data;
                        
                        if (data.is_running) {
                            const percentage = data.total > 0 ? Math.round((data.current / data.total) * 100) : 0;
                            showInlineStatus('modelStatus',
                                `🔄 Đang train... ${percentage}%`, 
                                `${data.current}/${data.total} ảnh - ${data.current_person}`
                            );
                            
                            // Update progress bar
                            const progressBar = document.getElementById('progressBar');
                            if (progressBar) {
                                progressBar.style.width = percentage + '%';
                            }
                        } else {
                            // Stop polling when not running
                            if (progressInterval) {
                                clearInterval(progressInterval);
                                progressInterval = null;
                            }
                        }
                    } else {
                        // Stop polling on error
                        if (progressInterval) {
                            clearInterval(progressInterval);
                            progressInterval = null;
                        }
                    }
                } catch (error) {
                    console.error('Progress poll error:', error);
                    // Stop polling on exception
                    if (progressInterval) {
                        clearInterval(progressInterval);
                        progressInterval = null;
                    }
                }
            }, 500); // Poll every 500ms
            
            // Wait for retrain to complete
            const result = await retrainPromise;
            
            // Ensure interval is cleared
            if (progressInterval) {
                clearInterval(progressInterval);
                progressInterval = null;
            }
            
            // Hide progress bar
            const progressBarContainer = document.getElementById('progressBarContainer');
            if (progressBarContainer) progressBarContainer.style.display = 'none';
            
            if (result.success && result.data.success) {
                showInlineStatus('modelStatus', '✅ Hoàn tất!', `Train lại thành công ${result.data.retrained_count} ảnh!`, 'success');
                hideInlineStatus('modelStatus', 3000);
                return result.data;
            } else {
                showInlineStatus('modelStatus', '❌ Lỗi', result.data?.error || result.error, 'error');
                hideInlineStatus('modelStatus', 3000);
                throw new Error(result.data?.error || result.error);
            }
        } else {
            // Silent mode - just wait for completion
            const result = await retrainPromise;
            return result.data;
        }
    } catch (error) {
        if (!silent) {
            // Hide progress bar on error
            const progressBarContainer = document.getElementById('progressBarContainer');
            if (progressBarContainer) progressBarContainer.style.display = 'none';
            
            showInlineStatus('modelStatus', '❌ Lỗi', error.message, 'error');
            hideInlineStatus('modelStatus', 3000);
        }
        throw error;
    }
}

// ==================== Data Management ====================

function showSettingStatus(statusId, message, type = 'success', autoHide = true) {
    const statusDiv = document.getElementById(statusId);
    if (!statusDiv) return;
    
    statusDiv.textContent = message;
    statusDiv.className = `setting-status ${type}`;
    statusDiv.classList.remove('d-none');
    
    if (autoHide) {
        setTimeout(() => {
            statusDiv.classList.add('d-none');
        }, 3000);
    }
}

function adjustMaxImages(delta) {
    const input = document.getElementById('maxImagesInput');
    const currentValue = parseInt(input.value) || 10;
    const newValue = Math.max(1, Math.min(100, currentValue + delta));
    input.value = newValue;
}

async function applyMaxImages() {
    const maxImages = parseInt(document.getElementById('maxImagesInput').value);
    
    if (isNaN(maxImages) || maxImages < 1 || maxImages > 100) {
        showSettingStatus('maxImagesStatus', '❌ Số ảnh phải từ 1 đến 100', 'error');
        return;
    }
    
    try {
        const result = await apiRequest('/settings/max_images', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ max_images: maxImages })
        });
        
        if (result.success && result.data) {
            const deletedCount = result.data.deleted_count || 0;
            const oldMax = result.data.old_max;
            const newMax = result.data.max_images;
            
            if (deletedCount > 0) {
                showSettingStatus('maxImagesStatus', 
                    `✅ Đã cập nhật! Số ảnh tối đa: ${newMax} ảnh/người. Đã xóa ${deletedCount} ảnh cũ nhất (${oldMax}→${newMax})`, 
                    'warning', false);
                setTimeout(() => {
                    document.getElementById('maxImagesStatus').classList.add('d-none');
                }, 5000);
            } else {
                showSettingStatus('maxImagesStatus', 
                    `✅ Đã cập nhật! Số ảnh tối đa: ${newMax} ảnh/người`, 
                    'success');
            }
        } else {
            showSettingStatus('maxImagesStatus', 
                `❌ Lỗi: ${result.data?.error || result.error || 'Không thể cập nhật'}`, 
                'error');
        }
    } catch (error) {
        showSettingStatus('maxImagesStatus', 
            `❌ Lỗi kết nối: ${error.message}`, 
            'error');
    }
}

async function toggleAutoTrain(enabled) {
    try {
        const result = await apiRequest('/settings/toggle_auto_train', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: enabled })
        });
        
        if (result.success) {
            showSettingStatus('autoTrainStatus', 
                `✅ Auto-Train đã ${enabled ? 'BẬT' : 'TẮT'}`, 
                'success');
        } else {
            showSettingStatus('autoTrainStatus', 
                `❌ Lỗi: ${result.error || 'Không thể cập nhật'}`, 
                'error');
            // Revert checkbox
            document.getElementById('autoTrainToggle').checked = !enabled;
        }
    } catch (error) {
        showSettingStatus('autoTrainStatus', 
            `❌ Lỗi kết nối: ${error.message}`, 
            'error');
        // Revert checkbox
        document.getElementById('autoTrainToggle').checked = !enabled;
    }
}

async function setVotingTopK(topK) {
    try {
        // Update active class immediately for better UX
        document.querySelectorAll('.radio-option').forEach(option => {
            option.classList.remove('active');
        });
        const activeOption = document.querySelector(`input[name="votingTopK"][value="${topK}"]`).closest('.radio-option');
        if (activeOption) {
            activeOption.classList.add('active');
        }
        
        const result = await apiRequest('/settings/voting_top_k', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ voting_top_k: topK })
        });
        
        if (result.success) {
            showSettingStatus('votingStatus', 
                `✅ Đã cập nhật Voting Top-K: ${topK} ảnh`, 
                'success');
        } else {
            showSettingStatus('votingStatus', 
                `❌ Lỗi: ${result.error || 'Không thể cập nhật'}`, 
                'error');
        }
    } catch (error) {
        showSettingStatus('votingStatus', 
            `❌ Lỗi: ${error.message}`, 
            'error');
    }
}

async function clearHistory() {
    if (!confirm('⚠️ Bạn có chắc muốn xóa toàn bộ lịch sử nhận diện?')) {
        return;
    }
    
    try {
        showProgress('🗑️ Đang xóa lịch sử...', 'Đang xóa tất cả bản ghi lịch sử');
        
        const result = await apiRequest('/settings/clear_history', {
            method: 'POST'
        });
        
        if (result.success) {
            showSuccess('✅ Đã xóa!', 'Lịch sử đã được xóa hoàn toàn');
        } else {
            showError('❌ Lỗi', result.error || 'Không thể xóa lịch sử');
        }
    } catch (error) {
        showError('❌ Lỗi kết nối', error.message);
    }
}

async function clearAll() {
    if (!confirm('⚠️ CẢNH BÁO: Bạn có chắc muốn xóa TOÀN BỘ dữ liệu?\n\nHành động này sẽ xóa tất cả người dùng, ảnh và lịch sử. Không thể hoàn tác!')) {
        return;
    }
    
    try {
        showProgress('⚠️ Đang xóa toàn bộ...', 'Đang xóa tất cả người dùng, ảnh và lịch sử. Vui lòng chờ...');
        
        const result = await apiRequest('/settings/clear_all', {
            method: 'POST'
        });
        
        if (result.success) {
            showSuccess('✅ Hoàn tất!', 'Đã xóa toàn bộ dữ liệu. Đang reload...', false);
            setTimeout(() => location.reload(), 2000);
        } else {
            showError('❌ Lỗi', result.error || 'Không thể xóa dữ liệu');
        }
    } catch (error) {
        showError('❌ Lỗi kết nối', error.message);
    }
}

// Export for onclick handlers
window.toggleAutoTrain = toggleAutoTrain;
window.adjustMaxImages = adjustMaxImages;
window.applyMaxImages = applyMaxImages;
window.setVotingTopK = setVotingTopK;
window.changeModel = changeModel;
window.retrainAll = retrainAll;
window.testMqtt = testMqtt;
window.clearHistory = clearHistory;
window.clearAll = clearAll;

