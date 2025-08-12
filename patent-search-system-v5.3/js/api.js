/**
 * API功能模塊
 * 處理所有與後端API的通信
 */

class APIService {
    constructor(baseUrl = 'http://localhost:8005') {
        this.baseUrl = baseUrl;
        this.isConnected = false;
    }

    /**
     * 設置API基礎URL
     * @param {string} url - API基礎URL
     */
    setBaseUrl(url) {
        this.baseUrl = url;
    }

    /**
     * 通用的API請求方法
     * @param {string} endpoint - API端點
     * @param {Object} options - 請求選項
     * @returns {Promise<Object>} API響應
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        };

        const config = { ...defaultOptions, ...options };
        
        try {
            console.log(`🔍 API請求: ${config.method || 'GET'} ${url}`);
            if (config.body) {
                console.log('請求數據:', config.body);
            }

            const response = await fetch(url, config);
            
            console.log(`🔍 API響應狀態: ${response.status}`);

            if (!response.ok) {
                let errorDetail = '未知錯誤';
                try {
                    const errorData = await response.json();
                    console.error('🔍 API錯誤詳情:', errorData);
                    errorDetail = errorData.detail || errorData.message || `HTTP ${response.status}`;
                } catch (e) {
                    errorDetail = `HTTP ${response.status}: ${response.statusText}`;
                }
                throw new Error(errorDetail);
            }

            const data = await response.json();
            console.log('🔍 API響應數據:', data);
            return data;

        } catch (error) {
            console.error(`API請求失敗 (${endpoint}):`, error);
            throw error;
        }
    }

    /**
     * 測試API連接
     * @returns {Promise<boolean>} 連接狀態
     */
    async testConnection() {
        try {
            const response = await this.request('/ping');
            this.isConnected = true;
            return true;
        } catch (error) {
            this.isConnected = false;
            throw error;
        }
    }

    /**
     * 測試專利API
     * @returns {Promise<boolean>} 測試結果
     */
    async testPatentAPI() {
        try {
            const response = await this.request('/api/v1/patents/test/ping');
            return response.success || true;
        } catch (error) {
            console.warn('專利API測試失敗:', error);
            throw error;
        }
    }

    /**
     * 測試GPSS API
     * @param {string} userCode - 用戶API碼
     * @returns {Promise<Object>} 測試結果
     */
    async testGPSS(userCode) {
        try {
            const response = await this.request('/api/v1/patents/test/gpss', {
                method: 'POST',
                body: JSON.stringify({ user_code: userCode })
            });
            return response;
        } catch (error) {
            console.error('GPSS API測試失敗:', error);
            throw error;
        }
    }

    /**
     * 生成關鍵字
     * @param {string} description - 技術描述
     * @param {string} sessionId - 會話ID
     * @returns {Promise<Object>} 關鍵字生成結果
     */
    async generateKeywords(description, sessionId) {
        try {
            const response = await this.request('/api/v1/patents/keywords/generate-for-confirmation', {
                method: 'POST',
                body: JSON.stringify({
                    description: description,
                    session_id: sessionId
                })
            });
            return response;
        } catch (error) {
            console.error('關鍵字生成失敗:', error);
            throw error;
        }
    }

    /**
     * 確認關鍵字並搜索
     * @param {Object} searchData - 搜索數據
     * @returns {Promise<Object>} 搜索結果
     */
    async confirmKeywordsAndSearch(searchData) {
        try {
            const response = await this.request('/api/v1/patents/search/tech-description-confirmed', {
                method: 'POST',
                body: JSON.stringify(searchData)
            });
            return response;
        } catch (error) {
            console.error('關鍵字確認搜索失敗:', error);
            throw error;
        }
    }

    /**
     * 使用同義詞搜索
     * @param {Object} searchData - 搜索數據
     * @returns {Promise<Object>} 搜索結果
     */
    async searchWithSynonyms(searchData) {
        try {
            const response = await this.request('/api/v1/patents/search/tech-description-with-synonyms', {
                method: 'POST',
                body: JSON.stringify(searchData)
            });
            return response;
        } catch (error) {
            console.error('同義詞搜索失敗:', error);
            throw error;
        }
    }

    /**
     * 條件搜索
     * @param {Object} searchParams - 搜索參數
     * @returns {Promise<Object>} 搜索結果
     */
    async conditionSearch(searchParams) {
        try {
            const response = await this.request('/api/v1/patents/condition/search', {
                method: 'POST',
                body: JSON.stringify(searchParams)
            });
            return response;
        } catch (error) {
            console.error('條件搜索失敗:', error);
            throw error;
        }
    }

