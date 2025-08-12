/**
 * 聊天功能模塊
 * 處理智能問答和對話記憶功能
 */

class ChatManager {
    constructor() {
        this.chatEnabled = false;
        this.memoryEnabled = true;
        this.chatHistory = [];
        this.currentSessionId = null;
        this.memoryStatus = {
            cached: false,
            count: 0,
            hasHistory: false,
            ready: false
        };
        this.elements = {};
    }

    /**
     * 初始化聊天功能
     */
    init() {
        this.cacheElements();
        this.bindEvents();
        this.updateMemoryIndicator();
        console.log('聊天系統已初始化（支持對話記憶）');
    }

    /**
     * 快取DOM元素
     */
    cacheElements() {
        this.elements = {
            chatPanel: document.getElementById('chatPanel'),
            chatToggleBtn: document.getElementById('chatToggleBtn'),
            chatCloseBtn: document.getElementById('chatCloseBtn'),
            chatMessages: document.getElementById('chatMessages'),
            chatInput: document.getElementById('chatInput'),
            chatSendBtn: document.getElementById('chatSendBtn'),
            chatStatus: document.getElementById('chatStatus'),
            chatTyping: document.getElementById('chatTyping'),
            mainContent: document.querySelector('.main-content'),
            
            // 記憶功能元素
            memoryToggleBtn: document.getElementById('memoryToggleBtn'),
            chatHistoryBtn: document.getElementById('chatHistoryBtn'),
            clearMemoryBtn: document.getElementById('clearMemoryBtn'),
            useMemoryCheckbox: document.getElementById('useMemoryCheckbox'),
            memoryIndicator: document.getElementById('memoryIndicator'),
            memoryStatusPanel: document.getElementById('memoryStatusPanel'),
            memoryStats: document.getElementById('memoryStats'),
            memoryStatus: document.getElementById('memoryStatus')
        };
    }

