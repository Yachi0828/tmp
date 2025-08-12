/**
 * 搜索功能模塊
 * 處理技術描述搜索和條件搜索
 */

class SearchManager {
    constructor() {
        this.generatedKeywords = [];
        this.currentSessionId = null;
        this.isSearching = false;
        this.searchResults = {
            tech: null,
            condition: null
        };
    }

    /**
     * 設置會話ID
     * @param {string} sessionId - 會話ID
     */
    setSessionId(sessionId) {
        this.currentSessionId = sessionId;
    }

    /**
     * 生成關鍵字
     * @param {string} description - 技術描述
     * @returns {Promise<Object>} 生成結果
     */
    async generateKeywords(description) {
        if (!description || description.length < 50) {
            throw new Error('技術描述太短，請提供更詳細的描述（至少50個字）');
        }

        if (!this.currentSessionId) {
            this.currentSessionId = Utils.generateSessionId();
        }

        try {
            const response = await apiService.generateKeywords(description, this.currentSessionId);
            
            if (response.success) {
                this.currentSessionId = response.session_id;
                this.generatedKeywords = response.keywords_with_synonyms || [];
                return response;
            } else {
                throw new Error(response.detail || response.message || '關鍵字生成失敗');
            }
        } catch (error) {
            console.error('關鍵字生成錯誤:', error);
            throw error;
        }
    }

    /**
     * 初始化拖放功能
     */
    initializeDragAndDrop() {
        this.initializeAvailableKeywords();
        this.initializeDropZones();
        this.bindConditionEvents();
    }

    /**
     * 初始化可用關鍵字
     */
    initializeAvailableKeywords() {
        const availableKeywords = document.getElementById('available-keywords');
        if (!availableKeywords) return;

        availableKeywords.innerHTML = '';

        this.generatedKeywords.forEach((group, groupIndex) => {
            const keyword = group.keyword || '';
            const synonyms = group.synonyms || [];

            // 創建主關鍵字
            if (keyword) {
                const keywordDiv = this.createDraggableKeyword(keyword, 'keyword');
                availableKeywords.appendChild(keywordDiv);
            }

            // 創建同義詞
            synonyms.forEach(synonym => {
                const synonymDiv = this.createDraggableKeyword(synonym, 'synonym');
                availableKeywords.appendChild(synonymDiv);
            });
        });
    }

    /**
     * 創建可拖拉的關鍵字元素
     * @param {string} text - 關鍵字文本
     * @param {string} type - 類型（keyword/synonym）
     * @returns {HTMLElement} 關鍵字元素
     */
    createDraggableKeyword(text, type) {
        const div = document.createElement('div');
        div.className = type === 'keyword' ? 'keyword-item' : 'synonym-item';
        div.textContent = text;
        div.draggable = true;
        div.dataset.keyword = text;
        div.dataset.type = type;

        // 添加拖拽事件
        div.addEventListener('dragstart', (e) => {
            e.dataTransfer.setData('text/plain', text);
            e.dataTransfer.setData('type', type);
        });

        return div;
    }

    /**
     * 初始化拖放區域
     */
    initializeDropZones() {
        const dropZones = document.querySelectorAll('.keywords-dropzone');
        dropZones.forEach(zone => {
            // 移除舊的事件監聽器
            zone.removeEventListener('dragover', this.handleDragOver);
            zone.removeEventListener('dragleave', this.handleDragLeave);
            zone.removeEventListener('drop', this.handleDrop);

            // 添加新的事件監聽器
            zone.addEventListener('dragover', this.handleDragOver.bind(this));
            zone.addEventListener('dragleave', this.handleDragLeave.bind(this));
            zone.addEventListener('drop', this.handleDrop.bind(this));
        });
    }

    /**
     * 處理拖拽懸停
     * @param {Event} e - 事件對象
     */
    handleDragOver(e) {
        e.preventDefault();
        e.currentTarget.classList.add('dragover');
    }

