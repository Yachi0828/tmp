/**
 * 工具函數模塊
 * 包含通用的工具方法和輔助函數
 */

class Utils {
    /**
     * 生成唯一的會話ID
     */
    static generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * 根據主機名判斷API地址
     */
    static determineApiUrl() {
        const hostname = window.location.hostname;
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            return 'http://localhost:8005';
        }
        return window.location.origin;
    }

    /**
     * 提取錯誤訊息
     * @param {*} error - 錯誤對象
     * @returns {string} 錯誤訊息
     */
    static extractErrorMessage(error) {
        if (typeof error === 'string') {
            return error;
        }
        
        if (error instanceof Error) {
            return error.message;
        }
        
        if (error && typeof error === 'object') {
            if (error.detail) {
                return typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail);
            }
            if (error.message) {
                return error.message;
            }
            if (error.error) {
                return typeof error.error === 'string' ? error.error : JSON.stringify(error.error);
            }
            if (error.status && error.statusText) {
                return `HTTP ${error.status}: ${error.statusText}`;
            }
            try {
                return JSON.stringify(error);
            } catch (e) {
                return '未知錯誤';
            }
        }
        
        return '未知錯誤類型';
    }

    /**
     * HTML轉義
     * @param {string} text - 要轉義的文本
     * @returns {string} 轉義後的HTML
     */
    static escapeHtml(text) {
        if (!text) return 'N/A';
        if (typeof text !== 'string') return String(text);
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 安全的字符串值處理
     * @param {*} value - 要處理的值
     * @returns {string} 安全的字符串值
     */
    static safeStringValue(value) {
        if (value === null || value === undefined) return 'N/A';
        if (typeof value === 'string') return value || 'N/A';
        if (Array.isArray(value)) return value.join('; ') || 'N/A';
        return String(value) || 'N/A';
    }

    /**
     * 安全截斷文本
     * @param {string} value - 要截斷的文本
     * @param {number} maxLength - 最大長度
     * @returns {string} 截斷後的文本
     */
    static safeTruncateText(value, maxLength) {
        const str = Utils.safeStringValue(value);
        if (str === 'N/A') return str;
        if (str.length <= maxLength) return str;
        return str.substring(0, maxLength - 3) + '...';
    }

    /**
     * 格式化數組字段
     * @param {Array} arr - 數組
     * @returns {string} 格式化後的字符串
     */
    static formatArrayField(arr) {
        if (!Array.isArray(arr)) return arr || '';
        return arr.join('; ');
    }

    /**
     * 獲取國家標誌
     * @param {string} country - 國家代碼
     * @returns {string} 國家標誌
     */
    static getCountryFlag(country) {
        const flagMap = {
            'TW': ':',
            'US': ':', 
            'JP': ':',
            'EP': ':',
            'KR': ':',
            'CN': ':',
            'WO': ':',
            'SEA': ':',
        };
        return flagMap[country] || 'N/A';
    }

    /**
     * 獲取國家名稱
     * @param {string} country - 國家代碼
     * @returns {string} 國家名稱
     */
    static getCountryName(country) {
        const nameMap = {
            'TW': 'TW',
            'US': 'US',
            'JP': 'JP',
            'EP': 'EP',
            'KR': 'KR',
            'CN': 'CN',
            'WO': 'WO',
            'SEA': 'SEA',
        };
        return nameMap[country] || country;
    }

    /**
     * 延遲執行
     * @param {number} ms - 延遲毫秒數
     * @returns {Promise} Promise對象
     */
    static delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * 防抖函數
     * @param {Function} func - 要防抖的函數
     * @param {number} wait - 等待時間
     * @returns {Function} 防抖後的函數
     */
    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * 節流函數
     * @param {Function} func - 要節流的函數
     * @param {number} limit - 限制時間
     * @returns {Function} 節流後的函數
     */
    static throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    /**
     * 深度克隆對象
     * @param {*} obj - 要克隆的對象
     * @returns {*} 克隆後的對象
     */
    static deepClone(obj) {
        if (obj === null || typeof obj !== 'object') return obj;
        if (obj instanceof Date) return new Date(obj.getTime());
        if (obj instanceof Array) return obj.map(item => Utils.deepClone(item));
        if (typeof obj === 'object') {
            const clonedObj = {};
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    clonedObj[key] = Utils.deepClone(obj[key]);
                }
            }
            return clonedObj;
        }
    }

    /**
     * 驗證電子郵件格式
     * @param {string} email - 電子郵件地址
     * @returns {boolean} 是否有效
     */
    static isValidEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }

    /**
     * 驗證URL格式
     * @param {string} url - URL地址
     * @returns {boolean} 是否有效
     */
    static isValidUrl(url) {
        try {
            new URL(url);
            return true;
        } catch (e) {
            return false;
        }
    }

    /**
     * 格式化日期
     * @param {Date|string} date - 日期對象或字符串
     * @param {string} format - 格式字符串
     * @returns {string} 格式化後的日期
     */
    static formatDate(date, format = 'YYYY-MM-DD') {
        const d = new Date(date);
        if (isNaN(d.getTime())) return 'Invalid Date';
        
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        const hours = String(d.getHours()).padStart(2, '0');
        const minutes = String(d.getMinutes()).padStart(2, '0');
        const seconds = String(d.getSeconds()).padStart(2, '0');
        
        return format
            .replace('YYYY', year)
            .replace('MM', month)
            .replace('DD', day)
            .replace('HH', hours)
            .replace('mm', minutes)
            .replace('ss', seconds);
    }

    /**
     * 獲取文件擴展名
     * @param {string} filename - 文件名
     * @returns {string} 文件擴展名
     */
    static getFileExtension(filename) {
        return filename.split('.').pop().toLowerCase();
    }

    /**
     * 格式化文件大小
     * @param {number} bytes - 字節數
     * @returns {string} 格式化後的文件大小
     */
    static formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * 獲取隨機顏色
     * @returns {string} 十六進制顏色代碼
     */
    static getRandomColor() {
        return '#' + Math.floor(Math.random()*16777215).toString(16);
    }

    /**
     * 檢查是否為移動設備
     * @returns {boolean} 是否為移動設備
     */
    static isMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }

    /**
     * 獲取瀏覽器信息
     * @returns {Object} 瀏覽器信息
     */
    static getBrowserInfo() {
        const ua = navigator.userAgent;
        let browser = 'Unknown';
        
        if (ua.indexOf('Chrome') > -1) browser = 'Chrome';
        else if (ua.indexOf('Firefox') > -1) browser = 'Firefox';
        else if (ua.indexOf('Safari') > -1) browser = 'Safari';
        else if (ua.indexOf('Edge') > -1) browser = 'Edge';
        else if (ua.indexOf('Opera') > -1) browser = 'Opera';
        
        return {
            browser: browser,
            userAgent: ua,
            isMobile: Utils.isMobile()
        };
    }

    /**
     * 複製文本到剪貼板
     * @param {string} text - 要複製的文本
     * @returns {Promise<boolean>} 是否成功
     */
    static async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            // 備用方法
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            const success = document.execCommand('copy');
            document.body.removeChild(textArea);
            return success;
        }
    }

    /**
     * 本地存儲工具
     */
    static storage = {
        /**
         * 設置本地存儲
         * @param {string} key - 鍵
         * @param {*} value - 值
         */
        set(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
            } catch (e) {
                console.warn('LocalStorage set failed:', e);
            }
        },

        /**
         * 獲取本地存儲
         * @param {string} key - 鍵
         * @param {*} defaultValue - 默認值
         * @returns {*} 存儲的值
         */
        get(key, defaultValue = null) {
            try {
                const item = localStorage.getItem(key);
                return item ? JSON.parse(item) : defaultValue;
            } catch (e) {
                console.warn('LocalStorage get failed:', e);
                return defaultValue;
            }
        },

        /**
         * 移除本地存儲
         * @param {string} key - 鍵
         */
        remove(key) {
            try {
                localStorage.removeItem(key);
            } catch (e) {
                console.warn('LocalStorage remove failed:', e);
            }
        },

        /**
         * 清空本地存儲
         */
        clear() {
            try {
                localStorage.clear();
            } catch (e) {
                console.warn('LocalStorage clear failed:', e);
            }
        }
    };
}