    /**
     * 綁定事件
     */
    bindEvents() {
        // 聊天基本功能
        if (this.elements.chatToggleBtn) {
            this.elements.chatToggleBtn.addEventListener('click', () => this.toggleChat());
        }
        
        if (this.elements.chatCloseBtn) {
            this.elements.chatCloseBtn.addEventListener('click', () => this.closeChat());
        }
        
        if (this.elements.chatSendBtn) {
            this.elements.chatSendBtn.addEventListener('click', () => this.sendChatMessage());
        }
        
        if (this.elements.chatInput) {
            this.elements.chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendChatMessage();
                }
            });
        }

        // 記憶功能
        if (this.elements.memoryToggleBtn) {
            this.elements.memoryToggleBtn.addEventListener('click', () => this.toggleMemoryMode());
        }
        
        if (this.elements.chatHistoryBtn) {
            this.elements.chatHistoryBtn.addEventListener('click', () => this.showChatHistory());
        }
        
        if (this.elements.clearMemoryBtn) {
            this.elements.clearMemoryBtn.addEventListener('click', () => this.clearChatMemory());
        }
        
        if (this.elements.useMemoryCheckbox) {
            this.elements.useMemoryCheckbox.addEventListener('change', (e) => {
                this.memoryEnabled = e.target.checked;
                this.updateMemoryIndicator();
            });
        }
    }

    /**
     * 設置會話ID
     * @param {string} sessionId - 會話ID
     */
    setSessionId(sessionId) {
        this.currentSessionId = sessionId;
        console.log('聊天系統會話ID已設置:', sessionId);
    }

    /**
     * 切換聊天面板
     */
    toggleChat() {
        const isOpen = this.elements.chatPanel?.classList.contains('open');
        if (isOpen) {
            this.closeChat();
        } else {
            this.openChat();
        }
    }

    /**
     * 打開聊天面板
     */
    openChat() {
        if (this.elements.chatPanel) {
            this.elements.chatPanel.classList.add('open');
        }
        if (this.elements.mainContent) {
            this.elements.mainContent.classList.add('chat-open');
        }
        if (this.elements.chatToggleBtn) {
            this.elements.chatToggleBtn.style.display = 'none';
        }
        
        // 如果聊天未啟用但有搜索結果，啟用聊天
        if (!this.chatEnabled && this.hasSearchResults()) {
            this.enableChat();
        }
    }

    /**
     * 關閉聊天面板
     */
    closeChat() {
        if (this.elements.chatPanel) {
            this.elements.chatPanel.classList.remove('open');
        }
        if (this.elements.mainContent) {
            this.elements.mainContent.classList.remove('chat-open');
        }
        if (this.elements.chatToggleBtn) {
            this.elements.chatToggleBtn.style.display = 'flex';
        }
    }

    /**
     * 檢查是否有搜索結果
     * @returns {boolean} 是否有搜索結果
     */
    hasSearchResults() {
        // 這裡需要與搜索管理器或主應用協調
        return searchManager?.hasSearchResults() || false;
    }

    /**
     * 啟用聊天功能
     */
    enableChat() {
        this.chatEnabled = true;
        
        if (this.elements.chatInput) {
            this.elements.chatInput.disabled = false;
        }
        if (this.elements.chatSendBtn) {
            this.elements.chatSendBtn.disabled = false;
        }
        if (this.elements.chatStatus) {
            this.elements.chatStatus.textContent = '已就緒，可以開始問答！';
            this.elements.chatStatus.style.background = '#d4edda';
            this.elements.chatStatus.style.color = '#155724';
        }
        
        // 更新記憶狀態
        this.updateMemoryStatus();
        
        console.log('聊天功能已啟用（支持對話記憶）');
    }

    /**
     * 發送聊天消息
     */
    async sendChatMessage() {
        const message = this.elements.chatInput?.value.trim();
        if (!message || !this.chatEnabled) return;

        // 添加用戶消息
        this.addChatMessage('user', message, this.memoryEnabled);
        if (this.elements.chatInput) {
            this.elements.chatInput.value = '';
        }
        
        // 顯示輸入中
        this.showTyping();
        
        try {
            const response = await this.callQwenAPI(message, this.memoryEnabled);
            this.hideTyping();
            this.addChatMessage('assistant', response.answer, this.memoryEnabled, response);
            
            // 更新記憶狀態
            await this.updateMemoryStatus();
            
        } catch (error) {
            this.hideTyping();
            this.addChatMessage('assistant', '抱歉，回答時發生錯誤：' + error.message, false);
            console.error('聊天API錯誤:', error);
        }
    }

    /**
     * 調用QWEN API
     * @param {string} userMessage - 用戶消息
     * @param {boolean} useMemory - 是否使用記憶
     * @returns {Promise<Object>} API響應
     */
    async callQwenAPI(userMessage, useMemory = true) {
        if (!this.currentSessionId) {
            throw new Error('會話ID未設置');
        }

        try {
            let response;
            if (useMemory) {
                response = await apiService.askWithMemory(this.currentSessionId, userMessage);
            } else {
                response = await apiService.askSimpleQuestion(this.currentSessionId, userMessage);
            }

            if (response.success) {
                return response;
            } else {
                throw new Error(response.error || 'API回應錯誤');
            }
        } catch (error) {
            console.error('QWEN API調用失敗:', error);
            throw error;
        }
    }

    /**
     * 添加聊天消息
     * @param {string} type - 消息類型 (user/assistant/system)
     * @param {string} content - 消息內容
     * @param {boolean} memoryMode - 記憶模式
     * @param {Object} metadata - 元數據
     */
    addChatMessage(type, content, memoryMode, metadata = null) {
        if (!this.elements.chatMessages) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${type} ${memoryMode ? 'memory-enabled' : 'memory-disabled'}`;
        
        const now = new Date();
        const timeStr = now.toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' });
        
        let metaInfo = '';
        if (metadata && type === 'assistant') {
            const contextInfo = metadata.context_info || {};
            metaInfo = `
                <div class="message-meta">
                    記憶模式: ${contextInfo.memory_enabled ? '開啟' : '關閉'} | 
                    使用歷史: ${contextInfo.conversation_history_used || 0} 輪 | 
                    執行時間: ${(metadata.execution_time || 0).toFixed(2)}s
                </div>
            `;
        }
        
        messageDiv.innerHTML = `
            <div class="message-content">${Utils.escapeHtml(content)}</div>
            <div class="message-time">${timeStr}</div>
            ${metaInfo}
        `;
        
        this.elements.chatMessages.appendChild(messageDiv);
        this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
        
        // 保存到聊天歷史
        this.chatHistory.push({
            type: type,
            content: content,
            memoryMode: memoryMode,
            timestamp: now.toISOString(),
            metadata: metadata
        });
    }

    /**
     * 顯示輸入中狀態
     */
    showTyping() {
        if (this.elements.chatTyping) {
            this.elements.chatTyping.classList.add('show');
        }
        if (this.elements.chatMessages) {
            this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
        }
    }

    /**
     * 隱藏輸入中狀態
     */
    hideTyping() {
        if (this.elements.chatTyping) {
            this.elements.chatTyping.classList.remove('show');
        }
    }

    /**
     * 切換記憶模式
     */
    toggleMemoryMode() {
        this.memoryEnabled = !this.memoryEnabled;
        if (this.elements.useMemoryCheckbox) {
            this.elements.useMemoryCheckbox.checked = this.memoryEnabled;
        }
        this.updateMemoryIndicator();
        
        this.addChatMessage('system', 
            `對話記憶已${this.memoryEnabled ? '開啟' : '關閉'}。` +
            `${this.memoryEnabled ? 'AI將記住我們之前的對話內容。' : 'AI將不會記住之前的對話。'}`, 
            false
        );
    }

    /**
     * 更新記憶指示器
     */
    updateMemoryIndicator() {
        if (!this.elements.memoryIndicator) return;
        
        const indicator = this.elements.memoryIndicator;
        const status = this.elements.memoryStatus;
        
        if (this.memoryEnabled) {
            indicator.className = 'memory-indicator active';
            indicator.style.display = 'flex';
            if (status) status.textContent = '記憶模式';
        } else {
            indicator.className = 'memory-indicator inactive';
            indicator.style.display = 'flex';
            if (status) status.textContent = '簡單模式';
        }
    }

    /**
     * 更新記憶狀態
     */
    async updateMemoryStatus() {
        if (!this.currentSessionId) return;
        
        try {
            const response = await apiService.getMemoryStatus(this.currentSessionId);
            if (response.success) {
                this.memoryStatus = response.memory_status;
                this.updateMemoryStatusDisplay();
            }
        } catch (error) {
            console.error('更新記憶狀態失敗:', error);
        }
    }

    /**
     * 更新記憶狀態顯示
     */
    updateMemoryStatusDisplay() {
        if (!this.elements.memoryStats) return;
        
        const status = this.memoryStatus;
        const statsText = `記憶快取: ${status.memory_count || 0} 輪 | ` +
                         `歷史記錄: ${status.has_db_history ? '有' : '無'} | ` +
                         `檢索結果: ${status.has_search_cache ? '可用' : '無'}`;
        
        this.elements.memoryStats.textContent = statsText;
        
        // 顯示/隱藏狀態面板
        if (this.elements.memoryStatusPanel) {
            this.elements.memoryStatusPanel.style.display = 
                (status.memory_count > 0 || status.has_db_history) ? 'block' : 'none';
        }
    }

    /**
     * 顯示對話歷史
     */
    async showChatHistory() {
        if (!this.currentSessionId) {
            uiManager.showError('沒有當前會話ID');
            return;
        }
        
        try {
            const response = await apiService.getChatHistory(this.currentSessionId, 20);
            
            if (response.success && response.history.length > 0) {
                let historyHtml = '<div style="max-height: 60vh; overflow-y: auto; padding: 1rem;">';
                
                response.history.forEach((item, index) => {
                    const time = new Date(item.created_at).toLocaleString('zh-TW');
                    historyHtml += `
                        <div class="history-item">
                            <div class="history-time">${time}</div>
                            <div class="history-question">問: ${Utils.escapeHtml(item.question)}</div>
                            <div class="history-answer">答: ${Utils.escapeHtml(item.answer.substring(0, 200))}${item.answer.length > 200 ? '...' : ''}</div>
                        </div>
                    `;
                });
                
                historyHtml += '</div>';
                
                // 創建對話歷史模態框
                uiManager.showModal('對話歷史', historyHtml);
            } else {
                uiManager.showWarning('暫無對話歷史');
            }
        } catch (error) {
            console.error('獲取對話歷史失敗:', error);
            uiManager.showError('獲取對話歷史失敗');
        }
    }

    /**
     * 清除聊天記憶
     */
    async clearChatMemory() {
        if (!this.currentSessionId) {
            uiManager.showError('沒有當前會話ID');
            return;
        }
        
        const confirmed = await this.showConfirmDialog(
            '確定要清除對話記憶嗎？這將清除AI對之前對話的記憶，但不會刪除歷史記錄。'
        );
        
        if (!confirmed) return;
        
        try {
            const response = await apiService.clearChatMemory(this.currentSessionId);
            
            if (response.success) {
                this.addChatMessage('system', '對話記憶已清除。AI將不再記住之前的對話內容。', false);
                await this.updateMemoryStatus();
                uiManager.showSuccess('對話記憶已清除');
            } else {
                uiManager.showError('清除記憶失敗');
            }
        } catch (error) {
            console.error('清除記憶失敗:', error);
            uiManager.showError('清除記憶失敗');
        }
    }

    /**
     * 顯示確認對話框
     * @param {string} message - 確認消息
     * @returns {Promise<boolean>} 用戶確認結果
     */
    showConfirmDialog(message) {
        return new Promise((resolve) => {
            uiManager.showConfirm(
                message,
                () => resolve(true),
                () => resolve(false)
            );
        });
    }

    /**
     * 重置聊天狀態
     */
    reset() {
        this.chatEnabled = false;
        this.chatHistory = [];
        this.memoryStatus = {
            cached: false,
            count: 0,
            hasHistory: false,
            ready: false
        };
        
        // 重置UI狀態
        if (this.elements.chatInput) {
            this.elements.chatInput.disabled = true;
            this.elements.chatInput.value = '';
        }
        if (this.elements.chatSendBtn) {
            this.elements.chatSendBtn.disabled = true;
        }
        if (this.elements.chatStatus) {
            this.elements.chatStatus.textContent = '等待檢索結果...';
            this.elements.chatStatus.style.background = '';
            this.elements.chatStatus.style.color = '';
        }
        
        // 清空聊天消息（保留歡迎消息）
        if (this.elements.chatMessages) {
            const welcomeMessage = this.elements.chatMessages.querySelector('.chat-message.assistant');
            this.elements.chatMessages.innerHTML = '';
            if (welcomeMessage) {
                this.elements.chatMessages.appendChild(welcomeMessage);
            }
        }
        
        this.updateMemoryStatusDisplay();
    }

    /**
     * 添加系統消息
     * @param {string} message - 系統消息
     */
    addSystemMessage(message) {
        this.addChatMessage('system', message, false);
    }

    /**
     * 設置聊天狀態
     * @param {string} status - 狀態文本
     * @param {string} type - 狀態類型 (success/warning/error)
     */
    setChatStatus(status, type = 'info') {
        if (!this.elements.chatStatus) return;
        
        this.elements.chatStatus.textContent = status;
        
        // 設置狀態樣式
        const styles = {
            success: { background: '#d4edda', color: '#155724' },
            warning: { background: '#fff3cd', color: '#856404' },
            error: { background: '#f8d7da', color: '#721c24' },
            info: { background: '', color: '' }
        };
        
        const style = styles[type] || styles.info;
        this.elements.chatStatus.style.background = style.background;
        this.elements.chatStatus.style.color = style.color;
    }

    /**
     * 檢查聊天是否已啟用
     * @returns {boolean} 聊天是否已啟用
     */
    isEnabled() {
        return this.chatEnabled;
    }

    /**
     * 檢查記憶模式是否啟用
     * @returns {boolean} 記憶模式是否啟用
     */
    isMemoryEnabled() {
        return this.memoryEnabled;
    }

    /**
     * 獲取聊天歷史
     * @returns {Array} 聊天歷史
     */
    getChatHistory() {
        return [...this.chatHistory];
    }

    /**
     * 獲取記憶狀態
     * @returns {Object} 記憶狀態
     */
    getMemoryStatus() {
        return { ...this.memoryStatus };
    }

    /**
     * 設置記憶模式
     * @param {boolean} enabled - 是否啟用記憶模式
     */
    setMemoryMode(enabled) {
        this.memoryEnabled = enabled;
        if (this.elements.useMemoryCheckbox) {
            this.elements.useMemoryCheckbox.checked = enabled;
        }
        this.updateMemoryIndicator();
    }
}

// 創建全局聊天管理器實例
const chatManager = new ChatManager();