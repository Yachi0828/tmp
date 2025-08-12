/**
 * 主應用程序類
 * 整合所有功能模塊並提供統一的應用程序接口
 */

class PatentSearchApp {
    constructor() {
        this.searchResults = {
            tech: null,
            condition: null,
            excel: null
        };
        this.currentTab = 'tech-search';
        this.isSearching = false;
        this.apiBaseUrl = 'http://localhost:8005';
        this.apiKeyVerified = false;
        this.currentSessionId = Utils.generateSessionId();
        this.elements = {};
        
        // 初始化設置
        this.init();
    }

    /**
     * 初始化應用程序
     */
    async init() {
        console.log('=== 專利檢索系統啟動 ===');
        
        try {
            // 初始化DOM元素
            this.cacheElements();
            
            // 設置API基礎URL
            this.setupApiUrl();
            
            // 初始化各個模塊
            this.initializeModules();
            
            // 綁定事件
            this.bindEvents();
            
            // 顯示歡迎消息
            this.showWelcomeMessage();
            
            // 自動測試API連接
            setTimeout(() => {
                this.testApiConnection();
            }, 1000);
            
            console.log('✅ 應用程序初始化完成');
            
        } catch (error) {
            console.error('❌ 應用程序初始化失敗:', error);
            uiManager.showError('系統初始化失敗，請刷新頁面重試');
        }
    }

    /**
     * 快取DOM元素
     */
    cacheElements() {
        this.elements = uiManager.cacheElements();
        console.log('✅ DOM元素已快取');
    }

    /**
     * 設置API URL
     */
    setupApiUrl() {
        const savedUrl = Utils.storage.get('api_base_url');
        if (savedUrl) {
            this.apiBaseUrl = savedUrl;
            if (this.elements.apiBaseUrl) {
                this.elements.apiBaseUrl.value = savedUrl;
            }
        } else {
            this.apiBaseUrl = Utils.determineApiUrl();
        }
        
        apiService.setBaseUrl(this.apiBaseUrl);
        console.log('✅ API URL 已設置:', this.apiBaseUrl);
    }

    /**
     * 初始化各個模塊
     */
    initializeModules() {
        // 設置會話ID
        searchManager.setSessionId(this.currentSessionId);
        chatManager.setSessionId(this.currentSessionId);
        
        // 初始化模塊
        chatManager.init();
        excelManager.init();
        
        console.log('✅ 功能模塊已初始化');
    }

    /**
     * 綁定事件
     */
    bindEvents() {
        this.bindTabEvents();
        this.bindApiEvents();
        this.bindPatentLookupEvents();
        this.bindTechSearchEvents();
        this.bindConditionSearchEvents();
        this.bindExportEvents();
        
        console.log('✅ 事件已綁定');
    }

    /**
     * 綁定分頁事件
     */
    bindTabEvents() {
        if (this.elements.tabContainer) {
            this.elements.tabContainer.addEventListener('click', (e) => {
                if (e.target.classList.contains('tab')) {
                    this.showTab(e.target.dataset.tab);
                }
            });
        }
    }

    /**
     * 綁定API相關事件
     */
    bindApiEvents() {
        if (this.elements.testApiBtn) {
            this.elements.testApiBtn.addEventListener('click', () => this.testApiConnection());
        }
        
        if (this.elements.testGpssBtn) {
            this.elements.testGpssBtn.addEventListener('click', () => this.testGpssConnection());
        }

        if (this.elements.apiBaseUrl) {
            this.elements.apiBaseUrl.addEventListener('change', (e) => {
                this.apiBaseUrl = e.target.value.trim();
                apiService.setBaseUrl(this.apiBaseUrl);
                Utils.storage.set('api_base_url', this.apiBaseUrl);
            });
        }
    }

