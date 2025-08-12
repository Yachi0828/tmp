# KYEC-專利檢索系統

一個基於AI的智能專利檢索系統，支持技術描述查詢、條件查詢和Excel批量分析，並提供智能問答功能。

## 🌟 主要功能

### 1. 技術描述查詢
- 輸入技術描述，自動生成關鍵字
- 支持拖拉式關鍵字組合
- 一鍵檢索和手動檢索模式
- 智能同義詞擴展

### 2. 條件查詢
- 申請人、發明人、專利號查詢
- IPC分類和日期範圍篩選
- 多欄位組合查詢

### 3. Excel批量分析
- 上傳Excel文件批量分析專利
- 自動生成技術特徵和功效
- 支持.xlsx和.xls格式

### 4. 智能問答 🎃
- 基於QWEN的AI問答系統
- 支持對話記憶功能
- 針對專利內容的智能分析

## 📁 項目結構

```
patent-search-system/
├── index.html                 # 主頁面
├── css/
│   └── styles.css             # 主要樣式文件
├── js/
│   ├── utils.js               # 工具函數
│   ├── api.js                 # API通信模塊
│   ├── ui.js                  # UI管理模塊
│   ├── search.js              # 搜索功能模塊
│   ├── chat.js                # 聊天功能模塊
│   ├── excel.js               # Excel分析模塊
│   └── app.js                 # 主應用程序
├── static/                    # 靜態資源
│   ├── icon_ceV2.ico          # 聊天圖標
│   ├── iconmonstr-idea-11-240.png
│   ├── iconmonstr-time-17-240.png
│   └── iconmonstr-trash-can-27-240.png
└── README.md                  # 項目說明
```

## 🚀 快速開始

### 前端部署

1. **部署文件**
   ```bash
   # 將所有文件上傳到Web服務器
   # 確保目錄結構正確
   ```

2. **配置API地址**
   - 在`js/api.js`中修改默認API地址
   - 或在界面中設置API地址

