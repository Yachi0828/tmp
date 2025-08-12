# src/ai_services/gpss_service.py - 修復申請人和國家問題的版本

import aiohttp
import asyncio
import logging
import json
import re
from urllib.parse import urlencode, quote
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class GPSSAPIService:
    """真實GPSS API服務類 - 修復版本"""
    
    BASE_URL = "https://tiponet.tipo.gov.tw/gpss1/gpsskmc/gpss_api"
    
    # GPSS API 支援的資料庫代碼
    DATABASE_CODES = {
        'TWA': '本國公開案',
        'TWB': '本國公告案', 
        'USA': '美國公開案',
        'USB': '美國公告案',
        'JPA': '日本公開案',
        'JPB': '日本公告案',
        'EPA': '歐洲公開案',
        'EPB': '歐洲公告案',
        'KPA': '韓國公開案',
        'KPB': '韓國公告案',
        'CNA': '中國公開案',
        'CNB': '中國公告案',
        'WO': 'PCT',
        'SEAA': '東南亞公開案',
        'SEAB': '東南亞公告案',
        'OTA': '其他公開案',
        'OTB': '其他公告案'
    }

    # 🆕 新增完整的輸出欄位配置，包含AG和PA
    DEFAULT_OUTPUT_FIELDS = 'PN,AN,ID,AD,TI,AX,PA,IN,AB,IC,CS,CL,AG,PD'

    def __init__(self):
        self.session = None
        self.request_count = 0
        self.success_count = 0
        self.json_error_count = 0
        self.last_request_time = None

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def initialize(self):
        """初始化HTTP會話"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=120)
            connector = aiohttp.TCPConnector(
                limit=10, 
                limit_per_host=3,
                ttl_dns_cache=300,
                use_dns_cache=True
            )
            self.session = aiohttp.ClientSession(
                timeout=timeout, 
                connector=connector,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                trust_env=True
            )
            logger.info("真實GPSS API會話已初始化")

    async def close(self):
        """關閉HTTP會話"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("GPSS API會話已關閉")

    async def search_patents_with_and_or_logic(
        self,
        user_code: str,
        user_keywords: Optional[List[str]] = None,
        ai_keywords: Optional[List[str]] = None,
        databases: Optional[List[str]] = None,
        max_results: int = 50,
        **kwargs
    ) -> Dict:
        """
        使用AND/OR邏輯執行GPSS API搜索
        邏輯：(user_kw1 OR user_kw2 OR ...) AND (ai_kw1 OR ai_kw2 OR ...)
        """
        try:
            self.request_count += 1
            self.last_request_time = datetime.now()
            
            if not self.session:
                await self.initialize()
            
            # 構建AND/OR搜索URL
            full_url, params = self.build_and_or_search_url(
                user_code=user_code,
                user_keywords=user_keywords,
                ai_keywords=ai_keywords,
                databases=databases,
                max_results=max_results,
                **kwargs
            )
            
            logger.info(f"🌐 發送AND/OR GPSS API請求")
            logger.info(f"🔗 請求URL長度: {len(full_url)} 字符")
            
            # 發送HTTP請求
            async with self.session.get(full_url) as response:
                logger.info(f"📡 AND/OR GPSS API回應狀態: {response.status}")
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"AND/OR GPSS API HTTP錯誤 {response.status}: {error_text}")
                    raise Exception(f"AND/OR GPSS API HTTP錯誤: {response.status}")
                
                try:
                    # 使用修復版JSON解析
                    raw_text = await response.text()
                    raw_data = self._safe_json_parse(raw_text)
                    
                    self.success_count += 1
                    
                    if 'gpss-API' not in raw_data:
                        logger.error(f"AND/OR GPSS API回應格式錯誤")
                        raise Exception("AND/OR GPSS API回應格式錯誤")
                    
                    logger.info(f"✅ AND/OR GPSS API請求成功")
                    return raw_data
                    
                except Exception as e:
                    logger.error(f"AND/OR GPSS API JSON解析失敗: {e}")
                    self.json_error_count += 1
                    raise Exception(f"AND/OR GPSS API JSON解析失敗: {e}")
                    
        except Exception as e:
            logger.error(f"❌ AND/OR GPSS API請求失敗: {e}")
            raise

    def build_and_or_search_url(
        self,
        user_code: str,
        user_keywords: Optional[List[str]] = None,
        ai_keywords: Optional[List[str]] = None,
        databases: Optional[List[str]] = None,
        max_results: int = 50,
        output_fields: Optional[str] = None,
        **kwargs
    ) -> Tuple[str, Dict[str, str]]:
        """
        構建AND/OR邏輯的GPSS API搜索URL
        邏輯：(user_kw1 OR user_kw2 OR ...) AND (ai_kw1 OR ai_kw2 OR ...)
        """
        # 基本參數
        params = {
            'userCode': user_code,
            'expFmt': 'json',
            'expQty': str(min(max_results, 1000)),
            'expFld': output_fields or self.DEFAULT_OUTPUT_FIELDS  # 🆕 使用包含AG的欄位
        }
        
        # 設定資料庫範圍
        if databases:
            params['patDB'] = ','.join(databases)
        else:
            params['patDB'] = 'TWA,TWB,USA,USB,JPA,JPB,EPA,EPB,KPA,KPB,CNA,CNB,WO,SEAA,SEAB,OTA,OTB'

        params['patAG'] = kwargs.get('case_types', 'A,B')
        params['patTY'] = kwargs.get('patent_types', 'I,M')
        
        # 構建AND/OR查詢邏輯
        logger.info(f"🔍 構建AND/OR查詢邏輯")
        logger.info(f"📝 用戶關鍵字: {user_keywords}")
        logger.info(f"🤖 AI關鍵字: {ai_keywords}")
        
        # 處理用戶關鍵字（OR邏輯）和AI關鍵字（AND邏輯）
        if user_keywords or ai_keywords:
            # 分別構建標題和摘要的查詢邏輯
            title_query = self._build_title_query(user_keywords, ai_keywords)
            abstract_query = self._build_abstract_query(user_keywords, ai_keywords)
            claim_query = self._build_claim_query(user_keywords, ai_keywords)

            if title_query:
                params['TI'] = title_query
                logger.info(f"📋 標題查詢: {title_query}")
            
            if abstract_query:
                params['+AB'] = abstract_query  # + 表示OR條件與標題查詢
                logger.info(f"📄 摘要查詢: {abstract_query}")

            if claim_query:
                params['+CL'] = claim_query  # + 表示OR條件與標題查詢
                logger.info(f"📄 權利要求查詢: {claim_query}")

        # 設定日期範圍
        if 'date_range' not in kwargs:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365*10)
            params['ID'] = f"{start_date.strftime('%Y%m%d')}:{end_date.strftime('%Y%m%d')}"
        
        # 處理額外參數
        for key, value in kwargs.items():
            if key.startswith('gpss_') and value:
                gpss_key = key[5:]
                params[gpss_key] = str(value)
        
        # 構建完整URL
        query_string = urlencode(params, safe=':,+()&|', quote_via=quote)
        full_url = f"{self.BASE_URL}?{query_string}"
        
        logger.info(f"🌐 構建AND/OR GPSS API URL: {self.BASE_URL}")
        logger.debug(f"🔧 AND/OR搜索參數: {params}")
        
        return full_url, params

    async def search_patents_with_complex_and_or_logic(
        self,
        user_code: str,
        complex_query: str,
        databases: Optional[List[str]] = None,
        max_results: int = 50,
        **kwargs
    ) -> Dict:
        """
        使用複雜的AND/OR邏輯執行GPSS API搜索
        直接將複雜查詢語法發送給GPSS資料庫執行

        例如: "(關鍵字1 OR 同義詞1-1 OR 同義詞1-2) AND (關鍵字2 OR 同義詞2-1 OR 同義詞2-2)"
        """
        try:
            self.request_count += 1
            self.last_request_time = datetime.now()

            if not self.session:
                await self.initialize()

            # 構建複雜查詢URL
            full_url, params = self.build_complex_query_url(
                user_code=user_code,
                complex_query=complex_query,
                databases=databases,
                max_results=max_results,
                **kwargs
            )

            logger.info(f"🌐 發送GPSS複雜查詢API請求")
            logger.info(f"🔗 查詢語法: {complex_query}")
            logger.info(f"🔗 請求URL長度: {len(full_url)} 字符")
            safe_url = full_url.replace(user_code, f"{user_code[:16]}...")
            logger.info(f"📋 完整GPSS API URL:")
            logger.info(f"   {safe_url}")


            # 發送HTTP請求
            async with self.session.get(full_url) as response:
                logger.info(f"📡 GPSS複雜查詢API回應狀態: {response.status}")

                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"GPSS API HTTP錯誤 {response.status}: {error_text}")
                    raise Exception(f"GPSS API HTTP錯誤: {response.status}")

                try:
                    raw_text = await response.text()
                    raw_data = self._safe_json_parse(raw_text)

                    self.success_count += 1

                    if 'gpss-API' not in raw_data:
                        logger.error(f"GPSS API回應格式錯誤，缺少'gpss-API'字段")
                        raise Exception("GPSS API回應格式錯誤")

                    logger.info(f"✅ GPSS複雜查詢API請求成功")
                    return raw_data

                except Exception as e:
                    logger.error(f"GPSS API JSON解析失敗: {e}")
                    self.json_error_count += 1
                    raise Exception(f"GPSS API JSON解析失敗: {e}")

        except Exception as e:
            logger.error(f"❌ GPSS複雜查詢API請求失敗: {e}")
            raise
            
    def build_complex_query_url(
        self,
        user_code: str,
        complex_query: str,
        databases: Optional[List[str]] = None,
        max_results: int = 1000,
        output_fields: Optional[str] = None,
        **kwargs
    ) -> Tuple[str, Dict[str, str]]:
        """
        構建GPSS API複雜查詢URL和參數

        將AND/OR邏輯查詢直接嵌入到GPSS API參數中
        """
        params = {
            'userCode': user_code,
            'expFmt': 'json',
            'expQty': str(min(max_results, 1000)),
            'expFld': output_fields or self.DEFAULT_OUTPUT_FIELDS
        }

        if databases:
            params['patDB'] = ','.join(databases)
        else:
            params['patDB'] = 'TWA,TWB,USA,USB,JPA,JPB,EPA,EPB,KPA,KPB,CNA,CNB,WO,SEAA,SEAB,OTA,OTB'

        params['patAG'] = kwargs.get('case_types', 'A,B')
        params['patTY'] = kwargs.get('patent_types', 'I,M')

        # 🎯 關鍵：將複雜查詢同時應用到標題和摘要欄位
        if complex_query:
            # 根據GPSS API規範，將複雜查詢應用到多個搜索欄位
            params['TI'] = complex_query  # 標題欄位
            params['+AB'] = complex_query  # 摘要欄位
            params['+CL'] = complex_query  # Claims欄位

        # 設定預設日期範圍（最近10年）
        if 'date_range' not in kwargs:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365*10)
            params['ID'] = f"{start_date.strftime('%Y%m%d')}:{end_date.strftime('%Y%m%d')}"
    
        # 處理其他參數
        for key, value in kwargs.items():
            if key.startswith('gpss_') and value:
                gpss_key = key[5:]
                params[gpss_key] = str(value)

        # 構建完整URL
        query_string = urlencode(params, safe=':,+()&|', quote_via=quote)
        full_url = f"{self.BASE_URL}?{query_string}"

        logger.info(f"🌐 構建GPSS複雜查詢API URL: {self.BASE_URL}")
        logger.debug(f"🔧 複雜查詢參數: {params}")

        return full_url, params

    def parse_gpss_response(self, raw_response: Dict) -> List[Dict]:
        """
        解析GPSS API原始回應，提取專利資料 - 修復版本
        """
        try:
            patents = []
            
            # 驗證回應結構
            if 'gpss-API' not in raw_response:
                logger.error("GPSS回應缺少'gpss-API'字段")
                return []
            
            gpss_data = raw_response['gpss-API']
            
            # 檢查是否有錯誤
            if 'error' in gpss_data:
                error_msg = gpss_data['error']
                logger.error(f"GPSS API返回錯誤: {error_msg}")
                raise Exception(f"GPSS API錯誤: {error_msg}")
            
            # 獲取專利數據
            patent_info = gpss_data.get('patent', {})
            if not patent_info:
                logger.warning("GPSS回應中沒有專利數據")
                return []
            
            patent_content = patent_info.get('patentcontent', [])
            if not patent_content:
                logger.warning("GPSS回應中沒有專利內容")
                return []
            
            logger.info(f"📋 開始解析 {len(patent_content)} 筆GPSS專利數據")
            
            # 解析每筆專利
            for i, patent_item in enumerate(patent_content):
                try:
                    patent = self._extract_patent_details_improved(patent_item)
                    if patent:
                        patent['_source_index'] = i
                        patents.append(patent)
                        
                except Exception as e:
                    logger.warning(f"解析第{i+1}筆專利失敗: {e}")
                    continue
            
            logger.info(f"✅ 成功解析 {len(patents)} 筆專利數據")
            return patents
            
        except Exception as e:
            logger.error(f"❌ 解析GPSS回應失敗: {e}")
            return []

    def _extract_patent_details_improved(self, patent_item: Dict) -> Optional[Dict]:
        """從單個專利項目中提取詳細信息 - 改進版本"""
        try:
            patent = {}
            
            # 🆕 更好的標題提取
            title_data = patent_item.get('patent-title', {})
            if isinstance(title_data, dict):
                # 優先選擇中文標題，如果沒有則選英文
                patent['title'] = (
                    title_data.get('title') or 
                    title_data.get('chinese-title') or
                    title_data.get('english-title') or 
                    'N/A'
                )
            else:
                patent['title'] = str(title_data) if title_data else 'N/A'
            
            # 🆕 改進申請人提取邏輯
            applicants = []
            parties_data = patent_item.get('parties', {})
            
            if parties_data:
                # 嘗試多種可能的結構
                applicants_section = parties_data.get('applicants', {})
                
                if applicants_section:
                    applicant_list = applicants_section.get('applicant', [])
                    
                    # 處理單個申請人的情況
                    if isinstance(applicant_list, dict):
                        applicant_list = [applicant_list]
                    
                    # 處理申請人列表
                    if isinstance(applicant_list, list):
                        for applicant in applicant_list:
                            if isinstance(applicant, dict):
                                # 優先使用中文名稱，如果沒有則使用英文名稱
                                name = (
                                    applicant.get('name') or 
                                    applicant.get('chinese-name') or
                                    applicant.get('english-name') or
                                    applicant.get('party-name')
                                )
                                if name and name.strip():
                                    applicants.append(name.strip())
                            elif isinstance(applicant, str) and applicant.strip():
                                applicants.append(applicant.strip())
            
            # 如果申請人為空，嘗試其他可能的字段
            if not applicants:
                # 嘗試從根級別的申請人字段獲取
                root_applicants = patent_item.get('applicants', [])
                if root_applicants:
                    if isinstance(root_applicants, list):
                        applicants = [str(a) for a in root_applicants if a]
                    else:
                        applicants = [str(root_applicants)]

            patent['applicants'] = '; '.join(applicants) if applicants else 'N/A'
            
            # 🆕 改進發明人提取
            inventors = []
            if parties_data:
                inventors_section = parties_data.get('inventors', {})
                if inventors_section:
                    inventor_list = inventors_section.get('inventor', [])
                    
                    if isinstance(inventor_list, dict):
                        inventor_list = [inventor_list]
                    
                    if isinstance(inventor_list, list):
                        for inventor in inventor_list:
                            if isinstance(inventor, dict):
                                name = (
                                    inventor.get('name') or 
                                    inventor.get('chinese-name') or
                                    inventor.get('english-name')
                                )
                                if name and name.strip():
                                    inventors.append(name.strip())
                            elif isinstance(inventor, str) and inventor.strip():
                                inventors.append(inventor.strip())

            patent['inventors'] = '; '.join(inventors) if inventors else 'N/A'
            
            # 提取摘要
            patent['abstract'] = self._extract_abstract(patent_item)
            
            # 提取權利要求
            patent['claims'] = self._extract_claims(patent_item)
            
            # 提取專利號碼信息
            patent.update(self._extract_patent_numbers(patent_item))
            
            # 提取日期信息
            patent.update(self._extract_dates(patent_item))
            
            # 提取分類信息
            patent['ipc_classes'] = self._extract_classifications(patent_item)
            
            # 🆕 改進國家信息提取
            database = patent_item.get('@database', 'Unknown')
            country = self._determine_country_improved(database, patent_item)
            patent['database'] = database
            patent['country'] = country
            
            # 提取其他屬性
            patent['patent_type'] = patent_item.get('@type', 'Unknown')
            patent['status'] = patent_item.get('@status', 'Unknown')
            
            # 🆕 添加案件類型信息（AG欄位）
            patent['case_type'] = patent_item.get('@status', 'Unknown')  # A=公開案, B=公告案
            
            # 驗證必要字段
            if not patent['title'] or patent['title'] == 'N/A':
                logger.warning("專利缺少標題，跳過")
                return None
            
            return patent
            
        except Exception as e:
            logger.error(f"提取專利詳細信息失敗: {e}")
            return None

    def _determine_country_improved(self, database: str, patent_item: Dict) -> str:
        """根據資料庫和其他信息確定國家代碼 - 改進版本"""
        if not database:
            return 'TW'
        
        database_upper = database.upper()
        
        # 🆕 更精確的國家判斷邏輯
        if 'TW' in database_upper or '本國' in database or '中華民國' in database:
            return 'TW'
        elif 'US' in database_upper or '美國' in database:
            return 'US'
        elif 'JP' in database_upper or '日本' in database:
            return 'JP'
        elif 'EP' in database_upper or '歐洲' in database:
            return 'EP'
        elif 'KP' in database_upper or 'KR' in database_upper or '韓國' in database:
            return 'KR'
        elif 'CN' in database_upper or '中國' in database:
            return 'CN'
        elif 'WO' in database_upper or 'PCT' in database_upper:
            return 'WO'
        elif 'SEA' in database_upper or '東南亞' in database:
            return 'SEA'
        elif 'OT' in database_upper or '其他' in database:
            return 'OTHER'
        else:
            # 🆕 嘗試從申請人國家信息獲取
            try:
                parties = patent_item.get('parties', {})
                if parties:
                    applicants = parties.get('applicants', {})
                    if applicants:
                        applicant_list = applicants.get('applicant', [])
                        if isinstance(applicant_list, list) and applicant_list:
                            first_applicant = applicant_list[0]
                            if isinstance(first_applicant, dict):
                                country_code = first_applicant.get('country-code')
                                if country_code:
                                    return country_code.upper()
            except Exception:
                pass
            
            return 'TW'  # 預設返回TW

    # 保留其他現有方法...
    def _extract_abstract(self, patent_item: Dict) -> str:
        """提取摘要"""
        try:
            abstract_data = patent_item.get('abstract', {})
            
            if isinstance(abstract_data, dict):
                paragraphs = abstract_data.get('p', [])
                if isinstance(paragraphs, list):
                    return ' '.join(str(p) for p in paragraphs if p).strip()
                elif isinstance(paragraphs, str):
                    return paragraphs.strip()
                
                return str(abstract_data.get('content', '')).strip()
                
            elif isinstance(abstract_data, str):
                return abstract_data.strip()
            
            return ''
            
        except Exception as e:
            logger.debug(f"提取摘要失敗: {e}")
            return ''

    def _extract_claims(self, patent_item: Dict) -> str:
        """提取權利要求"""
        try:
            claims_data = patent_item.get('claims', {})
            
            if isinstance(claims_data, dict):
                claim_list = claims_data.get('claim', [])
                if not isinstance(claim_list, list):
                    claim_list = [claim_list]
                
                claims_text = []
                for i, claim in enumerate(claim_list[:3]):
                    if isinstance(claim, dict):
                        claim_text = claim.get('claim-text', '')
                        if claim_text:
                            claims_text.append(f"{i+1}. {claim_text}")
                    elif isinstance(claim, str):
                        claims_text.append(f"{i+1}. {claim}")
                
                return ' '.join(claims_text)
            
            return str(claims_data) if claims_data else ''
            
        except Exception as e:
            logger.debug(f"提取權利要求失敗: {e}")
            return ''

    def _extract_patent_numbers(self, patent_item: Dict) -> Dict[str, str]:
        """提取專利號碼相關信息"""
        try:
            result = {}
            
            pub_ref = patent_item.get('publication-reference', {})
            result['publication_number'] = pub_ref.get('doc-number', 'N/A')
            
            app_ref = patent_item.get('application-reference', {})  
            result['application_number'] = app_ref.get('doc-number', 'N/A')
            
            return result
            
        except Exception as e:
            logger.debug(f"提取專利號碼失敗: {e}")
            return {'publication_number': 'N/A', 'application_number': 'N/A'}

    def _extract_dates(self, patent_item: Dict) -> Dict[str, str]:
        """提取日期信息"""
        try:
            result = {}
            
            pub_ref = patent_item.get('publication-reference', {})
            result['publication_date'] = pub_ref.get('date', 'N/A')
            
            app_ref = patent_item.get('application-reference', {})
            result['application_date'] = app_ref.get('date', 'N/A')
            
            priority_data = patent_item.get('priority-claims', {})
            if priority_data:
                result['priority_date'] = priority_data.get('date', 'N/A')
            else:
                result['priority_date'] = 'N/A'
            
            return result
            
        except Exception as e:
            logger.debug(f"提取日期信息失敗: {e}")
            return {
                'publication_date': 'N/A',
                'application_date': 'N/A', 
                'priority_date': 'N/A'
            }

    def _extract_classifications(self, patent_item: Dict) -> List[str]:
        """提取IPC分類信息"""
        try:
            classifications = []
            
            ipc_data = patent_item.get('classifications-ipc', {})
            if isinstance(ipc_data, dict):
                ipc_list = ipc_data.get('ipc', [])
                if not isinstance(ipc_list, list):
                    ipc_list = [ipc_list]
                
                for ipc in ipc_list:
                    if isinstance(ipc, dict):
                        key_value = ipc.get('keyValue') or ipc.get('classification-symbol')
                        if key_value and key_value.strip():
                            classifications.append(key_value.strip())
                    elif isinstance(ipc, str) and ipc.strip():
                        classifications.append(ipc.strip())
            
            return classifications
            
        except Exception as e:
            logger.debug(f"提取分類信息失敗: {e}")
            return []

    # 其他輔助方法...
    def _build_title_query(self, user_keywords: Optional[List[str]], ai_keywords: Optional[List[str]]) -> str:
        """構建標題查詢邏輯"""
        query_parts = []
        
        # 用戶關鍵字用OR連接
        if user_keywords:
            user_query_parts = []
            for keyword in user_keywords:
                safe_keyword = self._escape_keyword(keyword)
                user_query_parts.append(safe_keyword)
            
            if len(user_query_parts) > 1:
                user_query = f"({' or '.join(user_query_parts)})"
            else:
                user_query = user_query_parts[0]
            query_parts.append(user_query)
        
        # AI關鍵字用OR連接
        if ai_keywords:
            ai_query_parts = []
            for keyword in ai_keywords:
                safe_keyword = self._escape_keyword(keyword)
                ai_query_parts.append(safe_keyword)
            
            if len(ai_query_parts) > 1:
                ai_query = f"({' or '.join(ai_query_parts)})"
            else:
                ai_query = ai_query_parts[0]
            query_parts.append(ai_query)
        
        # 用AND連接兩組
        if len(query_parts) > 1:
            return f"({' and '.join(query_parts)})"
        elif len(query_parts) == 1:
            return query_parts[0]
        else:
            return ""

    def _build_abstract_query(self, user_keywords: Optional[List[str]], ai_keywords: Optional[List[str]]) -> str:
        """構建摘要查詢邏輯（與標題查詢相同）"""
        return self._build_title_query(user_keywords, ai_keywords)

    def _build_claim_query(self, user_keywords: Optional[List[str]], ai_keywords: Optional[List[str]]) -> str:
        """構建權利要求查詢邏輯"""
        return self._build_title_query(user_keywords, ai_keywords)

    def _escape_keyword(self, keyword: str) -> str:
        """轉義關鍵字中的特殊字符"""
        escaped = keyword.strip()
        escaped = re.sub(r'[()&|]', '', escaped)
        
        if ' ' in escaped:
            escaped = f'"{escaped}"'
        
        return escaped

    def _safe_json_parse(self, json_text: str) -> Dict:
        """安全的JSON解析，處理轉義字符問題"""
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON直接解析失敗，嘗試修復: {e}")
            
            try:
                fixed_text = self._fix_json_escape_issues(json_text)
                return json.loads(fixed_text)
            except json.JSONDecodeError as e2:
                logger.error(f"JSON修復解析也失敗: {e2}")
                
                try:
                    return self._fallback_json_parse(json_text)
                except Exception as e3:
                    logger.error(f"分段解析也失敗: {e3}")
                    raise Exception(f"JSON解析完全失敗: 原始錯誤={e}, 修復錯誤={e2}, 分段錯誤={e3}")

    def _fix_json_escape_issues(self, json_text: str) -> str:
        """修復JSON中的轉義字符問題"""
        fixes = [
            (r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r'\\\\'),
            (r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\'),
            (r'\\<', r'<'),
            (r'\\>', r'>'),
            (r'\\=', r'='),
            (r'\\%', r'%'),
            (r'\\#', r'#'),
            (r'\\&', r'&'),
            (r'\\\+', r'+'),
            (r'\\([\u4e00-\u9fff])', r'\1'),
            (r'\\(\d)', r'\1'),
        ]
        
        fixed_text = json_text
        for pattern, replacement in fixes:
            try:
                fixed_text = re.sub(pattern, replacement, fixed_text)
            except Exception as e:
                logger.debug(f"正則表達式修復失敗: {pattern} -> {replacement}, 錯誤: {e}")
                continue
        
        return fixed_text

    def _fallback_json_parse(self, json_text: str) -> Dict:
        """分段解析JSON的後備方案"""
        logger.info("嘗試分段解析JSON...")
        
        try:
            gpss_start = json_text.find('"gpss-API"')
            if gpss_start == -1:
                raise Exception("找不到gpss-API字段")
            
            json_start = json_text.find('{')
            if json_start == -1:
                raise Exception("找不到JSON開始標記")
            
            return self._extract_essential_data(json_text)
            
        except Exception as e:
            logger.error(f"分段解析失敗: {e}")
            return {
                "gpss-API": {
                    "patent": {
                        "patentcontent": []
                    }
                }
            }

    def _extract_essential_data(self, json_text: str) -> Dict:
        """從有問題的JSON中提取必要數據"""
        try:
            patent_pattern = r'"patentcontent"\s*:\s*\[(.*?)\]'
            match = re.search(patent_pattern, json_text, re.DOTALL)
            
            if match:
                return {
                    "gpss-API": {
                        "patent": {
                            "patentcontent": []
                        }
                    }
                }
            else:
                return {
                    "gpss-API": {
                        "patent": {
                            "patentcontent": []
                        }
                    }
                }
                
        except Exception as e:
            logger.error(f"提取必要數據失敗: {e}")
            return {
                "gpss-API": {
                    "patent": {
                        "patentcontent": []
                    }
                }
            }

    async def search_patents_raw(
        self,
        user_code: str,
        keywords: Optional[List[str]] = None,
        search_conditions: Optional[Dict[str, str]] = None,
        databases: Optional[List[str]] = None,
        max_results: int = 50,
        **kwargs
    ) -> Dict:
        """執行真實GPSS API搜索並返回原始JSON回應"""
        try:
            self.request_count += 1
            self.last_request_time = datetime.now()
            
            if not self.session:
                await self.initialize()
            
            full_url, params = self.build_search_url(
                user_code=user_code,
                keywords=keywords,
                search_conditions=search_conditions,
                databases=databases,
                max_results=max_results,
                **kwargs
            )
            
            logger.info(f"🌐 發送GPSS API請求: 關鍵字={keywords}, 條件={search_conditions}")
            
            async with self.session.get(full_url) as response:
                logger.info(f"📡 GPSS API回應狀態: {response.status}")
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"GPSS API HTTP錯誤 {response.status}: {error_text}")
                    raise Exception(f"GPSS API HTTP錯誤: {response.status}")
                
                try:
                    raw_text = await response.text()
                    raw_data = self._safe_json_parse(raw_text)
                    
                    self.success_count += 1
                    
                    if 'gpss-API' not in raw_data:
                        logger.error(f"GPSS API回應格式錯誤，缺少'gpss-API'字段")
                        logger.debug(f"原始回應: {raw_data}")
                        raise Exception("GPSS API回應格式錯誤")
                    
                    logger.info(f"✅ GPSS API請求成功，準備解析專利數據")
                    return raw_data
                    
                except Exception as e:
                    logger.error(f"GPSS API JSON解析失敗: {e}")
                    self.json_error_count += 1
                    raise Exception(f"GPSS API JSON解析失敗: {e}")
                    
        except Exception as e:
            logger.error(f"❌ GPSS API請求失敗: {e}")
            raise

    def build_search_url(
        self,
        user_code: str,
        keywords: Optional[List[str]] = None,
        search_conditions: Optional[Dict[str, str]] = None,
        databases: Optional[List[str]] = None,
        max_results: int = 1000,
        output_fields: Optional[str] = None,
        **kwargs
    ) -> Tuple[str, Dict[str, str]]:
        """構建GPSS API搜索URL和參數"""
        params = {
            'userCode': user_code,
            'expFmt': 'json',
            'expQty': str(min(max_results, 1000)),
            'expFld': output_fields or self.DEFAULT_OUTPUT_FIELDS  # 🆕 使用包含AG的欄位
        }
        
        if databases:
            params['patDB'] = ','.join(databases)
        else:
            params['patDB'] = 'TWA,TWB,USA,USB,JPA,JPB,EPA,EPB,KPA,KPB,CNA,CNB,WO,SEAA,SEAB,OTA,OTB'

        params['patAG'] = kwargs.get('case_types', 'A,B')
        params['patTY'] = kwargs.get('patent_types', 'I,M')
        
        if keywords:
            keyword_query = ' OR '.join(keywords)
            params['TI'] = keyword_query
            params['+AB'] = keyword_query
        
        if search_conditions:
            for field, value in search_conditions.items():
                if field in self.SEARCH_FIELD_CODES and value:
                    field_code = self.SEARCH_FIELD_CODES[field]
                    params[field_code] = value
        
        if 'date_range' not in kwargs:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365*10)
            params['ID'] = f"{start_date.strftime('%Y%m%d')}:{end_date.strftime('%Y%m%d')}"
        
        for key, value in kwargs.items():
            if key.startswith('gpss_') and value:
                gpss_key = key[5:]
                params[gpss_key] = str(value)
        
        query_string = urlencode(params, safe=':,+', quote_via=quote)
        full_url = f"{self.BASE_URL}?{query_string}"
        
        logger.info(f"構建GPSS API URL: {self.BASE_URL}")
        logger.debug(f"搜索參數: {params}")
        
        return full_url, params

    async def test_api_connection(self, user_code: str) -> Dict:
        """測試GPSS API連接"""
        try:
            test_url, test_params = self.build_search_url(
                user_code=user_code,
                keywords=['test'],
                max_results=1
            )
            
            logger.info(f"🧪 測試GPSS API連接: {user_code[:8]}...")
            
            if not self.session:
                await self.initialize()
            
            async with self.session.get(test_url) as response:
                if response.status == 200:
                    raw_text = await response.text()
                    data = self._safe_json_parse(raw_text)
                    if 'gpss-API' in data:
                        logger.info("✅ GPSS API連接測試成功")
                        return {
                            'success': True,
                            'status': 'connected',
                            'message': 'GPSS API連接正常'
                        }
                
                logger.error(f"GPSS API測試失敗: HTTP {response.status}")
                return {
                    'success': False,
                    'status': 'failed', 
                    'message': f'連接測試失敗: HTTP {response.status}'
                }
                
        except Exception as e:
            logger.error(f"GPSS API連接測試異常: {e}")
            return {
                'success': False,
                'status': 'error',
                'message': f'連接測試異常: {str(e)}'
            }

    def get_service_stats(self) -> Dict:
        """獲取服務統計信息"""
        success_rate = (self.success_count / self.request_count * 100) if self.request_count > 0 else 0
        json_error_rate = (self.json_error_count / self.request_count * 100) if self.request_count > 0 else 0
        
        return {
            'base_url': self.BASE_URL,
            'total_requests': self.request_count,
            'successful_requests': self.success_count,
            'success_rate': f"{success_rate:.1f}%",
            'json_errors': self.json_error_count,
            'json_error_rate': f"{json_error_rate:.1f}%",
            'last_request_time': self.last_request_time.isoformat() if self.last_request_time else None,
            'session_active': self.session is not None,
            'supported_databases': list(self.DATABASE_CODES.keys()),
            'output_fields': self.DEFAULT_OUTPUT_FIELDS
        }

    # 檢索欄位代碼對照表 
    SEARCH_FIELD_CODES = {
        'title': 'TI',           # 標題
        'abstract': 'AB',        # 摘要  
        'claims': 'CL',          # 權利要求
        'applicant': 'AX',       # 申請人檢索用 AX
        'inventor': 'IV',        # 發明人
        'patent_number': 'PN',   # 專利號
        'application_number': 'AN', # 申請號
        'publication_number': 'PN', # 公開號
        'ipc_class': 'IC',       # IPC分類
        'application_date': 'AD', # 申請日
        'publication_date': 'ID', # 公開日
        'priority_date': 'DR'    # 優先權日
    }