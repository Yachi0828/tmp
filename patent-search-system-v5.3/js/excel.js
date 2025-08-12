/**
 * Excel分析功能模塊
 * 處理Excel文件的上傳、分析和導出
 */

class ExcelManager {
    constructor() {
        this.selectedFile = null;
        this.currentAnalysisResults = null;
        this.isProcessing = false;
        this.elements = {};
    }

    /**
     * 初始化Excel管理器
     */
    init() {
        this.cacheElements();
        this.bindEvents();
        console.log('Excel分析模塊已初始化');
    }

    /**
     * 快取DOM元素
     */
    cacheElements() {
        this.elements = {
            uploadArea: document.getElementById('uploadArea'),
            excelFileInput: document.getElementById('excelFileInput'),
            selectFileBtn: document.getElementById('selectFileBtn'),
            fileInfo: document.getElementById('fileInfo'),
            analyzeExcelBtn: document.getElementById('analyzeExcelBtn'),
            clearFileBtn: document.getElementById('clearFileBtn'),
            
            // 載入相關
            loadingExcel: document.getElementById('loading-excel'),
            loadingTextExcel: document.getElementById('loading-text-excel'),
            progressFillExcel: document.getElementById('progress-fill-excel'),
            progressTextExcel: document.getElementById('progress-text-excel'),
            
            // 結果顯示
            analysisSummary: document.getElementById('analysis-summary'),
            totalPatentsProcessed: document.getElementById('totalPatentsProcessed'),
            successfulAnalysis: document.getElementById('successfulAnalysis'),
            failedAnalysis: document.getElementById('failedAnalysis'),
            analysisMethod: document.getElementById('analysisMethod'),
            excelAnalysisResults: document.getElementById('excel-analysis-results'),
            excelPatentList: document.getElementById('excel-patent-list'),
            exportAnalysisBtn: document.getElementById('exportAnalysisBtn')
        };
    }

    /**
     * 綁定事件
     */
    bindEvents() {
        // 文件選擇
        if (this.elements.selectFileBtn) {
            this.elements.selectFileBtn.addEventListener('click', () => {
                if (this.elements.excelFileInput) {
                    this.elements.excelFileInput.click();
                }
            });
        }

        if (this.elements.excelFileInput) {
            this.elements.excelFileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }

        // 拖放事件
        if (this.elements.uploadArea) {
            this.elements.uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
            this.elements.uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
            this.elements.uploadArea.addEventListener('drop', (e) => this.handleDrop(e));
        }

        // 分析和清除按鈕
        if (this.elements.analyzeExcelBtn) {
            this.elements.analyzeExcelBtn.addEventListener('click', () => this.analyzeExcel());
        }

        if (this.elements.clearFileBtn) {
            this.elements.clearFileBtn.addEventListener('click', () => this.clearFile());
        }

        if (this.elements.exportAnalysisBtn) {
            this.elements.exportAnalysisBtn.addEventListener('click', () => this.exportAnalysisResults());
        }
    }

    /**
     * 處理拖拽懸停
     * @param {Event} e - 事件對象
     */
    handleDragOver(e) {
        e.preventDefault();
        if (this.elements.uploadArea) {
            this.elements.uploadArea.classList.add('dragover');
        }
    }

    /**
     * 處理拖拽離開
     * @param {Event} e - 事件對象
     */
    handleDragLeave(e) {
        e.preventDefault();
        if (this.elements.uploadArea) {
            this.elements.uploadArea.classList.remove('dragover');
        }
    }

