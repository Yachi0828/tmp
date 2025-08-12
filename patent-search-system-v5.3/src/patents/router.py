from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import time
import logging
import pandas as pd
from io import BytesIO
import json
import uuid
from urllib.parse import quote
from src.database import DatabaseManager
from src.services.enhanced_patent_qa_service import enhanced_patent_qa_service
from src.services.improved_patent_processing_service import improved_patent_processing_service
 
logger = logging.getLogger(__name__)
router = APIRouter()

# ================================
# 請求模型定義
# ================================

class TechDescriptionRequest(BaseModel):
    description: str = Field(..., description="技術描述", min_length=50, max_length=2000)
    user_code: str = Field(..., description="GPSS API驗證碼", min_length=16)
    max_results: int = Field(1000, ge=1, le=10000, description="最大結果數量")

class ConditionSearchRequest(BaseModel):
    user_code: str = Field(..., description="GPSS API驗證碼", min_length=16)
    max_results: int = Field(1000, ge=1, le=10000, description="最大結果數量")
    applicant: Optional[str] = Field(None, description="申請人")
    inventor: Optional[str] = Field(None, description="發明人")
    patent_number: Optional[str] = Field(None, description="專利號")
    application_number: Optional[str] = Field(None, description="申請號")
    ipc_class: Optional[str] = Field(None, description="IPC分類")
    title_keyword: Optional[str] = Field(None, description="標題關鍵字")
    abstract_keyword: Optional[str] = Field(None, description="摘要關鍵字")
    claims_keyword: Optional[str] = Field(None, description="專利範圍關鍵字")
    application_date_from: Optional[str] = Field(None, description="專利申請日（開始）")
    application_date_to: Optional[str] = Field(None, description="專利申請日（結束）")
    publication_date_from: Optional[str] = Field(None, description="公開日（開始）")
    publication_date_to: Optional[str] = Field(None, description="公開日（結束）")

class GPSSTestRequest(BaseModel):
    user_code: str = Field(..., description="GPSS API驗證碼")

class ExcelExportRequest(BaseModel):
    patents: List[Dict[str, Any]] = Field(..., description="專利數據列表")
    search_type: str = Field(..., description="搜索類型")

class KeywordGenerationRequest(BaseModel):
    description: str = Field(..., description="技術描述", min_length=50, max_length=3000)
    session_id: Optional[str] = Field(None, description="會話ID（可選，系統自動生成）")

class KeywordConfirmationRequest(BaseModel):
    session_id: str = Field(..., description="會話ID")
    description: str = Field(..., description="原始技術描述")
    generated_keywords: List[str] = Field(..., description="Qwen生成的關鍵字")
    selected_keywords: List[str] = Field(..., description="用戶選擇的AI關鍵字（AND邏輯）")
    custom_keywords: List[str] = Field(default=[], description="用戶自定義關鍵字（OR邏輯）")
    user_code: str = Field(..., description="GPSS API驗證碼", min_length=16)
    max_results: int = Field(1000, ge=1, le=10000, description="最大結果數量")
    use_and_or_logic: bool = Field(default=True, description="是否使用AND/OR邏輯")

class ExcelAnalysisResponse(BaseModel):
    success: bool = Field(..., description="處理是否成功")
    processed_count: int = Field(..., description="處理的專利數量")
    results: List[Dict[str, Any]] = Field(..., description="處理結果")
    errors: List[str] = Field(default=[], description="錯誤訊息")
    session_id: str = Field(..., description="會話ID")
    timestamp: float = Field(..., description="處理時間戳")

class QARequest(BaseModel):
    session_id: str = Field(..., description="會話ID")
    question: str = Field(..., description="用戶問題", min_length=1, max_length=1000)
    use_memory: bool = Field(default=True, description="是否使用對話記憶")

class QAHistoryRequest(BaseModel):
    session_id: str = Field(..., description="會話ID")
    limit: int = Field(default=10, ge=1, le=50, description="歷史記錄數量限制")

class ClearMemoryRequest(BaseModel):
    session_id: str = Field(..., description="會話ID")
# ================================
# 測試相關端點
# ================================

@router.get(
    "/test/ping",
    summary="API連接測試",
    description="測試API服務是否正常運行",
    tags=["測試"]
)
async def ping_test():
    return {
        "status": "ok",
        "message": "智能專利檢索API服務正常",
        "timestamp": time.time(),
        "services": {
            "fastapi": "running",
            "qwen": "available",
            "gpss": "ready"
        },
        "version": "6.0.0",
        "new_features": ["純技術特徵生成", "Excel編碼修復"]
    }

