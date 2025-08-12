/**
 * UI功能模塊
 * 處理所有用戶界面相關的操作
 */

class UIManager {
    constructor() {
        this.progressIntervals = {};
        this.messageTimeout = null;
    }

    /**
     * 快取DOM元素
     */
    cacheElements() {
        return {
            // API設定
            apiBaseUrl: document.getElementById('apiBaseUrl'),
            testApiBtn: document.getElementById('testApiBtn'),
            gpssApiKey: document.getElementById('gpssApiKey'),
            testGpssBtn: document.getElementById('testGpssBtn'),
            
            // 狀態指示器
            apiStatus: document.getElementById('apiStatus'),
            gpssStatus: document.getElementById('gpssStatus'),
            qwenStatus: document.getElementById('qwenStatus'),
            
            // 專利查詢
            patentLookupInput: document.getElementById('patentLookupInput'),
            patentLookupBtn: document.getElementById('patentLookupBtn'),
            
            // 分頁和內容
            tabContainer: document.getElementById('tabContainer'),
            techDescription: document.getElementById('techDescription'),
            
            // 關鍵字流程
            generateKeywordsBtn: document.getElementById('generateKeywordsBtn'),
            keywordSelection: document.getElementById('keyword-selection'),
            availableKeywords: document.getElementById('available-keywords'),
            searchConditions: document.getElementById('search-conditions'),
            
            // 進度和載入
            loadingTech: document.getElementById('loading-tech'),
            progressFill: document.getElementById('progress-fill'),
            progressText: document.getElementById('progress-text'),
            loadingText: document.getElementById('loading-text'),
            
            // 結果顯示
            keywordsResult: document.getElementById('keywords-result'),
            finalKeywords: document.getElementById('final-keywords'),
            techSearchResults: document.getElementById('tech-search-results'),
            techPatentList: document.getElementById('tech-patent-list'),
            exportExcelBtn: document.getElementById('exportExcelBtn'),
            
            // 條件搜索
            startConditionSearchBtn: document.getElementById('startConditionSearchBtn'),
            loadingCondition: document.getElementById('loading-condition'),
            conditionSearchResults: document.getElementById('condition-search-results'),
            conditionPatentList: document.getElementById('condition-patent-list'),
            exportConditionExcelBtn: document.getElementById('exportConditionExcelBtn'),
            
            // Excel分析
            uploadArea: document.getElementById('uploadArea'),
            excelFileInput: document.getElementById('excelFileInput'),
            selectFileBtn: document.getElementById('selectFileBtn'),
            fileInfo: document.getElementById('fileInfo'),
            analyzeExcelBtn: document.getElementById('analyzeExcelBtn'),
            clearFileBtn: document.getElementById('clearFileBtn'),
            loadingExcel: document.getElementById('loading-excel'),
            excelAnalysisResults: document.getElementById('excel-analysis-results'),
            excelPatentList: document.getElementById('excel-patent-list'),
            exportAnalysisBtn: document.getElementById('exportAnalysisBtn'),
            
            // 聊天相關
            chatPanel: document.getElementById('chatPanel'),
            chatToggleBtn: document.getElementById('chatToggleBtn'),
            chatCloseBtn: document.getElementById('chatCloseBtn'),
            chatMessages: document.getElementById('chatMessages'),
            chatInput: document.getElementById('chatInput'),
            chatSendBtn: document.getElementById('chatSendBtn'),
            chatStatus: document.getElementById('chatStatus'),
            chatTyping: document.getElementById('chatTyping'),
            mainContent: document.querySelector('.main-content'),
            
            // 記憶功能
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
     * 顯示/隱藏分頁
     * @param {string} tabId - 分頁ID
     */
    showTab(tabId) {
        // 隱藏所有分頁內容
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        // 移除所有分頁按鈕的active狀態
        document.querySelectorAll('.tab').forEach(tab => {
            tab.classList.remove('active');
        });
        
        // 顯示目標分頁
        const targetTab = document.getElementById(tabId);
        if (targetTab) {
            targetTab.classList.add('active');
        }
        
        // 激活對應的分頁按鈕
        const activeTabBtn = document.querySelector(`[data-tab="${tabId}"]`);
        if (activeTabBtn) {
            activeTabBtn.classList.add('active');
        }
    }

    /**
     * 更新狀態指示器
     * @param {string} elementId - 元素ID
     * @param {string} status - 狀態類型
     * @param {string} message - 狀態消息
     */
    updateStatus(elementId, status, message) {
        const element = document.getElementById(elementId);
        if (!element) return;

        element.className = `status-indicator status-${status}`;
        const icons = { 
            success: '✓', 
            error: '✗', 
            warning: '⚠', 
            testing: '⟳' 
        };
        const icon = icons[status] || '?';
        element.innerHTML = `<span>${icon}</span> ${message}`;
    }

    /**
     * 顯示成功消息
     * @param {string} message - 消息內容
     */
    showSuccess(message) {
        this.showMessage(message, 'success');
    }

    /**
     * 顯示錯誤消息
     * @param {string} message - 消息內容
     */
    showError(message) {
        this.showMessage(message, 'error');
    }

    /**
     * 顯示警告消息
     * @param {string} message - 消息內容
     */
    showWarning(message) {
        this.showMessage(message, 'warning');
    }

    /**
     * 顯示通用消息
     * @param {string} message - 消息內容
     * @param {string} type - 消息類型
     */
    showMessage(message, type) {
        // 移除現有消息
        const existing = document.querySelector('.temp-message');
        if (existing) existing.remove();

        // 清除之前的超時
        if (this.messageTimeout) {
            clearTimeout(this.messageTimeout);
        }

        // 創建新消息
        const div = document.createElement('div');
        div.className = `${type}-message temp-message`;
        const icon = type === 'error' ? '✗' : type === 'warning' ? '⚠' : '✓';
        const title = type === 'error' ? '錯誤' : type === 'warning' ? '警告' : '成功';
        div.innerHTML = `<strong>${icon} ${title}：</strong> ${message}`;
        
        // 插入到頁面
        const header = document.querySelector('.header');
        if (header) {
            header.after(div);
        }
        
        // 自動移除
        this.messageTimeout = setTimeout(() => {
            if (div.parentNode) {
                div.parentNode.removeChild(div);
            }
        }, 5000);
    }

    /**
     * 開始進度動畫
     * @param {string} progressElementId - 進度條元素ID
     * @param {string} textElementId - 文本元素ID
     * @param {number} duration - 動畫持續時間
     */
    startProgressAnimation(progressElementId, textElementId, duration = 30000) {
        const progressElement = document.getElementById(progressElementId);
        const textElement = document.getElementById(textElementId);
        
        if (!progressElement || !textElement) return;
        
        // 清除之前的動畫
        if (this.progressIntervals[progressElementId]) {
            clearInterval(this.progressIntervals[progressElementId]);
        }
        
        let progress = 0;
        const increment = 100 / (duration / 1000);
        
        this.progressIntervals[progressElementId] = setInterval(() => {
            progress += increment;
            
            if (progress > 90) {
                progress = 90;
            }
            
            progressElement.style.width = progress + '%';
            textElement.textContent = Math.round(progress) + '%';
        }, 1000);
    }

    /**
     * 完成進度
     * @param {string} progressElementId - 進度條元素ID
     * @param {string} textElementId - 文本元素ID
     */
    completeProgress(progressElementId, textElementId) {
        if (this.progressIntervals[progressElementId]) {
            clearInterval(this.progressIntervals[progressElementId]);
            delete this.progressIntervals[progressElementId];
        }
        
        const progressElement = document.getElementById(progressElementId);
        const textElement = document.getElementById(textElementId);
        
        if (progressElement && textElement) {
            progressElement.style.width = '100%';
            textElement.textContent = '100%';
        }
    }

    /**
     * 重置進度
     * @param {string} progressElementId - 進度條元素ID
     * @param {string} textElementId - 文本元素ID
     */
    resetProgress(progressElementId, textElementId) {
        if (this.progressIntervals[progressElementId]) {
            clearInterval(this.progressIntervals[progressElementId]);
            delete this.progressIntervals[progressElementId];
        }
        
        const progressElement = document.getElementById(progressElementId);
        const textElement = document.getElementById(textElementId);
        
        if (progressElement && textElement) {
            progressElement.style.width = '0%';
            textElement.textContent = '0%';
        }
    }

    /**
     * 更新進度
     * @param {string} progressElementId - 進度條元素ID
     * @param {string} textElementId - 文本元素ID
     * @param {number} percent - 進度百分比
     * @param {string} message - 進度消息
     */
    updateProgress(progressElementId, textElementId, percent, message) {
        const progressElement = document.getElementById(progressElementId);
        const textElement = document.getElementById(textElementId);
        const loadingElement = document.getElementById(message ? 'loading-text' : null);
        
        if (progressElement) {
            progressElement.style.width = (percent * 100) + '%';
        }
        if (textElement) {
            textElement.textContent = Math.round(percent * 100) + '%';
        }
        if (loadingElement && message) {
            loadingElement.textContent = message;
        }
    }

    /**
     * 顯示載入動畫
     * @param {string} loadingElementId - 載入元素ID
     */
    showLoading(loadingElementId) {
        const element = document.getElementById(loadingElementId);
        if (element) {
            element.classList.add('show');
        }
    }

    /**
     * 隱藏載入動畫
     * @param {string} loadingElementId - 載入元素ID
     */
    hideLoading(loadingElementId) {
        const element = document.getElementById(loadingElementId);
        if (element) {
            element.classList.remove('show');
        }
    }

    /**
     * 切換元素可見性
     * @param {string} elementId - 元素ID
     * @param {boolean} visible - 是否可見
     */
    toggleElement(elementId, visible) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.display = visible ? 'block' : 'none';
        }
    }