3. **獲取GPSS API密鑰**
   - 訪問[智慧財產局API申請](https://tiponet.tipo.gov.tw/gpss1/gpsskmc/gpssapi?@@0.532614314057245)
   - 申請GPSS API驗證碼

### 系統需求

- **瀏覽器**: Chrome, Firefox, Safari, Edge (最新版本)
- **網絡**: 需要連接到後端API服務
- **文件大小**: Excel文件最大10MB

## 🔧 後端API需求

系統需要後端API提供以下端點：

### 基礎服務
```
GET  /ping                                    # 健康檢查
GET  /api/v1/patents/test/ping               # 專利服務測試
POST /api/v1/patents/test/gpss               # GPSS API測試
```

### 關鍵字和搜索
```
POST /api/v1/patents/keywords/generate-for-confirmation    # 生成關鍵字
POST /api/v1/patents/search/tech-description-confirmed     # 確認關鍵字搜索
POST /api/v1/patents/search/tech-description-with-synonyms # 同義詞搜索
POST /api/v1/patents/condition/search                      # 條件搜索
```

### Excel分析
```
POST /api/v1/patents/excel/upload-and-analyze        # 上傳分析Excel
POST /api/v1/patents/excel/export-analysis-results   # 導出分析結果
```

### 智能問答
```
POST /api/v1/patents/qa/ask-simple                   # 簡單問答
POST /api/v1/patents/qa/ask-with-memory               # 記憶問答
GET  /api/v1/patents/qa/memory-status/{session_id}   # 記憶狀態
GET  /api/v1/patents/qa/history/{session_id}         # 對話歷史
POST /api/v1/patents/qa/clear-memory                 # 清除記憶
```

### 請求格式示例

#### 技術描述搜索請求
```json
{
  "session_id": "session_123456",
  "description": "自動化晶圓探針台系統，具備精密定位控制...",
  "generated_keywords": ["晶圓", "探針台", "自動化"],
  "selected_keywords": ["晶圓", "探針台", "定位控制"],
  "custom_keywords": [],
  "user_code": "YOUR_GPSS_API_KEY",
  "max_results": 1000,
  "use_and_or_logic": false
}
```

#### 智能問答請求
```json
{
  "session_id": "session_123456",
  "question": "這些專利中哪個技術最先進？",
  "use_memory": true
}
```

## 🎨 界面功能

### 側邊欄設定
- GPSS API設定和驗證
- 專利全文查詢
- API連接設定
- 服務狀態監控

### 主要功能區
- **技術描述查詢**: 關鍵字生成和拖拉式搜索
- **條件查詢**: 多欄位組合搜索
- **資料分析**: Excel文件批量處理

### 智能問答
- 側邊聊天面板
- 對話記憶功能
- 歷史記錄查看
- 記憶管理

## 🔧 技術特性

### 前端技術
- **原生JavaScript**: 模塊化架構
- **響應式設計**: 支持移動設備
- **拖拉功能**: 直觀的關鍵字操作
- **進度追蹤**: 實時操作反饋

### 核心模塊

#### 1. Utils.js - 工具函數
- 字符串處理和驗證
- 日期格式化
- 本地存儲管理
- 通用輔助函數

#### 2. API.js - API通信
- RESTful API封裝
- 請求重試機制
- 錯誤處理
- 文件上傳支持

#### 3. UI.js - 界面管理
- DOM操作封裝
- 進度條動畫
- 消息提示
- 模態框管理

#### 4. Search.js - 搜索功能
- 關鍵字生成
- 拖拉操作
- 搜索邏輯構建
- 結果渲染

#### 5. Chat.js - 聊天功能
- QWEN AI集成
- 對話記憶
- 歷史管理
- 狀態追蹤

#### 6. Excel.js - 文件處理
- 文件驗證
- 上傳進度
- 結果分析
- 導出功能

## 🔐 安全考慮

- API密鑰本地存儲（localStorage）
- HTTPS通信建議
- 文件大小和類型驗證
- XSS防護（HTML轉義）

## 📊 使用統計

系統支持以下統計功能：
- 搜索次數追蹤
- API調用監控
- 錯誤日誌記錄
- 性能指標收集

## 🛠️ 開發說明

### 調試功能
```javascript
// 查看系統狀態
window.patentSearchApp.showStatus()

// 查看模塊狀態
console.log(searchManager.getSearchResults('tech'))
console.log(chatManager.getChatHistory())
console.log(excelManager.getAnalysisStats())
```

### 自定義配置
```javascript
// 修改API地址
apiService.setBaseUrl('https://your-api-server.com')

// 設置會話ID
searchManager.setSessionId('custom-session-id')
chatManager.setSessionId('custom-session-id')
```

## 📋 後端實現建議

### 技術堆疊
- **API框架**: FastAPI (Python) 或 Express.js (Node.js)
- **AI模型**: Qwen 2.5 (通義千問)
- **數據庫**: PostgreSQL + Redis (對話記憶)
- **文件處理**: pandas, openpyxl
- **專利API**: GPSS (政府專利搜索服務)

### 核心功能實現

#### 1. 關鍵字生成
```python
# 使用Qwen模型生成關鍵字
async def generate_keywords(description: str):
    prompt = f"根據以下技術描述生成5個專利搜索關鍵字：{description}"
    keywords = await qwen_client.chat(prompt)
    return process_keywords(keywords)
```

#### 2. 專利搜索
```python
# 調用GPSS API進行專利搜索
async def search_patents(keywords: List[str], user_code: str):
    gpss_query = build_gpss_query(keywords)
    results = await gpss_client.search(gpss_query, user_code)
    return process_patent_results(results)
```

#### 3. 智能問答
```python
# 基於搜索結果的問答
async def answer_question(question: str, session_id: str, use_memory: bool):
    context = await get_search_context(session_id)
    if use_memory:
        history = await get_conversation_history(session_id)
        context += format_conversation_context(history)
    
    answer = await qwen_client.chat(question, context=context)
    await save_conversation(session_id, question, answer)
    return answer
```

## 📞 支援聯繫

如有技術問題或建議，請聯繫開發團隊。

## 📄 授權聲明

本項目為內部使用系統，請遵守相關使用條款和隱私政策。

---

**版本**: v2.0  
**更新日期**: 2024年12月  
**開發團隊**: KYEC專利檢索小組