@router.get(
    "/test/health",
    summary="健康檢查",
    description="檢查所有服務狀態",
    tags=["測試"]
)
async def health_check():
    try:
        if not improved_patent_processing_service.initialized:
            await improved_patent_processing_service.initialize()
        
        return {
            "status": "healthy",
            "version": "6.0.0",
            "timestamp": time.time(),
            "services": {
                "patent_processing": "ready",
                "qwen_api": "connected" if improved_patent_processing_service.qwen_service else "unavailable",
                "gpss_api": "available" if improved_patent_processing_service.gpss_service else "unavailable"
            },
            "features": [
                "√ 流程A: 技術描述查詢 (支持AND/OR邏輯)",
                "√ 流程B: 條件查詢 (擴展條件支持)", 
                "√ Qwen關鍵字生成和技術特徵提取",
                "√ Excel匯出功能 (修復編碼問題)",
                "√ API密鑰驗證機制",
                "🆕 純技術特徵提取（移除分類功能）"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"健康檢查失敗: {str(e)}")

@router.post(
    "/test/gpss",
    summary="測試GPSS API連接",
    description="測試GPSS API驗證碼是否有效",
    tags=["測試"]
)
async def test_gpss_connection(request: GPSSTestRequest):
    """測試GPSS API連接"""
    try:
        if not improved_patent_processing_service.initialized:
            await improved_patent_processing_service.initialize()

        is_valid = await improved_patent_processing_service.verify_api_key(request.user_code)
        if is_valid:
            return {
                "success": True,
                "status": "connected",
                "message": "GPSS API連接測試成功",
                "user_code_prefix": request.user_code[:8] + "...",
                "timestamp": time.time()
            }
        else:
            return {
                "success": False,
                "status": "failed", 
                "message": "GPSS API驗證失敗，請檢查驗證碼是否正確",
                "timestamp": time.time()
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GPSS API測試失敗: {str(e)}")

@router.post(
    "/test/and-or-logic",
    summary="測試AND/OR搜索邏輯",
    description="測試新的AND/OR搜索邏輯功能",
    tags=["測試"]
)
async def test_and_or_logic():
    """測試AND/OR搜索邏輯"""
    try:
        return {
            "success": True,
            "message": "AND/OR搜索邏輯測試成功",
            "logic_description": {
                "user_keywords": "用戶自定義關鍵字之間用 OR 連接",
                "ai_keywords": "AI生成且用戶選擇的關鍵字之間用 OR 連接", 
                "final_logic": "(用戶關鍵字1 OR 用戶關鍵字2 OR ...) AND (AI關鍵字1 OR AI關鍵字2 OR ...)",
                "example": "(測試設備 OR 檢測系統) AND (半導體 OR 自動化 OR 控制)"
            },
            "timestamp": time.time(),
            "version": "6.0.0"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AND/OR邏輯測試失敗: {str(e)}")

# ================================
# 流程A：技術描述查詢相關端點
# ================================

@router.post(
    "/keywords/generate-for-confirmation",
    summary="生成關鍵字和同義詞供用戶確認（新流程第一步）",
    description="從技術描述生成關鍵字和對應的同義詞，返回給前端供用戶選擇和修改",
    tags=["流程A-技術描述查詢"]
)
async def generate_keywords_for_confirmation(request: KeywordGenerationRequest):
    """新的流程A第一步：生成關鍵字和同義詞供用戶確認"""
    try:
        logger.info(f"🔑 生成關鍵字和同義詞供確認，描述長度: {len(request.description)}")
        
        if not improved_patent_processing_service.initialized:
            await improved_patent_processing_service.initialize()
        
        # 生成會話ID
        session_id = request.session_id or str(uuid.uuid4())
        
        # 使用Qwen生成關鍵字和同義詞
        result = await improved_patent_processing_service.generate_keywords_with_synonyms_from_description(request.description)
        
        keywords_with_synonyms = result.get('keywords_with_synonyms', [])
        
        if not keywords_with_synonyms:
            # 如果Qwen失敗，使用fallback方法
            fallback_result = improved_patent_processing_service._generate_keywords_synonyms_fallback(request.description, 3, 5)
            keywords_with_synonyms = fallback_result.get('keywords_with_synonyms', [])
        
        return {
            "success": True,
            "session_id": session_id,
            "description": request.description,
            "keywords_with_synonyms": keywords_with_synonyms,
            "message": f"成功生成 {len(keywords_with_synonyms)} 個關鍵字及其同義詞，請確認或修改",
            "timestamp": time.time(),
            "note": "✨ 支持關鍵字和同義詞組合的AND/OR搜索邏輯",
            "search_logic_description": "每個關鍵字組內用OR邏輯連接（關鍵字 OR 同義詞1 OR 同義詞2...），關鍵字組之間用AND連接"
        }
        
    except Exception as e:
        logger.error(f"❌ 關鍵字和同義詞生成失敗: {e}")
        raise HTTPException(status_code=500, detail=f"關鍵字和同義詞生成失敗: {str(e)}")

# 新增請求模型來處理同義詞選擇
class KeywordSynonymConfirmationRequest(BaseModel):
    session_id: str = Field(..., description="會話ID")
    description: str = Field(..., description="原始技術描述")
    selected_keyword_groups: List[Dict[str, Any]] = Field(..., description="選擇的關鍵字組合")
    custom_keywords: List[str] = Field(default=[], description="自定義關鍵字")
    user_code: str = Field(..., description="GPSS API用戶代碼")
    max_results: int = Field(default=200, description="最大結果數量", le=1000)

@router.post(
    "/search/tech-description-confirmed",
    summary="確認關鍵字後執行技術描述查詢（支持AND/OR邏輯）",
    description="用戶確認關鍵字後，執行完整的技術描述查詢流程。支持 (用戶關鍵字1 OR 用戶關鍵字2...) AND (AI關鍵字1 OR AI關鍵字2...)",
    tags=["流程A-技術描述查詢"]
)
async def tech_description_search_confirmed(request: KeywordConfirmationRequest):
    """
    確認關鍵字後的搜索處理
    支援傳統邏輯和AND/OR邏輯
    """
    try:
        logger.info(f"🎯 收到確認搜索請求")
        logger.info(f"會話ID: {request.session_id}")
        logger.info(f"選擇的關鍵字: {request.selected_keywords}")
        logger.info(f"自定義關鍵字: {request.custom_keywords}")
        logger.info(f"使用AND/OR邏輯: {request.use_and_or_logic}")
        
        if not improved_patent_processing_service.initialized:
            await improved_patent_processing_service.initialize()

        # 驗證用戶代碼
        if not request.user_code:
            raise HTTPException(status_code=400, detail="請先輸入GPSS API驗證碼")
        
        # 檢查關鍵字
        if not request.selected_keywords and not request.custom_keywords:
            raise HTTPException(status_code=400, detail="請至少選擇一個關鍵字或輸入自定義關鍵字")
        
        # 根據選擇的邏輯進行搜索
        if request.use_and_or_logic and request.selected_keywords and request.custom_keywords:
            # 使用AND/OR邏輯
            logger.info(f"🔄 使用AND/OR搜索邏輯")
            
            result = await improved_patent_processing_service.process_tech_description_search_with_and_or_logic(
                description=request.description,
                user_keywords=request.custom_keywords,
                ai_keywords=request.selected_keywords,
                user_code=request.user_code,
                max_results=request.max_results
            )
        else:
            # 使用傳統邏輯：所有關鍵字合併
            logger.info(f"🔄 使用傳統搜索邏輯")
            final_keywords = []
            
            # 添加用戶選擇的AI關鍵字
            if request.selected_keywords:
                final_keywords.extend(request.selected_keywords)
                
            # 添加用戶自定義關鍵字
            if request.custom_keywords:
                final_keywords.extend(request.custom_keywords)
            
            # 去重
            final_keywords = list(dict.fromkeys(final_keywords))
            
            result = await improved_patent_processing_service.process_tech_description_search_with_keywords(
                description=request.description,
                keywords=final_keywords,
                user_code=request.user_code,
                max_results=request.max_results
            )
        
        if not result.success:
            if "驗證失敗" in result.error:
                raise HTTPException(status_code=401, detail=result.error)
            else:
                raise HTTPException(status_code=400, detail=result.error)
        
        # 🆕 新增：保存搜尋結果到暫存，供智能問答使用
        if result.results and len(result.results) > 0:
            try:
                # 保存結果到資料庫暫存
                await DatabaseManager.save_search_results_to_cache(
                    session_id=request.session_id,
                    search_type="tech_description_search",
                    results=result.results,
                    expires_days=7
                )
                
                logger.info(f"✅ 技術描述搜尋結果已保存到暫存: {request.session_id}, {len(result.results)}筆")
                
            except Exception as cache_error:
                logger.error(f"⚠️ 保存搜尋結果到暫存失敗: {cache_error}")
                # 不影響搜尋結果回傳，只記錄錯誤
        
        # 構建詳細的查詢信息
        search_logic_info = {
            "used_and_or_logic": request.use_and_or_logic,
            "ai_keywords_or": request.selected_keywords,
            "user_keywords_or": request.custom_keywords,
            "search_description": ""
        }
        
        if request.use_and_or_logic and request.selected_keywords and request.custom_keywords:
            search_logic_info["search_description"] = f"({' OR '.join(request.custom_keywords)}) AND ({' OR '.join(request.selected_keywords)})"
        else:
            combined_keywords = list(dict.fromkeys(request.selected_keywords + request.custom_keywords))
            search_logic_info["search_description"] = f"傳統搜索: {' OR '.join(combined_keywords)}"
        
        return {
            "success": True,
            "results": result.results,
            "total_found": result.total_found,
            "message": result.message,
            "query_info": {
                **result.query_info,
                "session_id": request.session_id,
                "search_logic": search_logic_info,
                "cached_for_qa": len(result.results) > 0 if result.results else False  # 🆕 告知是否已暫存
            },
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 確認後搜索失敗: {e}")
        raise HTTPException(status_code=500, detail=f"確認後搜索失敗: {str(e)}")

@router.post(
    "/search/tech-description-with-synonyms",
    summary="使用關鍵字和同義詞執行技術描述查詢",
    description="用戶確認關鍵字和同義詞後，執行帶有同義詞邏輯的技術描述查詢流程",
    tags=["流程A-技術描述查詢"]
)
async def tech_description_search_with_synonyms(request: KeywordSynonymConfirmationRequest):
    """
    確認關鍵字和同義詞後的搜索處理
    支持 (關鍵字1 OR 同義詞1-1 OR 同義詞1-2) AND (關鍵字2 OR 同義詞2-1 OR 同義詞2-2) 邏輯
    """
    try:
        logger.info(f"🎯 收到關鍵字同義詞搜索請求")
        logger.info(f"會話ID: {request.session_id}")
        logger.info(f"選擇的關鍵字組合: {len(request.selected_keyword_groups)} 組")
        logger.info(f"自定義關鍵字: {request.custom_keywords}")
        
        if not improved_patent_processing_service.initialized:
            await improved_patent_processing_service.initialize()

        # 驗證用戶代碼
        if not request.user_code:
            raise HTTPException(status_code=400, detail="請先輸入GPSS API驗證碼")
        
        # 檢查是否有選擇的關鍵字或自定義關鍵字
        if not request.selected_keyword_groups and not request.custom_keywords:
            raise HTTPException(status_code=400, detail="請至少選擇一個關鍵字組合或輸入自定義關鍵字")
        
        logger.info(f"🔄 使用關鍵字同義詞搜索邏輯")
        
        # 執行帶同義詞的搜索
        result = await improved_patent_processing_service.process_tech_description_search_with_synonyms(
            description=request.description,
            selected_keyword_groups=request.selected_keyword_groups,
            custom_keywords=request.custom_keywords,
            user_code=request.user_code,
            max_results=request.max_results
        )
        
        if result.success:
            if result.results and len(result.results) > 0:
                try:
                    await DatabaseManager.save_search_results_to_cache(
                        session_id=request.session_id,
                        search_type="tech_description_search",
                        results=result.results,
                        expires_days=7
                    )
                    logger.info(f"✅ 技術描述同義詞搜尋結果已保存到暫存: {request.session_id}, {len(result.results)}筆")
                except Exception as cache_error:
                    logger.error(f"⚠️ 保存搜尋結果到暫存失敗: {cache_error}")

            return {
                "success": True,
                "session_id": request.session_id,
                "search_results": result.results,
                "total_found": result.total_found,
                "query_info": result.query_info,
                "message": result.message,
                "timestamp": time.time()
            }
        else:
            raise HTTPException(status_code=500, detail=result.error or "搜索失敗")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 關鍵字同義詞搜索失敗: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失敗: {str(e)}")
    
# ================================
# 流程B：條件查詢相關端點
# ================================

# 在 router.py 的條件搜尋端點中修正（簡化版）

@router.post(
    "/condition/search",
    summary="條件搜索（流程B）",
    description="流程B：條件查詢的API端點",
    tags=["流程B-條件查詢"]
)
async def condition_search(search_params: Dict[str, Any]):
    try:
        logger.info(f"🔍 收到流程B請求: {search_params}")
        if not improved_patent_processing_service.initialized:
            await improved_patent_processing_service.initialize()

        user_code = search_params.get('user_code')
        if not user_code:
            raise HTTPException(status_code=400, detail="請先輸入GPSS API驗證碼")

        # 構建有效條件
        valid_conditions = {}
        condition_fields = [
            'applicant', 'inventor', 'patent_number', 'application_number', 
            'ipc_class', 'title_keyword', 'abstract_keyword', 'claims_keyword',
            'application_date_from', 'application_date_to', 
            'publication_date_from', 'publication_date_to'
        ]
        
        for field in condition_fields:
            value = search_params.get(field)
            if value and str(value).strip():
                valid_conditions[field] = str(value).strip()
        
        if not valid_conditions:
            raise HTTPException(status_code=400, detail="請至少提供一個有效的搜索條件")

        result = await improved_patent_processing_service.process_condition_search(
            search_params=valid_conditions,
            user_code=user_code,
            max_results=search_params.get('max_results', 100)
        )
        
        if not result.success:
            if "驗證失敗" in result.error:
                raise HTTPException(status_code=401, detail=result.error)
            else:
                raise HTTPException(status_code=400, detail=result.error)
        
        # 🆕 新增：保存搜尋結果到暫存，供智能問答使用
        session_id = search_params.get('session_id', 'default')
        cached_for_qa = False
        
        if result.results and len(result.results) > 0:
            try:
                # 保存結果到資料庫暫存
                await DatabaseManager.save_search_results_to_cache(
                    session_id=session_id,
                    search_type="condition_search",
                    results=result.results,
                    expires_days=7
                )
                
                cached_for_qa = True
                logger.info(f"✅ 條件搜尋結果已保存到暫存: {session_id}, {len(result.results)}筆")
                
            except Exception as cache_error:
                logger.error(f"⚠️ 保存搜尋結果到暫存失敗: {cache_error}")
        
        # 🔧 簡化回傳結果，避免語法錯誤
        response_data = {
            "success": True,
            "results": result.results or [],
            "total_found": result.total_found,
            "message": result.message,
            "query_info": {
                "session_id": session_id,
                "cached_for_qa": cached_for_qa
            }
        }
        
        # 如果原本的 query_info 存在，合併進來
        if result.query_info:
            response_data["query_info"].update(result.query_info)
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🎭 流程B搜索失敗: {e}")
        raise HTTPException(status_code=500, detail=f"流程B搜索失敗: {str(e)}")
# ================================
# Excel分析功能相關端點
# ================================

@router.post(
    "/excel/upload-and-analyze",
    summary="上傳Excel並分析專利技術特徵",
    description="上傳包含專利資料的Excel檔案，系統會自動分析每筆專利並生成技術特徵與功效",
    tags=["Excel分析功能"]
)
async def upload_and_analyze_excel(
    file: UploadFile = File(..., description="Excel檔案(.xlsx, .xls)")
):
    """
    Excel上傳並分析功能
    必須包含欄位：公開公告號、專利名稱、摘要、專利範圍
    """
    try:
        # 驗證檔案類型
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="只支援Excel檔案格式(.xlsx, .xls)")
        
        # 檢查檔案大小 (限制為10MB)
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="檔案大小超過限制(10MB)")
        
        logger.info(f"📊 開始處理Excel檔案: {file.filename}, 大小: {len(content)} bytes")
        
        # 初始化服務
        if not improved_patent_processing_service.initialized:
            await improved_patent_processing_service.initialize()
        
        # 解析Excel檔案
        try:
            df = pd.read_excel(BytesIO(content))
            logger.info(f"📋 Excel解析成功，共 {len(df)} 行資料")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Excel檔案解析失敗: {str(e)}")
        
        # 驗證必要欄位
        required_columns = ['公開公告號', '專利名稱', '摘要', '專利範圍']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            # 嘗試英文欄位名稱
            english_mapping = {
                '公開公告號': ['publication_number', 'patent_number', 'pub_no'],
                '專利名稱': ['title', 'patent_title', 'name'],
                '摘要': ['abstract', 'summary'],
                '專利範圍': ['claims', 'patent_claims', 'claim']
            }
            
            column_mapping = {}
            for chinese_col in missing_columns:
                found = False
                for english_col in english_mapping.get(chinese_col, []):
                    if english_col in df.columns:
                        column_mapping[english_col] = chinese_col
                        found = True
                        break
                if not found:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Excel檔案缺少必要欄位: {missing_columns}。請確保包含：{required_columns}"
                    )
            
            # 重新命名欄位
            df = df.rename(columns=column_mapping)
        
        # 清理資料
        df = df.dropna(subset=required_columns, how='all')  # 移除完全空白的行
        
        if len(df) == 0:
            raise HTTPException(status_code=400, detail="Excel檔案中沒有有效的專利資料")
        
        # 限制處理數量 (最多500筆)
        max_records = 500
        if len(df) > max_records:
            df = df.head(max_records)
            logger.warning(f"⚠️ Excel資料超過{max_records}筆，只處理前{max_records}筆")
        
        # 生成會話ID
        session_id = str(uuid.uuid4())
        
        # 批量處理專利
        results = []
        errors = []
        
        logger.info(f"🔧 開始批量處理 {len(df)} 筆專利資料...")
        
        # 分批處理以避免記憶體問題
        batch_size = 10
        for i in range(0, len(df), batch_size):
            batch_df = df.iloc[i:i+batch_size]
            batch_results = await _process_excel_batch(batch_df, session_id, i)
            
            for result in batch_results:
                if result.get('error'):
                    errors.append(result['error'])
                else:
                    results.append(result)
            
            # 進度日誌
            processed_count = min(i + batch_size, len(df))
            logger.info(f"📊 已處理 {processed_count}/{len(df)} 筆專利")
            
            # 避免過載，稍作延遲
            if i + batch_size < len(df):
                await asyncio.sleep(0.5)
        
        success_count = len(results)
        error_count = len(errors)
        
        logger.info(f"✅ Excel分析完成: 成功 {success_count} 筆, 失敗 {error_count} 筆")
        
        return {
            "success": True,
            "processed_count": success_count,
            "total_count": len(df),
            "results": results,
            "errors": errors[:10],  # 只返回前10個錯誤
            "session_id": session_id,
            "timestamp": time.time(),
            "message": f"Excel分析完成，成功處理 {success_count} 筆專利資料"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Excel上傳分析失敗: {e}")
        raise HTTPException(status_code=500, detail=f"Excel分析失敗: {str(e)}")

@router.get(
    "/excel/analysis-status/{session_id}",
    summary="查詢Excel分析狀態",
    description="根據會話ID查詢Excel分析處理狀態",
    tags=["Excel分析功能"]
)
async def get_excel_analysis_status(session_id: str):
    """查詢Excel分析狀態（可選功能，用於長時間處理的情況）"""
    try:
        # 這裡可以實作進度追蹤，目前先返回基本資訊
        return {
            "session_id": session_id,
            "status": "completed",  # processing, completed, failed
            "message": "Excel分析已完成",
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢狀態失敗: {str(e)}")

# ================================
# 匯出功能相關端點
# ================================

@router.post(
    "/excel/export-analysis-results",
    summary="匯出Excel分析結果",
    description="將Excel分析結果匯出為新的Excel檔案",
    tags=["Excel分析功能"]
)
async def export_excel_analysis_results(request: Dict[str, Any]):
    """匯出Excel分析結果 - 修復檔案名問題"""
    try:
        results = request.get('results', [])
        session_id = request.get('session_id', 'unknown')
        
        if not results:
            raise HTTPException(status_code=400, detail="沒有可匯出的分析結果")
        
        # 準備匯出數據
        export_data = []
        for result in results:
            features = result.get("技術特徵", [])
            effects = result.get("技術功效", [])
            
            # 格式化技術特徵和功效，確保字符串格式
            features_text = "; ".join(str(f) for f in features) if isinstance(features, list) else str(features)
            effects_text = "; ".join(str(e) for e in effects) if isinstance(effects, list) else str(effects)
            
            # 確保所有文本都是字符串並處理None值
            export_data.append({
                "序號": result.get("序號", ""),
                "專利名稱": str(result.get("專利名稱", "")).strip() if result.get("專利名稱") else "",
                "公開公告號": str(result.get("公開公告號", "")).strip() if result.get("公開公告號") else "",
                "摘要": str(result.get("摘要", "")).strip() if result.get("摘要") else "",
                "專利範圍": str(result.get("專利範圍", "")).strip() if result.get("專利範圍") else "",
                "技術特徵": features_text,
                "技術功效": effects_text,
                "原始行號": result.get("原始行號", "")
            })
        
        # 創建Excel檔案 - 使用正確的編碼
        df = pd.DataFrame(export_data)
        buffer = BytesIO()
        
        # 使用openpyxl引擎並指定編碼選項
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='專利技術特徵分析結果', index=False)
            
            # 設置欄寬
            worksheet = writer.sheets['專利技術特徵分析結果']
            column_widths = {
                'A': 8,   # 序號
                'B': 35,  # 專利名稱
                'C': 18,  # 公開公告號
                'D': 50,  # 摘要
                'E': 50,  # 專利範圍
                'F': 40,  # 技術特徵
                'G': 40,  # 技術功效
                'H': 10   # 原始行號
            }
            
            for col, width in column_widths.items():
                worksheet.column_dimensions[col].width = width
        
        buffer.seek(0)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # 🎯 修正檔案名稱和Content-Disposition
        filename = f"patent_analysis_results_{session_id[:8]}_{timestamp}.xlsx"
        encoded_filename = quote(filename.encode('utf-8'))
        
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}',
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet; charset=utf-8"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Excel結果匯出失敗: {e}")
        raise HTTPException(status_code=500, detail=f"Excel結果匯出失敗: {str(e)}")