    /**
     * 處理拖拽放下
     * @param {Event} e - 事件對象
     */
    handleDrop(e) {
        e.preventDefault();
        if (this.elements.uploadArea) {
            this.elements.uploadArea.classList.remove('dragover');
        }
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            if (this.validateExcelFile(file)) {
                this.setSelectedFile(file);
            }
        }
    }

    /**
     * 處理文件選擇
     * @param {Event} e - 事件對象
     */
    handleFileSelect(e) {
        const file = e.target.files[0];
        if (file && this.validateExcelFile(file)) {
            this.setSelectedFile(file);
        }
    }

    /**
     * 驗證Excel文件
     * @param {File} file - 文件對象
     * @returns {boolean} 是否有效
     */
    validateExcelFile(file) {
        // 檢查檔案類型
        const validTypes = [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
            'application/vnd.ms-excel' // .xls
        ];
        
        const validExtensions = ['.xlsx', '.xls'];
        const fileName = file.name.toLowerCase();
        const hasValidExtension = validExtensions.some(ext => fileName.endsWith(ext));
        
        if (!validTypes.includes(file.type) && !hasValidExtension) {
            uiManager.showError('請選擇有效的Excel檔案(.xlsx 或 .xls)');
            return false;
        }

        // 檢查檔案大小 (10MB)
        if (file.size > 10 * 1024 * 1024) {
            uiManager.showError('檔案大小不能超過10MB');
            return false;
        }

        return true;
    }

    /**
     * 設置選中的文件
     * @param {File} file - 文件對象
     */
    setSelectedFile(file) {
        this.selectedFile = file;
        
        // 顯示檔案資訊
        const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
        if (this.elements.fileInfo) {
            this.elements.fileInfo.innerHTML = `
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span>📄</span>
                    <strong>${Utils.escapeHtml(file.name)}</strong>
                    <span>(${fileSizeMB} MB)</span>
                </div>
            `;
            this.elements.fileInfo.style.display = 'block';
        }
        
        // 顯示分析按鈕
        if (this.elements.analyzeExcelBtn) {
            this.elements.analyzeExcelBtn.style.display = 'inline-block';
            this.elements.analyzeExcelBtn.disabled = false;
        }
        if (this.elements.clearFileBtn) {
            this.elements.clearFileBtn.style.display = 'inline-block';
        }
        
        uiManager.showSuccess('Excel檔案已選擇，點擊"開始分析"進行處理');
    }

    /**
     * 清除文件
     */
    clearFile() {
        this.selectedFile = null;
        this.currentAnalysisResults = null;
        
        if (this.elements.excelFileInput) {
            this.elements.excelFileInput.value = '';
        }
        if (this.elements.fileInfo) {
            this.elements.fileInfo.style.display = 'none';
        }
        if (this.elements.analyzeExcelBtn) {
            this.elements.analyzeExcelBtn.style.display = 'none';
        }
        if (this.elements.clearFileBtn) {
            this.elements.clearFileBtn.style.display = 'none';
        }
        if (this.elements.excelAnalysisResults) {
            this.elements.excelAnalysisResults.style.display = 'none';
        }
        if (this.elements.analysisSummary) {
            this.elements.analysisSummary.style.display = 'none';
        }
    }

    /**
     * 分析Excel文件
     */
    async analyzeExcel() {
        if (!this.selectedFile) {
            uiManager.showError('請先選擇Excel檔案');
            return;
        }

        if (this.isProcessing) {
            uiManager.showError('系統正在處理其他請求，請稍候...');
            return;
        }

        try {
            this.isProcessing = true;
            this.disableAnalysisControls();
            this.showAnalysisLoading();
            
            this.updateExcelProgress(0.1, '正在上傳Excel檔案...');
            uiManager.startProgressAnimation('progress-fill-excel', 'progress-text-excel', 60000);

            const response = await apiService.uploadAndAnalyzeExcel(this.selectedFile);
            
            if (response.success) {
                uiManager.completeProgress('progress-fill-excel', 'progress-text-excel');
                this.completeExcelAnalysis(response);
                uiManager.showSuccess(`Excel分析完成！成功處理 ${response.processed_count} 筆專利，失敗 ${response.errors?.length || 0} 筆`);
            } else {
                throw new Error(response.message || '分析失敗');
            }

        } catch (error) {
            console.error('Excel分析錯誤:', error);
            uiManager.showError(`Excel分析失敗: ${Utils.extractErrorMessage(error)}`);
        } finally {
            this.isProcessing = false;
            this.enableAnalysisControls();
            this.hideAnalysisLoading();
            uiManager.resetProgress('progress-fill-excel', 'progress-text-excel');
        }
    }

    /**
     * 完成Excel分析
     * @param {Object} data - 分析結果數據
     */
    completeExcelAnalysis(data) {
        this.currentAnalysisResults = data;
        
        // 顯示摘要統計
        this.displayAnalysisSummary(data);
        
        // 顯示分析結果
        this.displayExcelAnalysisResults(data);
        
        // 更新搜索結果到全局狀態（如果需要啟用聊天功能）
        if (window.patentSearchApp) {
            window.patentSearchApp.searchResults.excel = data.results;
            if (!chatManager.isEnabled()) {
                chatManager.enableChat();
            }
        }
    }

    /**
     * 顯示分析摘要
     * @param {Object} data - 分析數據
     */
    displayAnalysisSummary(data) {
        const totalCount = data.total_count || 0;
        const successCount = data.processed_count || 0;
        const failedCount = (data.errors && data.errors.length) || 0;
        
        // 分析方法統計
        let primaryMethod = 'QWEN';
        if (data.results && data.results.length > 0) {
            const methodCount = {};
            data.results.forEach(result => {
                const method = result['分析方法'] || 'unknown';
                methodCount[method] = (methodCount[method] || 0) + 1;
            });
            
            // 找出最常用的分析方法
            primaryMethod = Object.keys(methodCount).reduce((a, b) => 
                methodCount[a] > methodCount[b] ? a : b, 'QWEN');
            
            // 格式化方法名稱
            if (primaryMethod === 'qwen_api') primaryMethod = 'Qwen AI';
            else if (primaryMethod === 'fallback') primaryMethod = 'Fallback';
            else primaryMethod = 'QWEN';
        }

        // 更新統計顯示
        if (this.elements.totalPatentsProcessed) {
            this.elements.totalPatentsProcessed.textContent = totalCount;
        }
        if (this.elements.successfulAnalysis) {
            this.elements.successfulAnalysis.textContent = successCount;
        }
        if (this.elements.failedAnalysis) {
            this.elements.failedAnalysis.textContent = failedCount;
        }
        if (this.elements.analysisMethod) {
            this.elements.analysisMethod.textContent = primaryMethod;
        }
        
        if (this.elements.analysisSummary) {
            this.elements.analysisSummary.style.display = 'block';
        }
    }

    /**
     * 顯示Excel分析結果
     * @param {Object} data - 分析數據
     */
    displayExcelAnalysisResults(data) {
        if (!data.results || data.results.length === 0) {
            if (this.elements.excelPatentList) {
                this.elements.excelPatentList.innerHTML = '<div class="no-results">沒有成功分析的專利資料</div>';
            }
            if (this.elements.exportAnalysisBtn) {
                this.elements.exportAnalysisBtn.style.display = 'none';
            }
        } else {
            if (this.elements.excelPatentList) {
                this.elements.excelPatentList.innerHTML = this.generateExcelAnalysisHtml(data.results);
            }
            if (this.elements.exportAnalysisBtn) {
                this.elements.exportAnalysisBtn.style.display = 'inline-block';
            }
        }
        
        if (this.elements.excelAnalysisResults) {
            this.elements.excelAnalysisResults.style.display = 'block';
        }
    }

    /**
     * 生成Excel分析結果HTML
     * @param {Array} results - 分析結果
     * @returns {string} HTML字符串
     */
    generateExcelAnalysisHtml(results) {
        return results.map((result, index) => {
            const features = result['技術特徵'] || [];
            const effects = result['技術功效'] || [];
            
            const featuresHtml = Array.isArray(features) ? 
                features.map(f => `<li>${Utils.escapeHtml(f)}</li>`).join('') :
                `<li>無技術特徵資料</li>`;

            const effectsHtml = Array.isArray(effects) ? 
                effects.map(e => `<li>${Utils.escapeHtml(e)}</li>`).join('') :
                `<li>無技術功效資料</li>`;

            return `
                <div class="patent-card">
                    <div class="patent-title">
                        ${result['序號'] || index + 1}. ${Utils.escapeHtml(result['專利名稱'] || 'N/A')}
                    </div>
                    
                    <div class="patent-metadata">
                        <div class="metadata-item">
                            <span class="metadata-label">公告號:</span>
                            <span class="metadata-value">${Utils.escapeHtml(result['公開公告號'] || 'N/A')}</span>
                        </div>
                        <div class="metadata-item">
                            <span class="metadata-label">原始行號:</span>
                            <span class="metadata-value">${result['原始行號'] || 'N/A'}</span>
                        </div>
                        <div class="metadata-item">
                            <span class="metadata-label">分析方法:</span>
                            <span class="metadata-value">${Utils.escapeHtml(result['分析方法'] || 'QWEN')}</span>
                        </div>
                    </div>

                    <div class="patent-abstract">
                        <h4>● 專利摘要</h4>
                        <p>${Utils.escapeHtml(result['摘要'] || '無摘要資料')}</p>
                    </div>

                    <div class="features-effects">
                        <div style="margin-bottom: 1rem;">
                            <h4>■ 技術特徵</h4>
                            <ul class="features-list">${featuresHtml}</ul>
                        </div>
                        <div style="margin-bottom: 1rem;">
                            <h4>▲ 技術功效</h4>
                            <ul class="effects-list">${effectsHtml}</ul>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * 導出分析結果
     */
    async exportAnalysisResults() {
        if (!this.currentAnalysisResults) {
            uiManager.showError('沒有可匯出的分析結果');
            return;
        }

        try {
            const exportData = {
                results: this.currentAnalysisResults.results,
                session_id: this.currentAnalysisResults.session_id
            };

            const result = await apiService.exportAnalysisResults(exportData);
            
            // 創建下載連結
            const url = window.URL.createObjectURL(result.blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = result.filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            uiManager.showSuccess('Excel分析結果已下載！');
        } catch (error) {
            console.error('匯出分析結果錯誤:', error);
            uiManager.showError(`匯出失敗: ${Utils.extractErrorMessage(error)}`);
        }
    }

    /**
     * 更新Excel進度
     * @param {number} percent - 進度百分比
     * @param {string} message - 進度消息
     */
    updateExcelProgress(percent, message) {
        if (this.elements.progressFillExcel) {
            this.elements.progressFillExcel.style.width = (percent * 100) + '%';
        }
        if (this.elements.loadingTextExcel) {
            this.elements.loadingTextExcel.textContent = message;
        }
    }

    /**
     * 顯示分析載入狀態
     */
    showAnalysisLoading() {
        if (this.elements.loadingExcel) {
            this.elements.loadingExcel.classList.add('show');
        }
    }

    /**
     * 隱藏分析載入狀態
     */
    hideAnalysisLoading() {
        if (this.elements.loadingExcel) {
            this.elements.loadingExcel.classList.remove('show');
        }
    }

    /**
     * 禁用分析控制項
     */
    disableAnalysisControls() {
        if (this.elements.analyzeExcelBtn) {
            this.elements.analyzeExcelBtn.disabled = true;
        }
        if (this.elements.clearFileBtn) {
            this.elements.clearFileBtn.disabled = true;
        }
        if (this.elements.selectFileBtn) {
            this.elements.selectFileBtn.disabled = true;
        }
    }

    /**
     * 啟用分析控制項
     */
    enableAnalysisControls() {
        if (this.elements.analyzeExcelBtn) {
            this.elements.analyzeExcelBtn.disabled = false;
        }
        if (this.elements.clearFileBtn) {
            this.elements.clearFileBtn.disabled = false;
        }
        if (this.elements.selectFileBtn) {
            this.elements.selectFileBtn.disabled = false;
        }
    }

    /**
     * 重置Excel管理器狀態
     */
    reset() {
        this.selectedFile = null;
        this.currentAnalysisResults = null;
        this.isProcessing = false;
        
        // 重置UI
        this.clearFile();
        this.hideAnalysisLoading();
        uiManager.resetProgress('progress-fill-excel', 'progress-text-excel');
    }

    /**
     * 檢查是否有分析結果
     * @returns {boolean} 是否有結果
     */
    hasAnalysisResults() {
        return this.currentAnalysisResults && this.currentAnalysisResults.results;
    }

    /**
     * 獲取分析結果
     * @returns {Array} 分析結果
     */
    getAnalysisResults() {
        return this.currentAnalysisResults?.results || [];
    }

    /**
     * 獲取分析統計
     * @returns {Object} 分析統計
     */
    getAnalysisStats() {
        if (!this.currentAnalysisResults) return null;
        
        return {
            total: this.currentAnalysisResults.total_count || 0,
            processed: this.currentAnalysisResults.processed_count || 0,
            failed: (this.currentAnalysisResults.errors && this.currentAnalysisResults.errors.length) || 0,
            successRate: this.currentAnalysisResults.total_count > 0 ? 
                (this.currentAnalysisResults.processed_count / this.currentAnalysisResults.total_count * 100).toFixed(1) : 0
        };
    }
}

// 創建全局Excel管理器實例
const excelManager = new ExcelManager();