    /**
     * 綁定專利查詢事件
     */
    bindPatentLookupEvents() {
        if (this.elements.patentLookupBtn) {
            this.elements.patentLookupBtn.addEventListener('click', () => this.lookupPatent());
        }
        
        if (this.elements.patentLookupInput) {
            this.elements.patentLookupInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.lookupPatent();
            });
        }
    }

    /**
     * 綁定技術搜索事件
     */
    bindTechSearchEvents() {
        if (this.elements.generateKeywordsBtn) {
            this.elements.generateKeywordsBtn.addEventListener('click', () => this.generateKeywords());
        }

        // 關鍵字操作按鈕
        const clearAllBtn = document.getElementById('clear-all-conditions-btn');
        if (clearAllBtn) {
            clearAllBtn.addEventListener('click', () => searchManager.clearAllConditions());
        }

        const autoGenerateBtn = document.getElementById('auto-generate-conditions-btn');
        if (autoGenerateBtn) {
            autoGenerateBtn.addEventListener('click', () => this.autoGenerateAndSearch());
        }

        const manualSearchBtn = document.getElementById('manual-search-btn');
        if (manualSearchBtn) {
            manualSearchBtn.addEventListener('click', () => this.manualSearch());
        }
    }

    /**
     * 綁定條件搜索事件
     */
    bindConditionSearchEvents() {
        if (this.elements.startConditionSearchBtn) {
            this.elements.startConditionSearchBtn.addEventListener('click', () => this.startConditionSearch());
        }
    }

    /**
     * 綁定導出事件
     */
    bindExportEvents() {
        if (this.elements.exportExcelBtn) {
            this.elements.exportExcelBtn.addEventListener('click', () => this.exportToExcel('tech'));
        }
        
        if (this.elements.exportConditionExcelBtn) {
            this.elements.exportConditionExcelBtn.addEventListener('click', () => this.exportToExcel('condition'));
        }
    }

    /**
     * 顯示分頁
     * @param {string} tabId - 分頁ID
     */
    showTab(tabId) {
        uiManager.showTab(tabId);
        this.currentTab = tabId;
        console.log('切換到分頁:', tabId);
    }

    /**
     * 顯示歡迎消息
     */
    showWelcomeMessage() {
        uiManager.showSuccess('智能專利檢索系統已啟動！請先輸入GPSS API驗證碼');
        console.log('系統已啟動，等待API驗證...');
    }

    /**
     * 測試API連接
     */
    async testApiConnection() {
        try {
            console.log(`嘗試連接API: ${this.apiBaseUrl}`);
            uiManager.updateStatus('apiStatus', 'testing', '測試中...');
            
            await apiService.testConnection();
            
            uiManager.updateStatus('apiStatus', 'success', 'API 連接正常');
            await this.testPatentAPI();
            uiManager.showSuccess('API連接測試成功！');
            
        } catch (error) {
            console.error('API連接測試失敗:', error);
            uiManager.updateStatus('apiStatus', 'error', 'API 連接失敗');
            uiManager.updateStatus('qwenStatus', 'error', '服務異常');
            uiManager.showError(`API連接失敗: ${Utils.extractErrorMessage(error)}`);
        }
    }

    /**
     * 測試專利API
     */
    async testPatentAPI() {
        try {
            await apiService.testPatentAPI();
            uiManager.updateStatus('qwenStatus', 'success', 'Qwen 服務正常');
            console.log('專利API測試成功');
        } catch (error) {
            console.warn('專利API測試失敗:', error);
            uiManager.updateStatus('qwenStatus', 'warning', 'Qwen 服務需檢查');
        }
    }

    /**
     * 測試GPSS連接
     */
    async testGpssConnection() {
        try {
            const apiKey = uiManager.getInputValue('gpssApiKey');
            
            if (!apiKey) {
                uiManager.showError('請先輸入GPSS API驗證碼');
                return;
            }

            if (apiKey.length < 16) {
                uiManager.showError('GPSS API驗證碼格式不正確（應為16位以上）');
                return;
            }

            console.log(`測試GPSS API: ${apiKey.substring(0, 8)}...`);
            uiManager.updateStatus('gpssStatus', 'testing', 'GPSS 測試中...');

            const response = await apiService.testGPSS(apiKey);

            if (response.success) {
                uiManager.updateStatus('gpssStatus', 'success', 'GPSS API 已驗證');
                uiManager.showSuccess('GPSS API連接測試成功！');
                this.apiKeyVerified = true;
                Utils.storage.set('gpss_api_key', apiKey);
            } else {
                throw new Error(response.detail || response.message || '驗證失敗');
            }
            
        } catch (error) {
            console.error('GPSS API測試錯誤:', error);
            uiManager.updateStatus('gpssStatus', 'error', 'GPSS API 驗證失敗');
            uiManager.showError(`GPSS API驗證失敗: ${Utils.extractErrorMessage(error)}`);
            this.apiKeyVerified = false;
        }
    }

    /**
     * 專利查詢
     */
    lookupPatent() {
        const patentNumber = uiManager.getInputValue('patentLookupInput');
        if (!patentNumber) {
            uiManager.showError('請輸入公開公告號');
            return;
        }
        
        const url = `https://tiponet.tipo.gov.tw/gpss4/gpsskmc/gpssbkm?!!FRURL${patentNumber}`;
        window.open(url, '_blank');
    }

    /**
     * 生成關鍵字
     */
    async generateKeywords() {
        if (!this.validateApiKey()) return;

        if (this.isSearching) {
            uiManager.showError('正在進行處理，請稍候...');
            return;
        }

        try {
            const description = uiManager.getInputValue('techDescription');
            if (!description) {
                uiManager.showError('請先輸入技術描述');
                return;
            }

            if (description.length < 50) {
                uiManager.showError('技術描述太短，請提供更詳細的描述（至少50個字）');
                return;
            }

            this.isSearching = true;
            uiManager.toggleButton('generateKeywordsBtn', false);
            uiManager.toggleElement('keyword-selection', false);
            uiManager.updateProgress('progress-fill', 'progress-text', 0.1, '正在生成關鍵字...');
            uiManager.showLoading('loading-tech');
            uiManager.startProgressAnimation('progress-fill', 'progress-text', 10000);

            const response = await searchManager.generateKeywords(description);
            
            if (response.success) {
                this.currentSessionId = response.session_id;
                searchManager.setSessionId(this.currentSessionId);
                chatManager.setSessionId(this.currentSessionId);
                
                uiManager.completeProgress('progress-fill', 'progress-text');
                this.showKeywordSelection(response);
            } else {
                throw new Error(response.detail || response.message || '關鍵字生成失敗');
            }

        } catch (error) {
            console.error('關鍵字生成錯誤:', error);
            uiManager.showError(`關鍵字生成失敗: ${Utils.extractErrorMessage(error)}`);
        } finally {
            this.isSearching = false;
            uiManager.toggleButton('generateKeywordsBtn', true);
            uiManager.hideLoading('loading-tech');
            uiManager.resetProgress('progress-fill', 'progress-text');
        }
    }

    /**
     * 顯示關鍵字選擇界面
     * @param {Object} data - 關鍵字數據
     */
    showKeywordSelection(data) {
        searchManager.initializeDragAndDrop();
        uiManager.toggleElement('keyword-selection', true);
        uiManager.showSuccess(`成功生成 ${data.keywords_with_synonyms?.length || 0} 個關鍵字組及其同義詞，請拖拉到搜索條件中`);
    }

    /**
     * 自動生成並搜索
     */
    async autoGenerateAndSearch() {
        if (!this.validateApiKey()) return;

        try {
            searchManager.autoGenerateConditions();
            await Utils.delay(500); // 讓UI更新
            await this.executeSearch();
        } catch (error) {
            console.error('自動生成搜索錯誤:', error);
            uiManager.showError(`自動搜索失敗: ${Utils.extractErrorMessage(error)}`);
        }
    }

    /**
     * 手動搜索
     */
    async manualSearch() {
        if (!this.validateApiKey()) return;
        await this.executeSearch();
    }

    /**
     * 執行搜索
     */
    async executeSearch() {
        if (this.isSearching) {
            uiManager.showError('正在進行搜尋，請稍候...');
            return;
        }

        try {
            const description = uiManager.getInputValue('techDescription');
            const gpssApiKey = uiManager.getInputValue('gpssApiKey');

            this.isSearching = true;
            uiManager.toggleElement('keyword-selection', false);
            uiManager.hideLoading('loading-tech');
            uiManager.toggleElement('tech-search-results', false);

            uiManager.updateProgress('progress-fill', 'progress-text', 0.3, '執行關鍵字檢索...');
            uiManager.showLoading('loading-tech');
            uiManager.startProgressAnimation('progress-fill', 'progress-text', 45000);

            const response = await searchManager.manualSearch(description, gpssApiKey);

            if (response.success) {
                uiManager.completeProgress('progress-fill', 'progress-text');
                this.completeTechSearch(response);

                // 啟用聊天功能
                if (!chatManager.isEnabled()) {
                    chatManager.enableChat();
                }

                uiManager.showSuccess(`搜索完成！找到 ${response.total_found || 0} 筆專利`);
            } else {
                throw new Error(response.detail || response.message || '檢索失敗');
            }

        } catch (error) {
            console.error('執行搜索錯誤:', error);
            uiManager.showError(`搜索失敗: ${Utils.extractErrorMessage(error)}`);
        } finally {
            this.isSearching = false;
            uiManager.hideLoading('loading-tech');
            uiManager.resetProgress('progress-fill', 'progress-text');
        }
    }

    /**
     * 完成技術搜索
     * @param {Object} searchResults - 搜索結果
     */
    completeTechSearch(searchResults) {
        this.searchResults.tech = searchResults.search_results || searchResults.results || [];
        this.displayTechSearchResults();
    }

    /**
     * 顯示技術搜索結果
     */
    displayTechSearchResults() {
        const results = this.searchResults.tech;
        if (!results || !results.length) {
            uiManager.setContainerContent('tech-patent-list', '<div class="no-results">沒有找到相關的專利</div>');
            uiManager.toggleElement('exportExcelBtn', false);
        } else {
            uiManager.setContainerContent('tech-patent-list', searchManager.generatePatentListHtml(results));
            uiManager.toggleElement('exportExcelBtn', true);
        }
        uiManager.toggleElement('tech-search-results', true);
    }

    /**
     * 開始條件搜索
     */
    async startConditionSearch() {
        if (!this.validateApiKey()) return;

        if (this.isSearching) {
            uiManager.showError('正在進行搜尋，請稍候...');
            return;
        }

        try {
            // 確保有session_id
            if (!this.currentSessionId) {
                this.currentSessionId = Utils.generateSessionId();
                searchManager.setSessionId(this.currentSessionId);
                chatManager.setSessionId(this.currentSessionId);
            }

            const searchParams = this.buildConditionSearchParams();

            this.isSearching = true;
            uiManager.toggleButton('startConditionSearchBtn', false);
            uiManager.showLoading('loading-condition');
            uiManager.toggleElement('condition-search-results', false);

            uiManager.updateProgress('progress-fill-condition', 'progress-text-condition', 0.3, '執行條件檢索...');
            uiManager.startProgressAnimation('progress-fill-condition', 'progress-text-condition', 30000);

            const searchResults = await searchManager.conditionSearch(searchParams);

            uiManager.completeProgress('progress-fill-condition', 'progress-text-condition');
            this.completeConditionSearch(searchResults);

            uiManager.showSuccess(`條件搜尋完成！找到 ${searchResults.total} 筆專利`);

            // 啟用聊天功能
            if (!chatManager.isEnabled()) {
                chatManager.enableChat();
            }

        } catch (error) {
            console.error('條件搜索錯誤:', error);
            uiManager.showError(`條件查詢失敗: ${Utils.extractErrorMessage(error)}`);
        } finally {
            this.isSearching = false;
            uiManager.toggleButton('startConditionSearchBtn', true);
            uiManager.hideLoading('loading-condition');
            uiManager.resetProgress('progress-fill-condition', 'progress-text-condition');
        }
    }

    /**
     * 構建條件搜索參數
     * @returns {Object} 搜索參數
     */
    buildConditionSearchParams() {
        const formData = {
            gpssApiKey: uiManager.getInputValue('gpssApiKey'),
            applicant: uiManager.getInputValue('applicant'),
            inventor: uiManager.getInputValue('inventor'),
            patentNumber: uiManager.getInputValue('patentNumber'),
            applicationNumber: uiManager.getInputValue('applicationNumber'),
            ipcClass: uiManager.getInputValue('ipcClass'),
            titleKeyword: uiManager.getInputValue('titleKeyword'),
            abstractKeyword: uiManager.getInputValue('abstractKeyword'),
            claimsKeyword: uiManager.getInputValue('claimsKeyword'),
            applicationDateFrom: uiManager.getInputValue('applicationDateFrom'),
            applicationDateTo: uiManager.getInputValue('applicationDateTo'),
            publicationDateFrom: uiManager.getInputValue('publicationDateFrom'),
            publicationDateTo: uiManager.getInputValue('publicationDateTo')
        };

        return searchManager.buildConditionSearchParams(formData);
    }

    /**
     * 完成條件搜索
     * @param {Object} searchResults - 搜索結果
     */
    completeConditionSearch(searchResults) {
        this.searchResults.condition = searchResults.patents || [];
        this.displayConditionSearchResults();
    }

    /**
     * 顯示條件搜索結果
     */
    displayConditionSearchResults() {
        const results = this.searchResults.condition;
        if (!results || !results.length) {
            uiManager.setContainerContent('condition-patent-list', '<div class="no-results">沒有找到相關的專利</div>');
            uiManager.toggleElement('exportConditionExcelBtn', false);
        } else {
            uiManager.setContainerContent('condition-patent-list', searchManager.generatePatentListHtml(results));
            uiManager.toggleElement('exportConditionExcelBtn', true);
        }
        uiManager.toggleElement('condition-search-results', true);
    }

    /**
     * 導出到Excel
     * @param {string} type - 搜索類型
     */
    async exportToExcel(type) {
        try {
            await searchManager.exportToExcel(type);
            uiManager.showSuccess('Excel文件已下載！');
        } catch (error) {
            console.error('Excel匯出錯誤:', error);
            uiManager.showError(`Excel匯出失敗: ${Utils.extractErrorMessage(error)}`);
        }
    }

    /**
     * 驗證API密鑰
     * @returns {boolean} 是否有效
     */
    validateApiKey() {
        const apiKey = uiManager.getInputValue('gpssApiKey');
        if (!apiKey) {
            uiManager.showError('請先輸入GPSS API驗證碼並完成驗證');
            return false;
        }
        if (!this.apiKeyVerified) {
            uiManager.showError('請先完成GPSS API驗證');
            return false;
        }
        return true;
    }

    /**
     * 檢查是否有任何搜索結果
     * @returns {boolean} 是否有結果
     */
    hasAnyResults() {
        return this.searchResults.tech || this.searchResults.condition || this.searchResults.excel;
    }

    /**
     * 重置應用狀態
     */
    reset() {
        this.searchResults = {
            tech: null,
            condition: null,
            excel: null
        };
        this.isSearching = false;
        this.currentSessionId = Utils.generateSessionId();
        
        // 重置各個模塊
        searchManager.reset();
        chatManager.reset();
        excelManager.reset();
        
        // 重置UI
        this.hideAllResults();
        this.resetAllProgress();
        
        console.log('應用狀態已重置');
    }

    /**
     * 隱藏所有結果
     */
    hideAllResults() {
        uiManager.toggleElement('keyword-selection', false);
        uiManager.toggleElement('tech-search-results', false);
        uiManager.toggleElement('condition-search-results', false);
        uiManager.toggleElement('excel-analysis-results', false);
    }

    /**
     * 重置所有進度
     */
    resetAllProgress() {
        uiManager.hideLoading('loading-tech');
        uiManager.hideLoading('loading-condition');
        uiManager.hideLoading('loading-excel');
        
        uiManager.resetProgress('progress-fill', 'progress-text');
        uiManager.resetProgress('progress-fill-condition', 'progress-text-condition');
        uiManager.resetProgress('progress-fill-excel', 'progress-text-excel');
    }

    /**
     * 獲取應用狀態
     * @returns {Object} 應用狀態
     */
    getStatus() {
        return {
            currentTab: this.currentTab,
            isSearching: this.isSearching,
            apiKeyVerified: this.apiKeyVerified,
            currentSessionId: this.currentSessionId,
            hasResults: this.hasAnyResults(),
            searchResults: {
                tech: this.searchResults.tech?.length || 0,
                condition: this.searchResults.condition?.length || 0,
                excel: this.searchResults.excel?.length || 0
            },
            modules: {
                search: searchManager.hasSearchResults(),
                chat: chatManager.isEnabled(),
                excel: excelManager.hasAnalysisResults()
            }
        };
    }

    /**
     * 顯示應用狀態（調試用）
     */
    showStatus() {
        const status = this.getStatus();
        console.table(status);
        console.log('詳細狀態:', status);
    }
}

// 啟動應用程序
document.addEventListener('DOMContentLoaded', function() {
    try {
        const app = new PatentSearchApp();
        
        // 將應用實例掛載到全局對象，方便調試和模塊間通信
        window.patentSearchApp = app;
        
        console.log('🎉 改進版專利檢索系統已啟動 v2.0 - 智能問答功能');
        console.log('📝 系統功能：技術描述搜索、條件搜索、Excel分析、智能問答');
        console.log('🔧 調試命令：window.patentSearchApp.showStatus() 查看系統狀態');
        
    } catch (error) {
        console.error('❌ 系統啟動失敗:', error);
        
        // 顯示錯誤信息給用戶
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.innerHTML = `
            <strong>⚠ 系統啟動失敗</strong><br>
            錯誤信息: ${error.message}<br>
            請刷新頁面重試，如問題持續存在請聯繫技術支援。
        `;
        
        const body = document.body;
        if (body) {
            body.insertBefore(errorDiv, body.firstChild);
        }
    }
});