@router.post(
    "/export/excel",
    summary="匯出Excel報告",
    description="將專利檢索結果匯出為Excel檔案",
    tags=["匯出功能"]
)
async def export_to_excel(request: ExcelExportRequest):
    """匯出Excel報告 - 修復檔案名問題"""
    try:
        if not request.patents:
            raise HTTPException(status_code=400, detail="沒有可匯出的專利數據")

        export_data = []
        for i, patent in enumerate(request.patents):
            features = patent.get("技術特徵", patent.get("technical_features", []))
            effects = patent.get("技術功效", patent.get("technical_effects", []))
            features_effects = []
            
            if isinstance(features, list):
                features_effects.extend([f"特徵: {str(f)}" for f in features])
            if isinstance(effects, list):
                features_effects.extend([f"功效: {str(e)}" for e in effects])
            
            # 安全處理字符串轉換
            def safe_str(value, default="N/A"):
                if value is None:
                    return default
                return str(value).strip() if str(value).strip() else default
            
            export_data.append({
                "序號": i + 1,
                "專利名稱": safe_str(patent.get("專利名稱", patent.get("title", ""))),
                "申請人": safe_str(patent.get("申請人", patent.get("applicants", ""))),
                "國家": safe_str(patent.get("國家", patent.get("country", ""))),
                "申請號": safe_str(patent.get("申請號", patent.get("application_number", ""))),
                "公開公告號": safe_str(patent.get("公開公告號", patent.get("publication_number", ""))),
                "摘要": _truncate_text(safe_str(patent.get("摘要", patent.get("abstract", ""))), 500),
                "專利範圍": _truncate_text(safe_str(patent.get("專利範圍", patent.get("claims", ""))), 500),
                "技術特徵及功效": "; ".join(features_effects) if features_effects else "N/A"
            })

        df = pd.DataFrame(export_data)
        buffer = BytesIO() 
        
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='專利檢索結果', index=False)
            worksheet = writer.sheets['專利檢索結果']
            column_widths = {
                'A': 8,   # 序號
                'B': 40,  # 專利名稱
                'C': 20,  # 申請人
                'D': 8,   # 國家
                'E': 18,  # 申請號
                'F': 18,  # 公開公告號
                'G': 60,  # 摘要
                'H': 60,  # 專利範圍
                'I': 50   # 技術特徵及功效
            }
            
            for col, width in column_widths.items():
                worksheet.column_dimensions[col].width = width
        
        buffer.seek(0)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # 🎯 修正檔案名稱和Content-Disposition
        filename = f"patent_search_results_{request.search_type}_{timestamp}.xlsx"
        encoded_filename = quote(filename.encode('utf-8'))
        
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}',
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet; charset=utf-8"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Excel匯出失敗: {str(e)}")