    /**
     * 處理拖拽離開
     * @param {Event} e - 事件對象
     */
    handleDragLeave(e) {
        e.currentTarget.classList.remove('dragover');
    }

    /**
     * 處理拖拽放下
     * @param {Event} e - 事件對象
     */
    handleDrop(e) {
        e.preventDefault();
        e.currentTarget.classList.remove('dragover');

        const keyword = e.dataTransfer.getData('text/plain');
        const type = e.dataTransfer.getData('type');

        this.addKeywordToDropZone(e.currentTarget, keyword, type);
    }

    /**
     * 添加關鍵字到拖放區域
     * @param {HTMLElement} zone - 拖放區域
     * @param {string} keyword - 關鍵字
     * @param {string} type - 類型
     */
    addKeywordToDropZone(zone, keyword, type) {
        const droppedKeywords = zone.querySelector('.dropped-keywords');
        const hint = zone.querySelector('.dropzone-hint');

        // 隱藏提示文字
        if (hint) hint.style.display = 'none';

        // 檢查是否已存在
        const existingKeywords = Array.from(droppedKeywords.children)
            .map(child => child.textContent.replace('×', '').trim());

        if (existingKeywords.includes(keyword)) {
            return; // 已存在，不重複添加
        }

        // 創建關鍵字標籤
        const keywordSpan = document.createElement('span');
        keywordSpan.className = 'dropped-keyword';
        keywordSpan.innerHTML = `${keyword} <span class="remove-btn">×</span>`;

        // 添加移除功能
        keywordSpan.querySelector('.remove-btn').addEventListener('click', () => {
            keywordSpan.remove();
            if (droppedKeywords.children.length === 0 && hint) {
                hint.style.display = 'block';
            }
        });

        droppedKeywords.appendChild(keywordSpan);
    }