    /**
     * 上傳並分析Excel文件
     * @param {File} file - Excel文件
     * @returns {Promise<Object>} 分析結果
     */
    async uploadAndAnalyzeExcel(file) {
        try {
            const formData = new FormData();
            formData.append('file', file);

            // 對於文件上傳，不設置Content-Type，讓瀏覽器自動設置
            const response = await fetch(`${this.baseUrl}/api/v1/patents/excel/upload-and-analyze`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => null);
                throw new Error(errorData?.detail || `HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Excel上傳分析失敗:', error);
            throw error;
        }
    }

    /**
     * 導出分析結果
     * @param {Object} exportData - 導出數據
     * @returns {Promise<Blob>} Excel文件Blob
     */
    async exportAnalysisResults(exportData) {
        try {
            const response = await fetch(`${this.baseUrl}/api/v1/patents/excel/export-analysis-results`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(exportData)
            });

            if (!response.ok) {
                throw new Error('導出失敗');
            }

            const blob = await response.blob();
            return {
                blob: blob,
                filename: response.headers.get('Content-Disposition')?.split('filename=')[1] || 'analysis_results.xlsx'
            };
        } catch (error) {
            console.error('導出分析結果失敗:', error);
            throw error;
        }
    }

    /**
     * 發送簡單問答請求
     * @param {string} sessionId - 會話ID
     * @param {string} question - 問題
     * @returns {Promise<Object>} 回答結果
     */
    async askSimpleQuestion(sessionId, question) {
        try {
            const response = await this.request('/api/v1/patents/qa/ask-simple', {
                method: 'POST',
                body: JSON.stringify({
                    session_id: sessionId,
                    question: question,
                    use_memory: false
                })
            });
            return response;
        } catch (error) {
            console.error('簡單問答失敗:', error);
            throw error;
        }
    }

    /**
     * 發送帶記憶的問答請求
     * @param {string} sessionId - 會話ID
     * @param {string} question - 問題
     * @returns {Promise<Object>} 回答結果
     */
    async askWithMemory(sessionId, question) {
        try {
            const response = await this.request('/api/v1/patents/qa/ask-with-memory', {
                method: 'POST',
                body: JSON.stringify({
                    session_id: sessionId,
                    question: question,
                    use_memory: true
                })
            });
            return response;
        } catch (error) {
            console.error('記憶問答失敗:', error);
            throw error;
        }
    }

    /**
     * 獲取記憶狀態
     * @param {string} sessionId - 會話ID
     * @returns {Promise<Object>} 記憶狀態
     */
    async getMemoryStatus(sessionId) {
        try {
            const response = await this.request(`/api/v1/patents/qa/memory-status/${sessionId}`);
            return response;
        } catch (error) {
            console.error('獲取記憶狀態失敗:', error);
            throw error;
        }
    }

    /**
     * 獲取對話歷史
     * @param {string} sessionId - 會話ID
     * @param {number} limit - 限制數量
     * @returns {Promise<Object>} 對話歷史
     */
    async getChatHistory(sessionId, limit = 20) {
        try {
            const response = await this.request(`/api/v1/patents/qa/history/${sessionId}?limit=${limit}`);
            return response;
        } catch (error) {
            console.error('獲取對話歷史失敗:', error);
            throw error;
        }
    }

    /**
     * 清除對話記憶
     * @param {string} sessionId - 會話ID
     * @returns {Promise<Object>} 清除結果
     */
    async clearChatMemory(sessionId) {
        try {
            const response = await this.request('/api/v1/patents/qa/clear-memory', {
                method: 'POST',
                body: JSON.stringify({
                    session_id: sessionId
                })
            });
            return response;
        } catch (error) {
            console.error('清除對話記憶失敗:', error);
            throw error;
        }
    }

    /**
     * 批量API請求
     * @param {Array} requests - 請求列表
     * @returns {Promise<Array>} 批量結果
     */
    async batchRequest(requests) {
        try {
            const promises = requests.map(req => this.request(req.endpoint, req.options));
            const results = await Promise.allSettled(promises);
            
            return results.map((result, index) => ({
                index: index,
                success: result.status === 'fulfilled',
                data: result.status === 'fulfilled' ? result.value : null,
                error: result.status === 'rejected' ? result.reason : null
            }));
        } catch (error) {
            console.error('批量請求失敗:', error);
            throw error;
        }
    }

    /**
     * 重試機制的API請求
     * @param {string} endpoint - API端點
     * @param {Object} options - 請求選項
     * @param {number} maxRetries - 最大重試次數
     * @param {number} delay - 重試延遲
     * @returns {Promise<Object>} API響應
     */
    async requestWithRetry(endpoint, options = {}, maxRetries = 3, delay = 1000) {
        let lastError;
        
        for (let i = 0; i <= maxRetries; i++) {
            try {
                return await this.request(endpoint, options);
            } catch (error) {
                lastError = error;
                
                if (i === maxRetries) {
                    throw error;
                }
                
                console.warn(`API請求失敗，${delay}ms後重試 (${i + 1}/${maxRetries}):`, error.message);
                await Utils.delay(delay);
                delay *= 2; // 指數退避
            }
        }
        
        throw lastError;
    }

    /**
     * 檢查API狀態
     * @returns {Promise<Object>} 狀態信息
     */
    async getStatus() {
        try {
            const response = await this.request('/api/v1/status');
            return response;
        } catch (error) {
            console.error('獲取API狀態失敗:', error);
            throw error;
        }
    }

    /**
     * 獲取API版本信息
     * @returns {Promise<Object>} 版本信息
     */
    async getVersion() {
        try {
            const response = await this.request('/api/v1/version');
            return response;
        } catch (error) {
            console.error('獲取API版本失敗:', error);
            throw error;
        }
    }
}

// 創建全局API服務實例
const apiService = new APIService();