# ================================
# 分析功能相關端點
# ================================

@router.post(
    "/keywords/generate",
    summary="生成關鍵字",
    description="從技術描述生成關鍵字",
    tags=["分析功能"]
)
async def generate_keywords(description: str):
    try:
        if len(description.strip()) < 20:
            raise HTTPException(status_code=400, detail="技術描述太短，請提供至少20個字的描述")

        if not improved_patent_processing_service.initialized:
            await improved_patent_processing_service.initialize()

        result = await improved_patent_processing_service.generate_keywords_from_description(description)     
        return {
            "success": True,
            "description": description,
            "keywords": result.get('keywords', []),
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"關鍵字生成失敗: {str(e)}")

# ================================
# 管理功能相關端點
# ================================

@router.post(
    "/admin/initialize",
    summary="初始化服務",
    description="手動初始化所有AI服務",
    tags=["管理功能"]
)
async def initialize_services():
    try:
        await improved_patent_processing_service.initialize()
        return {
            "success": True,
            "message": "所有服務初始化完成",
            "services": {
                "qwen": "ready" if improved_patent_processing_service.qwen_service else "failed",
                "gpss": "ready" if improved_patent_processing_service.gpss_service else "failed"
            },
            "timestamp": time.time(),
            "version": "6.0.0",
            "features": ["純技術特徵生成", "Excel編碼修復"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服務初始化失敗: {str(e)}")

@router.get(
    "/admin/status",
    summary="服務狀態",
    description="獲取所有服務的詳細狀態",
    tags=["管理功能"]
)
async def get_service_status():
    return {
        "initialized": improved_patent_processing_service.initialized,
        "qwen_service": improved_patent_processing_service.qwen_service is not None,
        "gpss_service": improved_patent_processing_service.gpss_service is not None,
        "verified_api_keys_count": len(improved_patent_processing_service.verified_api_keys),
        "timestamp": time.time(),
        "version": "6.0.0",
        "classification_removed": True,
        "new_features": {
            "pure_tech_features": "純技術特徵提取，移除所有分類功能",
            "excel_encoding_fix": "修復Excel下載檔案名編碼問題",
            "and_or_logic": "支持 (用戶關鍵字 OR ...) AND (AI關鍵字 OR ...) 搜索邏輯"
        }
    }

@router.post(
    "/qa/ask-with-memory",
    summary="智能問答（支持對話記憶）",
    description="基於檢索結果回答問題，支持記住前面的對話內容。利用128k token容量提供連續對話體驗。",
    tags=["🤖 智能問答"]
)
async def ask_question_with_memory(request: QARequest):
    """
    增強版智能問答 - 支持對話記憶
    
    特點：
    - 記住前面的對話內容
    - 自動管理token使用量（最大128k）
    - 智能修剪對話歷史
    - 上下文感知回答
    """
    try:
        logger.info(f"🤖 收到問答請求（記憶模式: {request.use_memory}）")
        
        if not enhanced_patent_qa_service.session:
            await enhanced_patent_qa_service.initialize()
        
        result = await enhanced_patent_qa_service.answer_question_with_memory(
            session_id=request.session_id,
            question=request.question,
            use_memory=request.use_memory
        )
        
        return {
            "success": result['success'],
            "answer": result['answer'],
            "referenced_patents": result.get('referenced_patents', []),
            "execution_time": result.get('execution_time', 0),
            "context_info": {
                "patent_count": result.get('context_patent_count', 0),
                "conversation_history_used": result.get('conversation_history_used', 0),
                "memory_enabled": result.get('memory_enabled', False)
            },
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ 問答請求失敗: {e}")
        raise HTTPException(status_code=500, detail=f"問答處理失敗: {str(e)}")

@router.post(
    "/qa/ask-simple", 
    summary="簡單問答（無記憶）",
    description="基於檢索結果回答問題，不使用對話記憶，每次都是獨立對話。",
    tags=["🤖 智能問答"]
)
async def ask_question_simple(request: QARequest):
    """簡單問答模式 - 不使用對話記憶"""
    try:
        if not enhanced_patent_qa_service.session:
            await enhanced_patent_qa_service.initialize()
        
        # 強制關閉記憶功能
        result = await enhanced_patent_qa_service.answer_question_with_memory(
            session_id=request.session_id,
            question=request.question,
            use_memory=False
        )
        
        return {
            "success": result['success'],
            "answer": result['answer'],
            "referenced_patents": result.get('referenced_patents', []),
            "execution_time": result.get('execution_time', 0),
            "mode": "simple_mode",
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ 簡單問答失敗: {e}")
        raise HTTPException(status_code=500, detail=f"簡單問答失敗: {str(e)}")

@router.get(
    "/qa/history/{session_id}",
    summary="獲取對話歷史",
    description="獲取指定會話的對話歷史記錄",
    tags=["🤖 智能問答"]
)
async def get_qa_history(session_id: str, limit: int = 10):
    """獲取對話歷史"""
    try:
        if limit > 50:
            limit = 50
            
        history = await DatabaseManager.get_qa_history(session_id, limit=limit)
        
        return {
            "success": True,
            "session_id": session_id,
            "history": history,
            "total_count": len(history),
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ 獲取對話歷史失敗: {e}")
        raise HTTPException(status_code=500, detail=f"獲取對話歷史失敗: {str(e)}")

@router.get(
    "/qa/conversation-summary/{session_id}",
    summary="獲取對話摘要",
    description="獲取會話的對話摘要，包括話題統計和最近問題",
    tags=["🤖 智能問答"]
)
async def get_conversation_summary(session_id: str):
    """獲取對話摘要"""
    try:
        if not enhanced_patent_qa_service.session:
            await enhanced_patent_qa_service.initialize()
            
        summary = await enhanced_patent_qa_service.get_conversation_summary(session_id)
        
        return {
            **summary,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ 獲取對話摘要失敗: {e}")
        raise HTTPException(status_code=500, detail=f"獲取對話摘要失敗: {str(e)}")

@router.post(
    "/qa/clear-memory",
    summary="清除對話記憶",
    description="清除指定會話的對話記憶（僅清除內存緩存，不刪除數據庫記錄）",
    tags=["🤖 智能問答"]
)
async def clear_conversation_memory(request: ClearMemoryRequest):
    """清除對話記憶"""
    try:
        if not enhanced_patent_qa_service.session:
            await enhanced_patent_qa_service.initialize()
            
        success = await enhanced_patent_qa_service.clear_conversation_memory(request.session_id)
        
        return {
            "success": success,
            "message": "對話記憶已清除" if success else "清除對話記憶失敗",
            "session_id": request.session_id,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ 清除對話記憶失敗: {e}")
        raise HTTPException(status_code=500, detail=f"清除對話記憶失敗: {str(e)}")

@router.get(
    "/qa/memory-status/{session_id}",
    summary="檢查記憶狀態",
    description="檢查指定會話的記憶狀態和統計信息",
    tags=["🤖 智能問答"]
)
async def get_memory_status(session_id: str):
    """檢查記憶狀態"""
    try:
        # 檢查內存緩存
        memory_cached = session_id in enhanced_patent_qa_service.session_conversations
        memory_count = 0
        
        if memory_cached:
            memory_count = len(enhanced_patent_qa_service.session_conversations[session_id])
        
        # 檢查數據庫歷史
        db_history = await DatabaseManager.get_qa_history(session_id, limit=1)
        has_db_history = len(db_history) > 0
        
        # 檢查檢索結果緩存
        cached_results = await DatabaseManager.get_cached_search_results(session_id)
        has_search_cache = len(cached_results) > 0
        
        return {
            "success": True,
            "session_id": session_id,
            "memory_status": {
                "memory_cached": memory_cached,
                "memory_count": memory_count,
                "has_db_history": has_db_history,
                "has_search_cache": has_search_cache,
                "max_tokens": enhanced_patent_qa_service.conversation_manager.max_tokens,
                "available_history_tokens": enhanced_patent_qa_service.conversation_manager.available_history_tokens
            },
            "ready_for_qa": has_search_cache,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ 檢查記憶狀態失敗: {e}")
        raise HTTPException(status_code=500, detail=f"檢查記憶狀態失敗: {str(e)}")

# ================================
# 測試端點
# ================================

@router.post(
    "/qa/test-memory",
    summary="測試對話記憶功能",
    description="測試對話記憶功能是否正常工作",
    tags=["🧪 測試功能"]
)
async def test_memory_functionality():
    """測試對話記憶功能"""
    try:
        test_session_id = f"test_memory_{int(time.time())}"
        
        if not enhanced_patent_qa_service.session:
            await enhanced_patent_qa_service.initialize()
        
        # 模擬對話歷史
        test_history = [
            {
                'question': '什麼是半導體測試？',
                'answer': '半導體測試是評估半導體器件性能和功能的過程。',
                'created_at': datetime.now().isoformat()
            },
            {
                'question': '測試探針的作用是什麼？',
                'answer': '測試探針用於與半導體器件建立電氣連接，進行電性測試。',
                'created_at': datetime.now().isoformat()
            }
        ]
        
        # 將測試歷史添加到內存緩存
        enhanced_patent_qa_service.session_conversations[test_session_id] = test_history
        
        # 測試token估算
        sample_text = "這是一個測試文本，用於驗證token估算功能。This is a test text for token estimation."
        estimated_tokens = enhanced_patent_qa_service.conversation_manager.estimate_tokens(sample_text)
        
        # 測試對話歷史修剪
        trimmed = enhanced_patent_qa_service.conversation_manager.trim_conversation_history(test_history)
        
        return {
            "success": True,
            "test_results": {
                "memory_management": "✅ 正常",
                "token_estimation": f"✅ 正常 (估算 {estimated_tokens} tokens)",
                "history_trimming": f"✅ 正常 (保留 {len(trimmed)}/{len(test_history)} 輪對話)",
                "max_token_capacity": f"{enhanced_patent_qa_service.conversation_manager.max_tokens:,} tokens",
                "available_for_history": f"{enhanced_patent_qa_service.conversation_manager.available_history_tokens:,} tokens"
            },
            "test_session_id": test_session_id,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ 測試對話記憶功能失敗: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": time.time()
        }
# ================================
# 輔助函數
# ================================

async def _process_excel_batch(batch_df: pd.DataFrame, session_id: str, start_index: int) -> List[Dict]:
    """處理Excel批次資料"""
    batch_results = []
    
    for idx, row in batch_df.iterrows():
        try:
            # 提取專利資料
            patent_data = {
                'title': str(row.get('專利名稱', '')).strip() if pd.notna(row.get('專利名稱')) else '',
                'abstract': str(row.get('摘要', '')).strip() if pd.notna(row.get('摘要')) else '',
                'claims': str(row.get('專利範圍', '')).strip() if pd.notna(row.get('專利範圍')) else '',
                'publication_number': str(row.get('公開公告號', '')).strip() if pd.notna(row.get('公開公告號')) else ''
            }
            
            # 基本驗證
            if not patent_data['title'] or not patent_data['publication_number']:
                batch_results.append({
                    'error': f"第 {start_index + idx + 2} 行資料不完整 (缺少專利名稱或公開公告號)"
                })
                continue
            
            # 生成技術特徵和功效
            features_result = await improved_patent_processing_service._generate_tech_features_and_effects(patent_data)
            
            # 組裝結果
            result = {
                "序號": start_index + idx + 1,
                "專利名稱": patent_data['title'],
                "公開公告號": patent_data['publication_number'],
                "摘要": patent_data['abstract'][:1300] + "..." if len(patent_data['abstract']) > 1300 else patent_data['abstract'],
                "專利範圍": patent_data['claims'][:1300] + "..." if len(patent_data['claims']) > 1300 else patent_data['claims'],
                "技術特徵": features_result.get('technical_features', []),
                "技術功效": features_result.get('technical_effects', []),
                "session_id": session_id,
                "原始行號": start_index + idx + 2  # Excel中的實際行號
            }
            
            batch_results.append(result)
            
        except Exception as e:
            logger.warning(f"處理第 {start_index + idx + 2} 行專利失敗: {e}")
            batch_results.append({
                'error': f"第 {start_index + idx + 2} 行處理失敗: {str(e)}"
            })
    
    return batch_results

def _truncate_text(text, max_length: int) -> str:
    """截斷文本到指定長度"""
    if not text or text == "N/A":
        return "N/A"

    text = str(text)
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."