    /**
     * 啟用/禁用按鈕
     * @param {string} buttonId - 按鈕ID
     * @param {boolean} enabled - 是否啟用
     */
    toggleButton(buttonId, enabled) {
        const button = document.getElementById(buttonId);
        if (button) {
            button.disabled = !enabled;
        }
    }

    /**
     * 設置輸入值
     * @param {string} inputId - 輸入框ID
     * @param {string} value - 值
     */
    setInputValue(inputId, value) {
        const input = document.getElementById(inputId);
        if (input) {
            input.value = value;
        }
    }

    /**
     * 獲取輸入值
     * @param {string} inputId - 輸入框ID
     * @returns {string} 輸入值
     */
    getInputValue(inputId) {
        const input = document.getElementById(inputId);
        return input ? input.value.trim() : '';
    }

    /**
     * 清空容器內容
     * @param {string} containerId - 容器ID
     */
    clearContainer(containerId) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = '';
        }
    }

    /**
     * 設置容器內容
     * @param {string} containerId - 容器ID
     * @param {string} content - 內容
     */
    setContainerContent(containerId, content) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = content;
        }
    }

    /**
     * 添加內容到容器
     * @param {string} containerId - 容器ID
     * @param {string} content - 內容
     */
    appendToContainer(containerId, content) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML += content;
        }
    }

    /**
     * 創建模態框
     * @param {string} title - 標題
     * @param {string} content - 內容
     * @param {Object} options - 選項
     */
    showModal(title, content, options = {}) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        
        const modalContent = document.createElement('div');
        modalContent.className = 'modal-content';
        
        modalContent.innerHTML = `
            <div class="modal-header">
                <h3>${title}</h3>
                <button class="modal-close" onclick="this.closest('.modal').remove()">&times;</button>
            </div>
            <div class="modal-body">
                ${content}
            </div>
        `;
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        // 點擊外部關閉
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });

        // ESC鍵關閉
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                modal.remove();
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);

        return modal;
    }

    /**
     * 創建確認對話框
     * @param {string} message - 確認消息
     * @param {Function} onConfirm - 確認回調
     * @param {Function} onCancel - 取消回調
     */
    showConfirm(message, onConfirm, onCancel) {
        const modal = this.showModal('確認', `
            <div style="padding: 1rem;">
                <p style="margin-bottom: 1rem;">${message}</p>
                <div style="text-align: right; gap: 0.5rem; display: flex; justify-content: flex-end;">
                    <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">取消</button>
                    <button class="btn btn-primary" id="confirmBtn">確認</button>
                </div>
            </div>
        `);

        const confirmBtn = modal.querySelector('#confirmBtn');
        confirmBtn.addEventListener('click', () => {
            modal.remove();
            if (onConfirm) onConfirm();
        });

        if (onCancel) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal || e.target.classList.contains('modal-close')) {
                    onCancel();
                }
            });
        }
    }

    /**
     * 滾動到元素
     * @param {string} elementId - 元素ID
     * @param {Object} options - 滾動選項
     */
    scrollToElement(elementId, options = {}) {
        const element = document.getElementById(elementId);
        if (element) {
            element.scrollIntoView({
                behavior: 'smooth',
                block: 'start',
                ...options
            });
        }
    }

    /**
     * 高亮元素
     * @param {string} elementId - 元素ID
     * @param {number} duration - 高亮持續時間
     */
    highlightElement(elementId, duration = 2000) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.backgroundColor = '#fff3cd';
            element.style.transition = 'background-color 0.3s ease';
            
            setTimeout(() => {
                element.style.backgroundColor = '';
                setTimeout(() => {
                    element.style.transition = '';
                }, 300);
            }, duration);
        }
    }

    /**
     * 複製文本到剪貼板並顯示反饋
     * @param {string} text - 要複製的文本
     * @param {string} message - 成功消息
     */
    async copyToClipboard(text, message = '已複製到剪貼板') {
        try {
            await Utils.copyToClipboard(text);
            this.showSuccess(message);
        } catch (error) {
            this.showError('複製失敗');
        }
    }

    /**
     * 創建工具提示
     * @param {string} elementId - 元素ID
     * @param {string} text - 提示文本
     */
    addTooltip(elementId, text) {
        const element = document.getElementById(elementId);
        if (element) {
            element.title = text;
            element.setAttribute('data-tooltip', text);
        }
    }

    /**
     * 動畫計數
     * @param {string} elementId - 元素ID
     * @param {number} start - 開始數字
     * @param {number} end - 結束數字
     * @param {number} duration - 動畫持續時間
     */
    animateNumber(elementId, start, end, duration = 1000) {
        const element = document.getElementById(elementId);
        if (!element) return;

        const range = end - start;
        const increment = range / (duration / 16);
        let current = start;

        const timer = setInterval(() => {
            current += increment;
            if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
                current = end;
                clearInterval(timer);
            }
            element.textContent = Math.round(current);
        }, 16);
    }

    /**
     * 淡入動畫
     * @param {string} elementId - 元素ID
     * @param {number} duration - 動畫持續時間
     */
    fadeIn(elementId, duration = 300) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.opacity = '0';
            element.style.display = 'block';
            element.style.transition = `opacity ${duration}ms ease`;
            
            setTimeout(() => {
                element.style.opacity = '1';
            }, 10);
        }
    }

    /**
     * 淡出動畫
     * @param {string} elementId - 元素ID
     * @param {number} duration - 動畫持續時間
     */
    fadeOut(elementId, duration = 300) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.transition = `opacity ${duration}ms ease`;
            element.style.opacity = '0';
            
            setTimeout(() => {
                element.style.display = 'none';
            }, duration);
        }
    }
}

// 創建全局UI管理器實例
const uiManager = new UIManager();