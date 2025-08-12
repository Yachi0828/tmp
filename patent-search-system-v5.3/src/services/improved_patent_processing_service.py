# src/services/improved_patent_processing_service.py - 修復申請人和國家顯示

import asyncio
import logging
import json
import time
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from src.ai_services.qwen_service import QwenAPIService
from src.ai_services.gpss_service import GPSSAPIService
from src.config import settings
import pandas as pd
from io import BytesIO
import uuid
from typing import BinaryIO

logger = logging.getLogger(__name__)

@dataclass
class PatentProcessingResult:
    success: bool
    results: List[Dict[str, Any]] = None
    total_found: int = 0
    message: str = ""
    query_info: Dict[str, Any] = None
    error: str = ""

class ImprovedPatentProcessingService:
    BATCH_SIZE = 30
    BATCH_DELAY = 0.1
    MAX_CONCURRENT_REQUESTS = 16
    REQUEST_DELAY = 0.2
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    
    def __init__(self):
        self.qwen_service = None
        self.gpss_service = None
        self.initialized = False
        self.verified_api_keys = set()
        self.semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_REQUESTS)
        
    async def initialize(self):
        """初始化所有AI服務"""
        if self.initialized:
            return
            
        try:
            logger.info("🚀 開始初始化專利處理服務（修復申請人和國家版本）...")
            
            # 初始化Qwen服務
            self.qwen_service = QwenAPIService(settings.QWEN_API_URL)
            await self.qwen_service.initialize()
            logger.info("✅ Qwen初始化成功")
            
            # 初始化真實GPSS服務
            self.gpss_service = GPSSAPIService()
            await self.gpss_service.initialize()
            logger.info("✅ GPSS初始化成功（已修復申請人和國家欄位）")
            
            self.initialized = True
            logger.info("專利處理服務初始化完成！（申請人和國家修復版本）")
            
        except Exception as e:
            logger.error(f"服務初始化失敗: {e}")
            raise
    
    async def close(self):
        """關閉所有服務"""
        if self.qwen_service:
            await self.qwen_service.close()
        if self.gpss_service:
            await self.gpss_service.close()
        logger.info("所有服務已關閉")

    async def verify_api_key(self, user_code: str) -> bool:
        """驗證GPSS API密鑰"""
        try:
            if user_code in self.verified_api_keys:
                return True
            
            # 基本格式驗證
            if not user_code or len(user_code) < 16:
                logger.warning("API密鑰格式不正確")
                return False
            
            # 使用真實GPSS API測試連接
            test_result = await self.gpss_service.test_api_connection(user_code)
            
            if test_result.get('success', False):
                self.verified_api_keys.add(user_code)
                logger.info(f"API密鑰驗證成功: {user_code[:8]}...")
                return True
            else:
                logger.warning(f"API密鑰驗證失敗: {test_result.get('message', 'Unknown error')}")
                return False
            
        except Exception as e:
            logger.error(f"API密鑰驗證異常: {e}")
            return False

    async def process_tech_description_search_with_keywords(
        self,
        description: str,
        keywords: List[str],
        user_code: str,
        max_results: int = 1000
    ) -> PatentProcessingResult:
        """流程A：使用已確認的關鍵字執行技術描述查詢"""
        start_time = time.time()
        
        try:
            logger.info(f"使用確認關鍵字執行技術描述查詢，關鍵字: {keywords}")
            
            # 步驟1：驗證API密鑰
            if settings.REQUIRE_API_VALIDATION and not await self.verify_api_key(user_code):
                return PatentProcessingResult(
                    success=False,
                    error="GPSS API密鑰驗證失敗，請檢查密鑰是否正確"
                )
            
            # 步驟2：使用提供的關鍵字搜索專利
            raw_patents = await self._search_patents_with_keywords(keywords, user_code, max_results)
            
            if not raw_patents:
                return PatentProcessingResult(
                    success=True,
                    results=[],
                    total_found=0,
                    message="未找到相關專利",
                    query_info={
                        "description": description,
                        "used_keywords": keywords,
                        "search_time": time.time() - start_time
                    }
                )
            
            logger.info(f"搜索到 {len(raw_patents)} 筆原始專利")
            
            # 步驟3：批次處理專利（只生成技術特徵）
            processed_patents = await self._process_patents_with_batching(raw_patents)
            
            # 步驟4：格式化結果（修復版本）
            formatted_results = self._format_search_results_fixed(processed_patents)
            
            execution_time = time.time() - start_time
            
            return PatentProcessingResult(
                success=True,
                results=formatted_results,
                total_found=len(formatted_results),
                message=f"技術描述查詢完成，找到 {len(formatted_results)} 筆專利",
                query_info={
                    "description": description,
                    "used_keywords": keywords,
                    "search_time": execution_time,
                    "processed_count": len(processed_patents),
                    "batch_processing": True
                }
            )
            
        except Exception as e:
            logger.error(f"使用關鍵字查詢失敗: {e}")
            return PatentProcessingResult(
                success=False,
                error=f"使用關鍵字查詢失敗: {str(e)}"
            )

    async def process_tech_description_search_with_and_or_logic(
        self,
        description: str,
        user_keywords: List[str],
        ai_keywords: List[str],
        user_code: str,
        max_results: int = 1000
    ) -> PatentProcessingResult:
        """流程A：使用 AND/OR 邏輯執行技術描述查詢"""
        start_time = time.time()
        
        try:
            logger.info(f"🔍 使用AND/OR邏輯執行技術描述查詢")
            logger.info(f"📝 用戶關鍵字(OR邏輯): {user_keywords}")
            logger.info(f"🤖 AI關鍵字(OR邏輯): {ai_keywords}")
            
            # 步驟1：驗證API密鑰
            if settings.REQUIRE_API_VALIDATION and not await self.verify_api_key(user_code):
                return PatentProcessingResult(
                    success=False,
                    error="GPSS API密鑰驗證失敗，請檢查密鑰是否正確"
                )
            
            # 步驟2：使用AND/OR邏輯搜索專利
            raw_patents = await self._search_patents_with_and_or_logic(
                user_keywords, ai_keywords, user_code, max_results
            )
            
            if not raw_patents:
                return PatentProcessingResult(
                    success=True,
                    results=[],
                    total_found=0,
                    message="未找到相關專利",
                    query_info={
                        "description": description,
                        "user_keywords": user_keywords,
                        "ai_keywords": ai_keywords,
                        "search_logic": "(用戶關鍵字 OR ...) AND (AI關鍵字 OR ...)",
                        "search_time": time.time() - start_time
                    }
                )
            
            logger.info(f"✅ AND/OR邏輯搜索到 {len(raw_patents)} 筆原始專利")
            
            # 步驟3：批次處理專利
            processed_patents = await self._process_patents_with_batching(raw_patents)
            
            # 步驟4：格式化結果（修復版本）
            formatted_results = self._format_search_results_fixed(processed_patents)
            
            execution_time = time.time() - start_time
            
            return PatentProcessingResult(
                success=True,
                results=formatted_results,
                total_found=len(formatted_results),
                message=f"AND/OR邏輯查詢完成，找到 {len(formatted_results)} 筆專利",
                query_info={
                    "description": description,
                    "user_keywords": user_keywords,
                    "ai_keywords": ai_keywords,
                    "search_logic": "(用戶關鍵字 OR ...) AND (AI關鍵字 OR ...)",
                    "search_time": execution_time,
                    "processed_count": len(processed_patents),
                    "batch_processing": True
                }
            )
            
        except Exception as e:
            logger.error(f"❌ AND/OR邏輯查詢失敗: {e}")
            return PatentProcessingResult(
                success=False,
                error=f"AND/OR邏輯查詢失敗: {str(e)}"
            )

    async def process_condition_search(
        self, 
        search_params: Dict[str, Any], 
        user_code: str, 
        max_results: int = 1000
    ) -> PatentProcessingResult:
        """流程B：條件查詢"""
        start_time = time.time()
        
        try:
            logger.info(f"開始條件查詢: {search_params}")
            
            # 步驟1：驗證API密鑰
            if settings.REQUIRE_API_VALIDATION and not await self.verify_api_key(user_code):
                return PatentProcessingResult(
                    success=False,
                    error="GPSS API密鑰驗證失敗，請檢查密鑰是否正確"
                )
            
            # 步驟2：根據條件搜索專利
            raw_patents = await self._search_patents_with_conditions(search_params, user_code, max_results)
            
            if not raw_patents:
                return PatentProcessingResult(
                    success=True,
                    results=[],
                    total_found=0,
                    message="未找到符合條件的專利",
                    query_info={
                        "search_conditions": search_params,
                        "search_time": time.time() - start_time
                    }
                )
            
            logger.info(f"搜索到 {len(raw_patents)} 筆原始專利")
            
            # 步驟3：批次處理專利
            processed_patents = await self._process_patents_with_batching(raw_patents)
            
            # 步驟4：格式化結果（修復版本）
            formatted_results = self._format_search_results_fixed(processed_patents)
            
            execution_time = time.time() - start_time
            
            return PatentProcessingResult(
                success=True,
                results=formatted_results,
                total_found=len(formatted_results),
                message=f"條件查詢完成，找到 {len(formatted_results)} 筆專利",
                query_info={
                    "search_conditions": search_params,
                    "search_time": execution_time,
                    "processed_count": len(processed_patents),
                    "batch_processing": True
                }
            )
            
        except Exception as e:
            logger.error(f"條件查詢失敗: {e}")
            return PatentProcessingResult(
                success=False,
                error=f"條件查詢失敗: {str(e)}"
            )

    async def _search_patents_with_and_or_logic(
        self, 
        user_keywords: List[str], 
        ai_keywords: List[str], 
        user_code: str, 
        max_results: int
    ) -> List[Dict]:
        """使用AND/OR關鍵字邏輯搜索專利"""
        try:
            logger.info(f"🔍 執行AND/OR邏輯搜索")
            logger.info(f"📝 用戶關鍵字(OR): {user_keywords}")
            logger.info(f"🤖 AI關鍵字(OR): {ai_keywords}")
            
            # 使用GPSS服務的AND/OR搜索方法
            raw_result = await self.gpss_service.search_patents_with_and_or_logic(
                user_code=user_code,
                user_keywords=user_keywords if user_keywords else None,
                ai_keywords=ai_keywords if ai_keywords else None,
                databases=['TWA','TWB','USA','USB','JPA','JPB','EPA','EPB','KPA','KPB','CNA','CNB','WO','SEAA','SEAB','OTA','OTB'],
                max_results=max_results
            )
            
            # 解析GPSS回應
            patents = self.gpss_service.parse_gpss_response(raw_result)
            logger.info(f"✅ AND/OR邏輯成功解析 {len(patents)} 筆專利")
            return patents
                
        except Exception as e:
            logger.error(f"❌ AND/OR專利搜索失敗: {e}")
            raise Exception(f"AND/OR專利搜索失敗: {str(e)}")

    async def _search_patents_with_keywords(self, keywords: List[str], user_code: str, max_results: int) -> List[Dict]:
        """使用關鍵字搜索專利（傳統方式）"""
        try:
            logger.info(f"使用GPSS API搜索專利，關鍵字: {keywords}")
            
            # 使用真實GPSS API
            raw_result = await self.gpss_service.search_patents_raw(
                user_code=user_code,
                keywords=keywords,
                databases=['TWA','TWB','USA','USB','JPA','JPB','EPA','EPB','KPA','KPB','CNA','CNB','WO','SEAA','SEAB','OTA','OTB'],
                max_results=max_results
            )
            
            # 解析GPSS回應
            patents = self.gpss_service.parse_gpss_response(raw_result)
            logger.info(f"成功解析 {len(patents)} 筆專利")
            return patents
                
        except Exception as e:
            logger.error(f"專利搜索失敗: {e}")
            raise Exception(f"專利搜索失敗: {str(e)}")

    async def _search_patents_with_conditions(self, conditions: Dict[str, Any], user_code: str, max_results: int) -> List[Dict]:
        """根據條件搜索專利"""
        try:
            logger.info(f"使用真實GPSS API條件搜索，條件: {conditions}")
            
            # 將條件轉換為GPSS API格式
            search_conditions = {}
            
            # 基本條件
            if conditions.get('applicant'):
                search_conditions['applicant'] = conditions['applicant']
            if conditions.get('inventor'):
                search_conditions['inventor'] = conditions['inventor']
            if conditions.get('patent_number'):
                search_conditions['patent_number'] = conditions['patent_number']
            if conditions.get('application_number'):
                search_conditions['application_number'] = conditions['application_number']
            if conditions.get('ipc_class'):
                search_conditions['ipc_class'] = conditions['ipc_class']
            if conditions.get('title_keyword'):
                search_conditions['title'] = conditions['title_keyword']
            if conditions.get('abstract_keyword'):
                search_conditions['abstract'] = conditions['abstract_keyword']
            if conditions.get('claims_keyword'):
                search_conditions['claims'] = conditions['claims_keyword']
            
            # 日期條件
            date_params = {}
            if conditions.get('application_date_from') or conditions.get('application_date_to'):
                date_range = []
                if conditions.get('application_date_from'):
                    date_range.append(conditions['application_date_from'].replace('-', ''))
                if conditions.get('application_date_to'):
                    if len(date_range) == 1:
                        date_range.append(conditions['application_date_to'].replace('-', ''))
                    else:
                        date_range = [conditions['application_date_to'].replace('-', '')]
                
                if len(date_range) == 2:
                    date_params['gpss_AD'] = f"{date_range[0]}:{date_range[1]}"
                elif len(date_range) == 1:
                    date_params['gpss_AD'] = f"{date_range[0]}:"
            
            if conditions.get('publication_date_from') or conditions.get('publication_date_to'):
                date_range = []
                if conditions.get('publication_date_from'):
                    date_range.append(conditions['publication_date_from'].replace('-', ''))
                if conditions.get('publication_date_to'):
                    if len(date_range) == 1:
                        date_range.append(conditions['publication_date_to'].replace('-', ''))
                    else:
                        date_range = [conditions['publication_date_to'].replace('-', '')]
                
                if len(date_range) == 2:
                    date_params['gpss_ID'] = f"{date_range[0]}:{date_range[1]}"
                elif len(date_range) == 1:
                    date_params['gpss_ID'] = f"{date_range[0]}:"
            
            # 使用真實GPSS API
            raw_result = await self.gpss_service.search_patents_raw(
                user_code=user_code,
                search_conditions=search_conditions,
                databases=['TWA','TWB','USA','USB','JPA','JPB','EPA','EPB','KPA','KPB','CNA','CNB','WO','SEAA','SEAB','OTA','OTB'],
                max_results=max_results,
                **date_params
            )
            
            # 解析GPSS回應
            patents = self.gpss_service.parse_gpss_response(raw_result)
            logger.info(f"成功解析 {len(patents)} 筆專利")
            return patents
                
        except Exception as e:
            logger.error(f"條件搜索失敗: {e}")
            raise Exception(f"條件搜索失敗: {str(e)}")

    async def generate_keywords_from_description(self, description: str) -> Dict[str, Any]:
        """使用Qwen從技術描述生成5個關鍵字"""
        try:
            if not self.qwen_service:
                return {"keywords": self._extract_fallback_keywords(description)}
        
            result = await self.qwen_service.generate_keywords_from_description(description, num_keywords=5)
            return result
        
        except Exception as e:
            logger.warning(f"Qwen關鍵字生成失敗，使用fallback: {e}")
            return {"keywords": self._extract_fallback_keywords(description)}

    async def generate_keywords_with_synonyms_from_description(self, description: str) -> Dict:
        """
        從技術描述生成關鍵字和同義詞
        """
        try:
            if not self.qwen_service:
                raise Exception("Qwen服務未初始化")

            result = await self.qwen_service.generate_keywords_with_synonyms(description, num_keywords=3, num_synonyms=5)
            return result

        except Exception as e:
            logger.error(f"生成關鍵字和同義詞失敗: {e}")
            # 使用fallback方法
            return self._generate_keywords_synonyms_fallback(description, 3, 5)

    def _generate_keywords_synonyms_fallback(self, description: str, num_keywords: int, num_synonyms: int) -> Dict:
        """
        Fallback方法：當Qwen失敗時使用的關鍵字和同義詞生成
        """
        # 基本的技術詞彙對應表
        tech_synonyms = {
            "測試": ["test", "檢測", "測量", "檢驗", "驗證"],
            "控制": ["control", "控制器", "調節", "管理", "操控"],
            "自動化": ["automation", "自動", "智能化", "無人化", "機械化"],
            "半導體": ["semiconductor", "晶片", "IC", "芯片", "電子元件"],
            "探針": ["probe", "測試針", "探測器", "檢測器", "測試頭"],
            "精密": ["precision", "精確", "高精度", "微米級", "準確"],
            "系統": ["system", "設備", "裝置", "機台", "平台"],
            "處理": ["processing", "處理器", "加工", "操作", "運算"],
            "檢測": ["detection", "檢查", "監測", "識別", "感測"],
            "晶圓": ["wafer", "矽片", "基板", "晶片", "圓片"]
        }

        # 從描述中提取關鍵詞
        keywords_found = []
        description_lower = description.lower()

        for main_word, synonyms in tech_synonyms.items():
            if main_word in description or any(syn.lower() in description_lower for syn in synonyms):
                keywords_found.append({
                    "keyword": main_word,
                    "synonyms": synonyms[:num_synonyms]
                })
                if len(keywords_found) >= num_keywords:
                    break
                    
        # 如果找到的不夠，添加通用技術詞彙
        if len(keywords_found) < num_keywords:
            default_keywords = [
                {"keyword": "檢測", "synonyms": ["detection", "測試", "檢驗", "測量", "分析"]},
                {"keyword": "控制", "synonyms": ["control", "調節", "管理", "操控", "指令"]},
                {"keyword": "自動化", "synonyms": ["automation", "智能", "機械", "無人", "自動"]}
            ]
            
            for default in default_keywords:
                if len(keywords_found) >= num_keywords:
                    break
                if not any(item['keyword'] == default['keyword'] for item in keywords_found):
                    keywords_found.append(default)

        return {
            "keywords_with_synonyms": keywords_found[:num_keywords],
            "source": "fallback"
        }

    async def process_tech_description_search_with_synonyms(
        self,
        description: str,
        selected_keyword_groups: List[Dict[str, Any]],
        custom_keywords: List[str],
        user_code: str,
        max_results: int = 200
    ) -> PatentProcessingResult:
        """
        處理帶同義詞的技術描述搜索
        構建GPSS API可理解的AND/OR查詢語法，直接發送給GPSS資料庫執行
        """
        try:
            start_time = time.time()
            logger.info(f"🔍 開始執行帶同義詞的技術描述搜索")

            # 驗證API密鑰
            if not await self.verify_api_key(user_code):
                return PatentProcessingResult(
                    success=False,
                    error="GPSS API驗證失敗，請檢查驗證碼是否正確"
                )

            # 🎯 構建GPSS API可理解的查詢語法
            gpss_query = self._build_gpss_and_or_query(selected_keyword_groups, custom_keywords)

            logger.info(f"🔍 構建的GPSS查詢語法: {gpss_query}")

            # 🚀 直接使用GPSS API執行複雜AND/OR邏輯查詢
            raw_result = await self.gpss_service.search_patents_with_complex_and_or_logic(
                user_code=user_code,
                complex_query=gpss_query,
                databases=['TWA','TWB','USA','USB','JPA','JPB','EPA','EPB','KPA','KPB','CNA','CNB','WO','SEAA','SEAB','OTA','OTB'],
                max_results=max_results
            )

            # 解析GPSS回應
            patents = self.gpss_service.parse_gpss_response(raw_result)

            if not patents:
                return PatentProcessingResult(
                    success=True,
                    results=[],
                    total_found=0,
                    message="未找到符合條件的專利",
                    query_info={
                        "gpss_query": gpss_query,
                        "keyword_groups": selected_keyword_groups,
                        "custom_keywords": custom_keywords,
                        "execution_time": time.time() - start_time
                    }
                )

            logger.info(f"📋 GPSS搜索返回 {len(patents)} 筆專利")

            # 使用Qwen為每個專利生成技術特徵和功效
            processed_patents = await self._process_patents_with_qwen_features(patents[:max_results])

            execution_time = time.time() - start_time

            return PatentProcessingResult(
                success=True,
                results=processed_patents,
                total_found=len(processed_patents),
                message=f"成功檢索並處理了 {len(processed_patents)} 筆專利",
                query_info={
                    "gpss_query": gpss_query,
                    "keyword_groups": selected_keyword_groups,
                    "custom_keywords": custom_keywords,
                    "execution_time": execution_time,
                    "search_logic": "GPSS資料庫執行AND/OR邏輯"
                }
            )

        except Exception as e:
            logger.error(f"❌ 帶同義詞的技術描述搜索失敗: {e}")
            return PatentProcessingResult(
                success=False,
                error=f"搜索失敗: {str(e)}"
            )

    def _build_gpss_and_or_query(
        self, 
        selected_keyword_groups: List[Dict[str, Any]], 
        custom_keywords: List[str]
    ) -> str:
        """
        構建GPSS API可理解的AND/OR查詢語法

        例如：(關鍵字1 OR 同義詞1-1 OR 同義詞1-2) AND (關鍵字2 OR 同義詞2-1 OR 同義詞2-2)

        GPSS API語法參考：
        - OR: 用 OR 連接
        - AND: 用 AND 連接  
        - 括號: 用 () 包圍
        """
        try:
            query_parts = []

            # 處理關鍵字組合（每組內用OR，組間用AND）
            for group_index, group in enumerate(selected_keyword_groups):
                group_terms = []

                # 添加主關鍵字（如果選中）
                if group.get('keyword_selected', False):
                    keyword = group.get('keyword', '')
                    if keyword:
                        group_terms.append(keyword)

                # 添加選中的同義詞
                selected_synonyms = group.get('selected_synonyms', [])
                group_terms.extend(selected_synonyms)

                # 如果這組有選中的詞彙，構建組內OR邏輯
                if group_terms:
                    # 清理和轉義詞彙
                    cleaned_terms = [self._escape_gpss_term(term) for term in group_terms if term.strip()]
                    if cleaned_terms:
                        # 組內用OR連接
                        group_query = " or ".join(cleaned_terms)
                        query_parts.append(f"({group_query})")

                        logger.debug(f"關鍵字組{group_index + 1}: {group_query}")

            # 處理自定義關鍵字
            if custom_keywords:
                custom_terms = []
                for custom_kw in custom_keywords:
                    if custom_kw and custom_kw.strip():
                        cleaned_kw = self._escape_gpss_term(custom_kw.strip())
                        custom_terms.append(cleaned_kw)

                if custom_terms:
                    custom_query = " or ".join(custom_terms)
                    query_parts.append(f"({custom_query})")
                    logger.debug(f"自定義關鍵字: {custom_query}")

            # 組間用AND連接
            if not query_parts:
                return ""

            final_query = " and ".join(query_parts)

            logger.info(f"🔧 GPSS查詢語法構建完成:")
            logger.info(f"   - 關鍵字組數: {len(selected_keyword_groups)}")
            logger.info(f"   - 自定義關鍵字數: {len(custom_keywords) if custom_keywords else 0}")
            logger.info(f"   - 最終查詢: {final_query}")

            return final_query

        except Exception as e:
            logger.error(f"❌ 構建GPSS查詢語法失敗: {e}")
            return ""

    def _escape_gpss_term(self, term: str) -> str:
        """
        轉義GPSS API查詢詞彙

        根據GPSS API規範處理特殊字符
        """
        if not term:
            return ""

        # 移除首尾空白
        term = term.strip()

        # 如果包含空格或特殊字符，用引號包圍
        if ' ' in term or any(char in term for char in ['(', ')', '&', '|', '"']):
            # 轉義內部的引號
            term = term.replace('"', '\\"')
            return f'"{term}"'
        
        return term

    async def _process_patents_with_qwen_features(self, patents: List[Dict]) -> List[Dict]:
        """
        使用Qwen為專利列表生成技術特徵和功效
        """
        processed_patents = []

        # 使用信號量控制並發
        async def process_single_patent(patent, index):
            async with self.semaphore:
                try:
                    logger.info(f"📝 處理專利 {index + 1}/{len(patents)}: {patent.get('title', 'N/A')[:50]}...")

                    # 準備專利數據
                    patent_data = {
                        'title': patent.get('title', ''),
                        'abstract': patent.get('abstract', ''),
                        'claims': patent.get('claims', ''),
                        'main_claim': patent.get('claims', '')[:500] if patent.get('claims') else ''
                    }

                    # 使用Qwen生成技術特徵和功效
                    features_result = await self.qwen_service.generate_technical_features_and_effects(patent_data)

                    # 組裝最終結果
                    processed_patent = {
                        "序號": index + 1,
                        "專利名稱": patent.get('title', 'N/A'),
                        "公開公告號": patent.get('publication_number', patent.get('id', 'N/A')),
                        "摘要": patent.get('abstract', 'N/A'),
                        "專利範圍": patent.get('claims', 'N/A'),
                        "技術特徵": features_result.get('technical_features', ['技術特徵生成中...']),
                        "技術功效": features_result.get('technical_effects', ['技術功效生成中...']),

                        # 保留原始資料供其他用途
                        "申請人": patent.get('applicants', 'N/A'),
                        "發明人": patent.get('inventors', 'N/A'),
                        "國家": patent.get('country', 'TW'),
                        "申請日": patent.get('application_date', 'N/A'),
                        "公開日": patent.get('publication_date', 'N/A'),
                        "IPC分類": patent.get('ipc_classes', 'N/A')
                    }

                    return processed_patent

                except Exception as e:
                    logger.error(f"❌ 處理專利 {index + 1} 失敗: {e}")
                    # 返回基本信息，標記處理失敗
                    return {
                        "序號": index + 1,
                        "專利名稱": patent.get('title', 'N/A'),
                        "公開公告號": patent.get('publication_number', patent.get('id', 'N/A')),
                        "摘要": patent.get('abstract', 'N/A'),
                        "專利範圍": patent.get('claims', 'N/A'),
                        "技術特徵": ['技術特徵生成失敗'],
                        "技術功效": ['技術功效生成失敗'],
                        "申請人": patent.get('applicants', 'N/A'),
                        "發明人": patent.get('inventors', 'N/A'),
                        "國家": patent.get('country', 'TW'),
                        "申請日": patent.get('application_date', 'N/A'),
                        "公開日": patent.get('publication_date', 'N/A'),
                        "IPC分類": patent.get('ipc_classes', 'N/A')
                    }

        # 並行處理所有專利
        tasks = [process_single_patent(patent, i) for i, patent in enumerate(patents)]
    
        # 分批處理以避免過載
        for i in range(0, len(tasks), self.BATCH_SIZE):
            batch = tasks[i:i + self.BATCH_SIZE]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
        
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"❌ 批次處理失敗: {result}")
                else:
                    processed_patents.append(result)

            # 批次間延遲
            if i + self.BATCH_SIZE < len(tasks):
                await asyncio.sleep(self.BATCH_DELAY)

        logger.info(f"✅ 成功處理 {len(processed_patents)} 筆專利")
        return processed_patents

    def _build_synonym_search_query(
        self, 
        selected_keyword_groups: List[Dict[str, Any]], 
        custom_keywords: List[str]
    ) -> str:
        """
        構建帶同義詞的搜索查詢
        邏輯：(關鍵字1 OR 同義詞1-1 OR 同義詞1-2) AND (關鍵字2 OR 同義詞2-1 OR 同義詞2-2)
        """
        query_parts = []

        # 處理關鍵字組合（每組內用OR，組間用AND）
        for group in selected_keyword_groups:
            group_terms = []

            # 添加主關鍵字（如果選中）
            if group.get('keyword_selected', False):
                keyword = group.get('keyword', '')
                if keyword:
                    group_terms.append(keyword)

            # 添加選中的同義詞
            selected_synonyms = group.get('selected_synonyms', [])
            group_terms.extend(selected_synonyms)

            # 如果這組有選中的詞彙，加入查詢
            if group_terms:
                # 組內用OR連接
                group_query = " OR ".join([f'"{term}"' for term in group_terms])
                query_parts.append(f"({group_query})")
        
        # 處理自定義關鍵字
        if custom_keywords:
            custom_query = " OR ".join([f'"{kw.strip()}"' for kw in custom_keywords if kw.strip()])
            if custom_query:
                query_parts.append(f"({custom_query})")

        # 組間用AND連接
        final_query = " AND ".join(query_parts)

        return final_query

    async def _process_patents_with_batching(self, patents: List[Dict]) -> List[Dict]:
        """批次處理專利"""
        if not patents:
            return []
        
        total_patents = len(patents)
        processed_patents = []
        failed_count = 0
        
        logger.info(f"🔧 開始批次處理 {total_patents} 筆專利，批次大小: {self.BATCH_SIZE}")
        
        batch_size = self._get_optimal_batch_size(total_patents)
        
        for batch_idx in range(0, total_patents, batch_size):
            batch_end = min(batch_idx + batch_size, total_patents)
            batch_patents = patents[batch_idx:batch_end]
            batch_num = (batch_idx // batch_size) + 1
            total_batches = (total_patents + batch_size - 1) // batch_size
            
            logger.info(f"📦 處理第 {batch_num}/{total_batches} 批，專利 {batch_idx+1}-{batch_end}")
            
            batch_results = await self._process_batch_with_concurrency_control(batch_patents)
            
            successful_in_batch = sum(1 for result in batch_results if not result.get('_processing_error'))
            failed_in_batch = len(batch_results) - successful_in_batch
            failed_count += failed_in_batch
            
            processed_patents.extend(batch_results)
            
            logger.info(f"✅ 批次 {batch_num} 完成，成功: {successful_in_batch}, 失敗: {failed_in_batch}")
            
            if batch_end < total_patents:
                delay_time = self._get_dynamic_delay(failed_in_batch, len(batch_results))
                logger.info(f"⏳ 批次間休息 {delay_time:.1f} 秒...")
                await asyncio.sleep(delay_time)
        
        success_rate = ((total_patents - failed_count) / total_patents * 100) if total_patents > 0 else 0
        logger.info(f"🎯 批次處理完成，總計: {total_patents}, 成功: {total_patents - failed_count}, 失敗: {failed_count}, 成功率: {success_rate:.1f}%")
        
        return processed_patents

    def _get_optimal_batch_size(self, total_count: int) -> int:
        """根據專利總數動態調整批次大小"""
        if total_count <= 50:
            return 10
        elif total_count <= 200:
            return 15
        else:
            return 20

    def _get_dynamic_delay(self, failed_count: int, total_count: int) -> float:
        """根據失敗率動態調整延遲時間"""
        failure_rate = failed_count / total_count if total_count > 0 else 0
        
        if failure_rate > 0.3:
            return self.BATCH_DELAY * 2.0
        elif failure_rate > 0.1:
            return self.BATCH_DELAY * 1.5
        else:
            return self.BATCH_DELAY

    async def _process_batch_with_concurrency_control(self, batch_patents: List[Dict]) -> List[Dict]:
        """使用並發控制處理單個批次"""
        
        async def process_with_semaphore(patent):
            async with self.semaphore:
                await asyncio.sleep(self.REQUEST_DELAY)
                return await self._process_single_patent_with_retry(patent)
        
        tasks = [process_with_semaphore(patent) for patent in batch_patents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"處理專利失敗 (批次內索引 {i}): {result}")
                patent_with_error = batch_patents[i].copy()
                patent_with_error['_processing_error'] = str(result)
                processed_results.append(patent_with_error)
            else:
                processed_results.append(result)
        
        return processed_results

    async def _process_single_patent_with_retry(self, patent: Dict) -> Dict:
        """處理單一專利並支持重試機制"""
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                return await self._process_single_patent_simple(patent)
            except Exception as e:
                if attempt < self.MAX_RETRIES:
                    wait_time = self.RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"處理專利失敗，{wait_time:.1f}秒後重試 (嘗試 {attempt + 1}/{self.MAX_RETRIES + 1}): {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"處理專利最終失敗，已達最大重試次數: {e}")
                    raise

    async def _process_single_patent_simple(self, patent: Dict) -> Dict:
        """處理單一專利：只生成技術特徵和功效"""
        try:
            enhanced_patent = patent.copy()
            
            # 生成技術特徵和功效
            try:
                features_result = await asyncio.wait_for(
                    self._generate_tech_features_and_effects(patent),
                    timeout=60.0
                )
                
                if isinstance(features_result, Exception):
                    logger.warning(f"技術特徵生成失敗: {features_result}")
                    enhanced_patent['technical_features'] = ["技術特徵提取失敗"]
                    enhanced_patent['technical_effects'] = ["技術功效提取失敗"]
                else:
                    enhanced_patent['technical_features'] = features_result.get('technical_features', [])
                    enhanced_patent['technical_effects'] = features_result.get('technical_effects', [])
                    
            except asyncio.TimeoutError:
                logger.warning(f"技術特徵生成超時，使用fallback: {patent.get('title', 'Unknown')[:50]}...")
                fallback_result = self._generate_fallback_features(patent)
                enhanced_patent['technical_features'] = fallback_result.get('technical_features', [])
                enhanced_patent['technical_effects'] = fallback_result.get('technical_effects', [])
            
            return enhanced_patent
            
        except Exception as e:
            logger.error(f"處理單一專利失敗: {e}")
            patent['_processing_error'] = str(e)
            return patent

    async def _generate_tech_features_and_effects(self, patent: Dict) -> Dict:
        """生成技術特徵和功效"""
        try:
            if not self.qwen_service:
                return self._generate_fallback_features(patent)
            
            result = await self.qwen_service.generate_technical_features_and_effects(patent)
            return result
            
        except Exception as e:
            logger.warning(f"技術特徵生成失敗: {e}")
            return self._generate_fallback_features(patent)

    def _format_search_results_fixed(self, patents: List[Dict]) -> List[Dict]:
        """🔧 修復版：格式化搜索結果為前端所需格式（修復申請人和國家顯示）"""
        formatted_results = []
    
        for i, patent in enumerate(patents):
            # 🔧 修復：處理申請人信息
            applicants_raw = patent.get('applicants', 'N/A')
            if isinstance(applicants_raw, list):
                applicants_str = '; '.join(applicants_raw) if applicants_raw else 'N/A'
            else:
                applicants_str = str(applicants_raw) if applicants_raw and applicants_raw != 'N/A' else 'N/A'
            
            # 🔧 修復：處理國家信息
            country_code = patent.get('country', 'TW')
            
            # 國家代碼到顯示名稱的映射
            country_display_mapping = {
                'TW': 'TW',
                'US': 'US',
                'JP': 'JP',
                'EP': 'EP',
                'KR': 'KR',
                'CN': 'CN',
                'WO': 'WO',
                'SEA': 'SEA',
                'OTHER': '其他'
            }
            
            country_display = country_display_mapping.get(country_code, country_code)
            
            formatted_patent = {
                "序號": i + 1,
                "專利名稱": patent.get('title', 'N/A'),
                "申請人": applicants_str,  # 🔧 修復後的申請人
                "國家": country_display,   # 🔧 修復後的國家顯示
                "申請號": patent.get('application_number', 'N/A'),
                "公開公告號": patent.get('publication_number', 'N/A'),
                "摘要": patent.get('abstract', 'N/A'),
                "專利範圍": patent.get('claims', 'N/A'),
                "技術特徵": patent.get('technical_features', []),
                "技術功效": patent.get('technical_effects', []),
                
                # 🔧 新增：專利連結（根據公開公告號生成）
                "專利連結": self._generate_patent_link(patent.get('publication_number', '')),
                
                # 🔧 新增：調試信息（開發階段使用）
                "_debug_info": {
                    "raw_applicants": patent.get('applicants'),
                    "raw_country": patent.get('country'),
                    "database": patent.get('database', 'Unknown')
                }
            }
        
            if patent.get('_processing_error'):
                formatted_patent["處理狀態"] = f"部分失敗: {patent['_processing_error']}"
            
            # 🔧 記錄修復結果
            logger.debug(f"格式化專利 {i+1}: 申請人={applicants_str}, 國家={country_display}")
            
            formatted_results.append(formatted_patent)
    
        logger.info(f"✅ 完成格式化 {len(formatted_results)} 筆專利結果（申請人和國家已修復）")
        return formatted_results

    def _generate_patent_link(self, publication_number: str) -> str:
        """🔧 新增：根據公開公告號生成GPSS專利連結"""
        if not publication_number or publication_number == 'N/A':
            return ''
        
        # GPSS專利詳細頁面連結格式
        base_url = "https://tiponet.tipo.gov.tw/gpss4/gpsskmc/gpssbkm"
        return f"{base_url}?!!FRURL{publication_number}"

    def _extract_fallback_keywords(self, description: str) -> List[str]:
        """fallback關鍵字提取"""
        keywords = []
    
        tech_terms = {
            '測試': 'test', '檢測': 'inspection', '自動化': 'automation',
            '控制': 'control', '精密': 'precision', '半導體': 'semiconductor',
            '探針': 'probe', '系統': 'system', '機械': 'mechanical'
        }

        description_lower = description.lower()
        for chinese, english in tech_terms.items():
            if chinese in description or english in description_lower:
                keywords.append(chinese)

        if not keywords:
            keywords = ['測試', '系統', '控制', '精密', '自動化']

        return keywords[:5]

    def _generate_fallback_features(self, patent: Dict) -> Dict:
        """生成fallback技術特徵和功效"""
        title = patent.get('title', '')
    
        features = []
        effects = []
    
        if '測試' in title:
            features.append('測試功能模組')
            effects.append('提升測試效率')
        if '自動' in title:
            features.append('自動化控制系統')
            effects.append('減少人工操作')
        if '控制' in title:
            features.append('精密控制機制')
            effects.append('提高控制精度')

        if not features:
            features = ['創新技術設計']
            effects = ['技術性能提升']

        return {
            'technical_features': features,
            'technical_effects': effects,
            'source': 'fallback'
        }

    def get_processing_stats(self) -> Dict:
        """獲取處理統計信息"""
        return {
            "batch_size": self.BATCH_SIZE,
            "batch_delay": self.BATCH_DELAY,
            "max_concurrent_requests": self.MAX_CONCURRENT_REQUESTS,
            "request_delay": self.REQUEST_DELAY,
            "max_retries": self.MAX_RETRIES,
            "retry_delay": self.RETRY_DELAY,
            "initialized": self.initialized,
            "verified_api_keys": len(self.verified_api_keys),
            "classification_enabled": False,
            "confidence_tracking": False,
            "applicant_country_fixed": True,  # 🔧 標記已修復申請人和國家問題
            "features": ["qwen_keywords", "tech_features", "gpss_search", "excel_processing", "applicant_country_fix"]
        }

    # Excel處理相關方法保持不變...
    async def process_excel_batch_analysis(
        self,
        excel_file_content: bytes,
        filename: str = "unknown.xlsx"
    ) -> Dict[str, Any]:
        """處理Excel檔案批量分析"""
        start_time = time.time()
        session_id = str(uuid.uuid4())
        
        try:
            logger.info(f"📊 開始處理Excel批量分析: {filename}, 大小: {len(excel_file_content)} bytes")
            
            if not self.initialized:
                await self.initialize()
            
            # 步驟1: 解析Excel檔案
            try:
                df = pd.read_excel(BytesIO(excel_file_content))
                logger.info(f"📋 Excel解析成功，共 {len(df)} 行資料")
            except Exception as e:
                raise Exception(f"Excel檔案解析失敗: {str(e)}")
            
            # 步驟2: 驗證必要欄位並標準化欄位名稱
            df_processed = self._validate_and_normalize_excel_columns(df)
            
            # 步驟3: 資料清理和預處理
            df_cleaned = self._clean_excel_data(df_processed)
            
            if len(df_cleaned) == 0:
                raise Exception("Excel檔案中沒有有效的專利資料")
            
            # 步驟4: 限制處理數量
            max_records = 500
            if len(df_cleaned) > max_records:
                df_cleaned = df_cleaned.head(max_records)
                logger.warning(f"⚠️ Excel資料超過{max_records}筆，只處理前{max_records}筆")
            
            # 步驟5: 批量處理專利分析
            analysis_results = await self._process_excel_patents_batch(
                df_cleaned, session_id
            )
            
            # 步驟6: 統計分析結果
            stats = self._calculate_excel_analysis_stats(analysis_results)
            
            execution_time = time.time() - start_time
            
            logger.info(f"✅ Excel批量分析完成，耗時: {execution_time:.2f}秒")
            
            return {
                "success": True,
                "session_id": session_id,
                "filename": filename,
                "total_count": len(df),
                "processed_count": stats["success_count"],
                "failed_count": stats["error_count"],
                "results": analysis_results["success_results"],
                "errors": analysis_results["error_messages"][:10],
                "statistics": stats,
                "execution_time": execution_time,
                "message": f"Excel分析完成，成功處理 {stats['success_count']} 筆專利資料"
            }
            
        except Exception as e:
            logger.error(f"❌ Excel批量分析失敗: {e}")
            return {
                "success": False,
                "session_id": session_id,
                "filename": filename,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    def _validate_and_normalize_excel_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """驗證並標準化Excel欄位名稱"""
        required_columns = ['公開公告號', '專利名稱', '摘要', '專利範圍']
        
        column_mapping = {
            'publication_number': '公開公告號',
            'patent_number': '公開公告號',
            'pub_no': '公開公告號',
            'patent_id': '公開公告號',
            
            'title': '專利名稱',
            'patent_title': '專利名稱',
            'name': '專利名稱',
            'patent_name': '專利名稱',
            
            'abstract': '摘要',
            'summary': '摘要',
            'description': '摘要',
            
            'claims': '專利範圍',
            'patent_claims': '專利範圍',
            'claim': '專利範圍',
            'patent_scope': '專利範圍'
        }
        
        missing_columns = []
        df_columns = df.columns.tolist()
        
        for required_col in required_columns:
            if required_col not in df_columns:
                missing_columns.append(required_col)
        
        if missing_columns:
            rename_dict = {}
            for english_col, chinese_col in column_mapping.items():
                if english_col in df_columns and chinese_col in missing_columns:
                    rename_dict[english_col] = chinese_col
                    missing_columns.remove(chinese_col)
            
            if rename_dict:
                df = df.rename(columns=rename_dict)
                logger.info(f"🔄 欄位映射: {rename_dict}")
        
        if missing_columns:
            raise Exception(f"Excel檔案缺少必要欄位: {missing_columns}")
        
        return df
    
    def _clean_excel_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理Excel資料"""
        df = df.dropna(subset=['公開公告號', '專利名稱'], how='all')
        
        df['摘要'] = df['摘要'].fillna('')
        df['專利範圍'] = df['專利範圍'].fillna('')
        
        df = df[
            (df['公開公告號'].notna()) & 
            (df['專利名稱'].notna()) &
            (df['公開公告號'].astype(str).str.strip() != '') &
            (df['專利名稱'].astype(str).str.strip() != '')
        ]
        
        df = df.reset_index(drop=True)
        
        logger.info(f"📋 資料清理完成，有效資料: {len(df)} 筆")
        return df
    
    async def _process_excel_patents_batch(
        self, 
        df: pd.DataFrame, 
        session_id: str
    ) -> Dict[str, Any]:
        """批量處理Excel中的專利資料"""
        success_results = []
        error_messages = []
        
        batch_size = 20
        total_batches = (len(df) + batch_size - 1) // batch_size
        
        logger.info(f"🔧 開始批量處理 {len(df)} 筆專利，分為 {total_batches} 批")
        
        for batch_idx in range(0, len(df), batch_size):
            batch_end = min(batch_idx + batch_size, len(df))
            batch_df = df.iloc[batch_idx:batch_end]
            batch_num = (batch_idx // batch_size) + 1
            
            logger.info(f"📦 處理第 {batch_num}/{total_batches} 批，專利 {batch_idx+1}-{batch_end}")
            
            batch_results = await self._process_single_excel_batch(
                batch_df, session_id, batch_idx
            )
            
            for result in batch_results:
                if result.get('error'):
                    error_messages.append(result['error'])
                else:
                    success_results.append(result)
            
            if batch_end < len(df):
                await asyncio.sleep(0.3)
        
        return {
            "success_results": success_results,
            "error_messages": error_messages
        }
    
    async def _process_single_excel_batch(
        self, 
        batch_df: pd.DataFrame, 
        session_id: str, 
        start_index: int
    ) -> List[Dict]:
        """處理單個Excel批次"""
        tasks = []
        
        for idx, row in batch_df.iterrows():
            patent_data = {
                'title': str(row.get('專利名稱', '')).strip() if pd.notna(row.get('專利名稱')) else '',
                'abstract': str(row.get('摘要', '')).strip() if pd.notna(row.get('摘要')) else '',
                'claims': str(row.get('專利範圍', '')).strip() if pd.notna(row.get('專利範圍')) else '',
                'publication_number': str(row.get('公開公告號', '')).strip() if pd.notna(row.get('公開公告號')) else '',
                'excel_row_index': start_index + idx + 2,
                'sequence_number': start_index + idx + 1
            }
            
            task = self._process_single_excel_patent_with_semaphore(patent_data, session_id)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"處理Excel專利失敗 (批次內索引 {i}): {result}")
                processed_results.append({
                    'error': f"第 {start_index + i + 2} 行處理失敗: {str(result)}"
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _process_single_excel_patent_with_semaphore(
        self, 
        patent_data: Dict, 
        session_id: str
    ) -> Dict:
        """使用信號量控制並發的單專利處理"""
        async with self.semaphore:
            await asyncio.sleep(self.REQUEST_DELAY)
            return await self._process_single_excel_patent(patent_data, session_id)
    
    async def _process_single_excel_patent(self, patent_data: Dict, session_id: str) -> Dict:
        """處理單個Excel專利資料"""
        try:
            if not patent_data['title'] or not patent_data['publication_number']:
                return {
                    'error': f"第 {patent_data['excel_row_index']} 行資料不完整 (缺少專利名稱或公開公告號)"
                }
        
            try:
                features_result = await asyncio.wait_for(
                    self._generate_tech_features_and_effects(patent_data),
                    timeout=60.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"第 {patent_data['excel_row_index']} 行技術特徵生成超時")
                features_result = self._generate_fallback_features(patent_data)
            except Exception as e:
                logger.warning(f"第 {patent_data['excel_row_index']} 行技術特徵生成失敗: {e}")
                features_result = self._generate_fallback_features(patent_data)

            result = {
                "序號": patent_data['sequence_number'],
                "專利名稱": patent_data['title'],
                "公開公告號": patent_data['publication_number'],
                "摘要": self._truncate_text(patent_data['abstract'], 500),
                "專利範圍": self._truncate_text(patent_data['claims'], 500),
                "技術特徵": features_result.get('technical_features', []),
                "技術功效": features_result.get('technical_effects', []),
                "分析方法": features_result.get('source', 'unknown'),
                "session_id": session_id,
                "原始行號": patent_data['excel_row_index']
            }

            return result

        except Exception as e:
            logger.error(f"處理第 {patent_data.get('excel_row_index', 'unknown')} 行專利失敗: {e}")
            return {
                'error': f"第 {patent_data.get('excel_row_index', 'unknown')} 行處理失敗: {str(e)}"
            }
    
    def _calculate_excel_analysis_stats(self, analysis_results: Dict) -> Dict:
        """計算Excel分析統計"""
        success_results = analysis_results["success_results"]
        error_messages = analysis_results["error_messages"]
    
        success_count = len(success_results)
        error_count = len(error_messages)
        total_count = success_count + error_count
    
        analysis_methods = {"qwen_api": 0, "fallback": 0, "other": 0}
    
        if success_results:
            for result in success_results:
                method = result.get('分析方法', 'other')
                if method in analysis_methods:
                    analysis_methods[method] += 1
                else:
                    analysis_methods["other"] += 1

        return {
            "success_count": success_count,
            "error_count": error_count,
            "total_count": total_count,
            "success_rate": (success_count / total_count * 100) if total_count > 0 else 0,
            "analysis_methods": analysis_methods
        }

    def _truncate_text(self, text: str, max_length: int) -> str:
        """截斷文本到指定長度"""
        if not text:
            return ""
        
        text = str(text).strip()
        if len(text) <= max_length:
            return text
        
        return text[:max_length-3] + "..."
    
    def get_excel_processing_stats(self) -> Dict:
        """獲取Excel處理統計信息"""
        return {
            "max_file_size_mb": 10,
            "max_records": 500,
            "supported_formats": [".xlsx", ".xls"],
            "required_columns": ["公開公告號", "專利名稱", "摘要", "專利範圍"],
            "batch_size": self.BATCH_SIZE,
            "processing_stats": self.get_processing_stats(),
            "classification_enabled": False,
            "applicant_country_fixed": True  # 🔧 標記已修復
        }

# 單例實例
improved_patent_processing_service = ImprovedPatentProcessingService()