    /**
     * 綁定條件事件
     */
    bindConditionEvents() {
        // 綁定添加條件按鈕事件（使用事件委託）
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('add-condition-btn-inline')) {
                this.addConditionRow();
            }
        });
    }

    /**
     * 添加條件行
     */
    addConditionRow() {
        const searchConditions = document.getElementById('search-conditions');
        const conditionIndex = searchConditions.children.length;

        const newRow = this.createConditionRow(conditionIndex);
        searchConditions.appendChild(newRow);

        // 重新初始化拖放區域
        this.initializeDropZones();
    }

    /**
     * 創建條件行
     * @param {number} conditionIndex - 條件索引
     * @returns {HTMLElement} 條件行元素
     */
    createConditionRow(conditionIndex) {
        const newRow = document.createElement('div');
        newRow.className = 'condition-row';
        newRow.dataset.conditionIndex = conditionIndex;

        newRow.innerHTML = `
            <div class="keywords-dropzone" data-condition="${conditionIndex}">
                <span class="dropzone-hint">拖拉關鍵字到這裡</span>
                <div class="dropped-keywords"></div>
            </div>
            <select class="field-selector">
                <option value="TI">專利名稱</option>
                <option value="AB">摘要</option>
                <option value="CL">專利範圍</option>
            </select>
            <select class="logic-selector">
                <option value="AND">AND</option>
                <option value="OR">OR</option>
            </select>
            <button class="add-condition-btn-inline">+</button>
        `;

        return newRow;
    }

    /**
     * 清除所有條件
     */
    clearAllConditions() {
        const allDropZones = document.querySelectorAll('.keywords-dropzone');
        allDropZones.forEach(zone => {
            const droppedKeywords = zone.querySelector('.dropped-keywords');
            const hint = zone.querySelector('.dropzone-hint');

            droppedKeywords.innerHTML = '';
            if (hint) hint.style.display = 'block';
        });

        // 重置為只有一個條件行
        const searchConditions = document.getElementById('search-conditions');
        const firstRow = searchConditions.querySelector('.condition-row');

        // 清除第一行的內容
        const firstDropZone = firstRow.querySelector('.dropped-keywords');
        const firstHint = firstRow.querySelector('.dropzone-hint');
        firstDropZone.innerHTML = '';
        if (firstHint) firstHint.style.display = 'block';

        // 重置選擇器
        firstRow.querySelector('.field-selector').selectedIndex = 0;
        firstRow.querySelector('.logic-selector').selectedIndex = 0;

        // 移除其他多餘的行
        const allRows = searchConditions.querySelectorAll('.condition-row');
        for (let i = 1; i < allRows.length; i++) {
            allRows[i].remove();
        }

        uiManager.showSuccess('已清除所有搜索條件');
    }

    /**
     * 自動生成條件
     */
    autoGenerateConditions() {
        this.clearAllConditions();

        if (this.generatedKeywords.length === 0) {
            uiManager.showError('沒有可用的關鍵字組合');
            return;
        }

        const searchConditions = document.getElementById('search-conditions');

        this.generatedKeywords.forEach((group, groupIndex) => {
            const keyword = group.keyword || '';
            const synonyms = group.synonyms || [];

            // 收集這一組的所有詞彙
            const allTerms = [];
            if (keyword) allTerms.push(keyword);
            allTerms.push(...synonyms);

            if (allTerms.length === 0) return;

            let conditionRow;

            if (groupIndex === 0) {
                // 使用第一行
                conditionRow = searchConditions.querySelector('.condition-row');
            } else {
                // 創建新行
                conditionRow = this.createConditionRow(groupIndex);
                searchConditions.appendChild(conditionRow);
            }

            // 填充關鍵字到該行
            const dropZone = conditionRow.querySelector('.keywords-dropzone');
            allTerms.forEach(term => {
                this.addKeywordToDropZone(dropZone, term, 'auto');
            });

            // 設置欄位為摘要
            const fieldSelector = conditionRow.querySelector('.field-selector');
            fieldSelector.value = 'AB';

            // 設置邏輯為AND
            const logicSelector = conditionRow.querySelector('.logic-selector');
            if (groupIndex < this.generatedKeywords.length - 1) {
                logicSelector.value = 'AND';
            }
        });

        // 重新初始化拖放區域
        this.initializeDropZones();

        uiManager.showSuccess(`已自動生成 ${this.generatedKeywords.length} 個搜索條件組`);
    }

    /**
     * 收集搜索條件
     * @returns {Array} 搜索條件列表
     */
    collectSearchConditions() {
        const searchConditions = [];
        const conditionRows = document.querySelectorAll('.condition-row');

        conditionRows.forEach((row, index) => {
            const droppedKeywords = row.querySelectorAll('.dropped-keyword');
            const fieldSelector = row.querySelector('.field-selector');
            const logicSelector = row.querySelector('.logic-selector');

            if (droppedKeywords.length > 0) {
                const keywords = Array.from(droppedKeywords)
                    .map(keyword => keyword.textContent.replace('×', '').trim())
                    .filter(kw => kw && kw.length > 0);

                if (keywords.length > 0) {
                    searchConditions.push({
                        keywords: keywords,
                        field: fieldSelector ? fieldSelector.value : 'AB',
                        logic: logicSelector ? logicSelector.value : 'AND',
                        condition_index: index
                    });
                }
            }
        });

        return searchConditions;
    }

    /**
     * 手動搜索
     * @param {string} description - 技術描述
     * @param {string} gpssApiKey - GPSS API密鑰
     * @returns {Promise<Object>} 搜索結果
     */
    async manualSearch(description, gpssApiKey) {
        const searchConditions = this.collectSearchConditions();

        if (searchConditions.length === 0) {
            throw new Error('請先拖拉關鍵字到搜索條件中');
        }

        // 檢查每個條件是否都有關鍵字
        const emptyConditions = searchConditions.filter(condition => 
            !condition.keywords || condition.keywords.length === 0
        );

        if (emptyConditions.length > 0) {
            throw new Error('請確保每個搜索條件都包含關鍵字');
        }

        // 收集所有關鍵字
        const allKeywords = [];
        searchConditions.forEach(condition => {
            if (condition.keywords && condition.keywords.length > 0) {
                allKeywords.push(...condition.keywords);
            }
        });

        const uniqueKeywords = [...new Set(allKeywords)].filter(kw => kw && kw.trim());

        if (uniqueKeywords.length === 0) {
            throw new Error('沒有有效的關鍵字可用於搜索');
        }

        const requestData = {
            session_id: this.currentSessionId,
            description: description,
            generated_keywords: this.extractGeneratedKeywords(),
            selected_keywords: uniqueKeywords,
            custom_keywords: [],
            user_code: gpssApiKey,
            max_results: 1000,
            use_and_or_logic: false
        };

        try {
            const response = await apiService.confirmKeywordsAndSearch(requestData);
            
            if (response.success) {
                this.searchResults.tech = response.search_results || response.results || [];
                this.displaySearchLogic(searchConditions);
                return response;
            } else {
                throw new Error(response.detail || response.message || '檢索失敗');
            }
        } catch (error) {
            console.error('手動檢索錯誤:', error);
            throw error;
        }
    }

    /**
     * 提取生成的關鍵字
     * @returns {Array} 關鍵字列表
     */
    extractGeneratedKeywords() {
        if (this.generatedKeywords && Array.isArray(this.generatedKeywords)) {
            return this.generatedKeywords.map(group => group.keyword || '').filter(kw => kw);
        }
        return [];
    }

    /**
     * 顯示搜索邏輯
     * @param {Array} searchConditions - 搜索條件
     */
    displaySearchLogic(searchConditions) {
        const logicParts = [];

        searchConditions.forEach((condition, index) => {
            const keywords = condition.keywords || [];
            const field = condition.field || 'AB';

            if (keywords.length > 0) {
                const keywordPart = keywords.length > 1 ? 
                    `(${keywords.join(' OR ')})` : keywords[0];

                const fieldName = field === 'TI' ? '專利名稱' : 
                                 field === 'AB' ? '摘要' : '專利範圍';

                logicParts.push(`${fieldName}: ${keywordPart}`);
            }
        });

        const finalLogic = logicParts.join(' AND ');

        // 顯示在界面上
        const searchLogicDiv = document.createElement('div');
        searchLogicDiv.className = 'search-logic-display';
        searchLogicDiv.innerHTML = `
            <h4>手動配置的搜索邏輯：</h4>
            <code style="background: #f5f5f5; padding: 0.5rem; display: block; margin: 0.5rem 0; border-radius: 4px;">
                ${finalLogic}
            </code>
            <p style="color: #666; font-size: 0.9rem; margin-top: 0.5rem;">
                ✨ 系統將使用上述關鍵字在GPSS資料庫中進行檢索
            </p>
        `;

        // 插入到結果顯示區域
        const resultsDiv = document.getElementById('keywords-result');
        if (resultsDiv) {
            // 清除之前的搜索邏輯顯示
            const existingLogic = resultsDiv.querySelector('.search-logic-display');
            if (existingLogic) {
                existingLogic.remove();
            }

            resultsDiv.appendChild(searchLogicDiv);
            resultsDiv.style.display = 'block';
        }
    }

    /**
     * 條件搜索
     * @param {Object} searchParams - 搜索參數
     * @returns {Promise<Object>} 搜索結果
     */
    async conditionSearch(searchParams) {
        if (!this.hasValidConditions(searchParams)) {
            throw new Error('請至少輸入一個搜索條件');
        }

        // 確保有session_id
        if (!this.currentSessionId) {
            this.currentSessionId = Utils.generateSessionId();
        }

        // 添加session_id到搜索參數
        searchParams.session_id = this.currentSessionId;

        try {
            const response = await apiService.conditionSearch(searchParams);
            
            if (response.success) {
                this.searchResults.condition = response.results || [];
                return {
                    patents: response.results || [],
                    total: response.total_found || 0,
                    message: response.message || '條件搜索完成'
                };
            } else {
                throw new Error(response.detail || response.message || '條件搜索失敗');
            }
        } catch (error) {
            console.error('條件搜索錯誤:', error);
            throw error;
        }
    }

    /**
     * 檢查是否有有效條件
     * @param {Object} params - 參數對象
     * @returns {boolean} 是否有效
     */
    hasValidConditions(params) {
        return Object.entries(params)
            .filter(([key]) => key !== 'user_code' && key !== 'max_results' && key !== 'session_id')
            .some(([key, value]) => value && value.length > 0);
    }

    /**
     * 構建條件搜索參數
     * @param {Object} formData - 表單數據
     * @returns {Object} 搜索參數
     */
    buildConditionSearchParams(formData) {
        return {
            user_code: formData.gpssApiKey,
            max_results: 1000,
            session_id: this.currentSessionId,
            applicant: formData.applicant || '',
            inventor: formData.inventor || '',
            patent_number: formData.patentNumber || '',
            application_number: formData.applicationNumber || '',
            ipc_class: formData.ipcClass || '',
            title_keyword: formData.titleKeyword || '',
            abstract_keyword: formData.abstractKeyword || '',
            claims_keyword: formData.claimsKeyword || '',
            application_date_from: formData.applicationDateFrom || '',
            application_date_to: formData.applicationDateTo || '',
            publication_date_from: formData.publicationDateFrom || '',
            publication_date_to: formData.publicationDateTo || ''
        };
    }

    /**
     * 生成專利列表HTML
     * @param {Array} patents - 專利列表
     * @returns {string} HTML字符串
     */
    generatePatentListHtml(patents) {
        if (!patents || patents.length === 0) {
            return '<div class="no-results">沒有找到相關的專利</div>';
        }

        return patents.map((patent, index) => {
            // 處理專利名稱和連結
            const title = patent['專利名稱'] || patent.title || 'N/A';
            const patentLink = patent['專利連結'] || patent.patent_link || '';
            const publicationNumber = patent['公開公告號'] || patent.publication_number || 'N/A';

            // 建立超連結
            let titleWithLink = title;
            if (patentLink) {
                titleWithLink = `<a href="${patentLink}" target="_blank" rel="noopener" style="color: #5a5859; text-decoration: none;">${Utils.escapeHtml(title)}</a>`;
            } else if (publicationNumber && publicationNumber !== 'N/A') {
                const autoGeneratedLink = `https://tiponet.tipo.gov.tw/gpss4/gpsskmc/gpssbkm?!!FRURL${publicationNumber}`;
                titleWithLink = `<a href="${autoGeneratedLink}" target="_blank" rel="noopener" style="color: #5a5859; text-decoration: none;">${Utils.escapeHtml(title)}</a>`;
            } else {
                titleWithLink = Utils.escapeHtml(title);
            }

            // 處理申請人
            let applicants = patent['申請人'] || patent.applicants || 'N/A';
            if (Array.isArray(applicants)) {
                applicants = applicants.join('; ');
            }
            if (!applicants || applicants === 'N/A' || applicants.trim() === '') {
                applicants = '申請人資訊待查';
            }

            // 處理摘要
            const abstract = patent['摘要'] || patent.abstract || '';
            const abstractHtml = abstract && abstract !== 'N/A' && abstract !== '暫無摘要資訊' ? 
                `<div class="patent-abstract">
                    <h4>● 專利摘要</h4>
                    <p>${Utils.escapeHtml(abstract)}</p>
                 </div>` : '';

            // 處理技術特徵和功效
            const features = patent['技術特徵'] || patent.technical_features || [];
            const effects = patent['技術功效'] || patent.technical_effects || [];
                 
            const featuresHtml = Array.isArray(features) ? 
                features.map(f => `<li>${Utils.escapeHtml(f)}</li>`).join('') :
                `<li>${Utils.escapeHtml(features)}</li>`;

            const effectsHtml = Array.isArray(effects) ? 
                effects.map(e => `<li>${Utils.escapeHtml(e)}</li>`).join('') :
                `<li>${Utils.escapeHtml(effects)}</li>`;

            return `
                <div class="patent-card">
                    <div class="patent-title">${index + 1}. ${titleWithLink}</div>
                    
                    <div class="patent-metadata">
                        <div class="metadata-item">
                            <span class="metadata-label">公告號:</span>
                            <span class="metadata-value">${publicationNumber}</span>
                        </div>
                        <div class="metadata-item">
                            <span class="metadata-label">申請人:</span>
                            <span class="metadata-value">${Utils.escapeHtml(applicants)}</span>
                        </div>
                    </div>
                    
                    ${abstractHtml}
                    
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
     * 導出搜索結果到Excel
     * @param {string} type - 搜索類型
     * @returns {Promise<void>}
     */
    async exportToExcel(type) {
        const results = this.searchResults[type];
        if (!results || !results.length) {
            throw new Error('沒有可匯出的資料');
        }

        // 準備匯出數據
        const exportData = results.map((patent, index) => {
            return {
                'No.': index + 1,
                '專利名稱': Utils.safeStringValue(patent['專利名稱'] || patent.title),
                '專利連結': Utils.safeStringValue(patent['專利連結'] || patent.patent_link || 
                    (patent['公開公告號'] || patent.publication_number ? 
                    `https://tiponet.tipo.gov.tw/gpss4/gpsskmc/gpssbkm?!!FRURL${patent['公開公告號'] || patent.publication_number}` : '')),
                '公開公告號': Utils.safeStringValue(patent['公開公告號'] || patent.publication_number),
                '申請人': Utils.safeStringValue(patent['申請人'] || patent.applicants),
                '國家': Utils.safeStringValue(patent['國家'] || patent.country),
                '摘要': Utils.safeTruncateText(patent['摘要'] || patent.abstract, 500),
                '專利範圍': Utils.safeTruncateText(patent['專利範圍'] || patent.claims, 500),
                '技術特徵': Utils.formatArrayField(patent['技術特徵'] || patent.technical_features || []),
                '技術功效': Utils.formatArrayField(patent['技術功效'] || patent.technical_effects || [])
            };
        });

        // 創建Excel文件
        const ws = XLSX.utils.json_to_sheet(exportData);
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, "專利檢索結果");

        // 設置列寬
        const colWidths = [
            { wch: 5 },   // No.
            { wch: 30 },  // 專利名稱
            { wch: 50 },  // 專利連結
            { wch: 15 },  // 公開公告號
            { wch: 20 },  // 申請人
            { wch: 8 },   // 國家
            { wch: 50 },  // 摘要
            { wch: 50 },  // 專利範圍
            { wch: 30 },  // 技術特徵
            { wch: 30 }   // 技術功效
        ];
        ws['!cols'] = colWidths;

        // 下載文件
        const fileName = `專利檢索結果_${type}_${Utils.formatDate(new Date(), 'YYYY-MM-DD')}.xlsx`;
        XLSX.writeFile(wb, fileName);
    }

    /**
     * 重置搜索狀態
     */
    reset() {
        this.generatedKeywords = [];
        this.currentSessionId = null;
        this.isSearching = false;
        this.searchResults = {
            tech: null,
            condition: null
        };
    }

    /**
     * 獲取當前搜索結果
     * @param {string} type - 搜索類型
     * @returns {Array} 搜索結果
     */
    getSearchResults(type) {
        return this.searchResults[type] || [];
    }

    /**
     * 檢查是否有搜索結果
     * @returns {boolean} 是否有結果
     */
    hasSearchResults() {
        return this.searchResults.tech || this.searchResults.condition;
    }
}

// 創建全局搜索管理器實例
const searchManager = new SearchManager();