import asyncio
import aiohttp
import logging
import json
import re
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class QwenAPIService:
    """Qwen API服務類 - 優化版本"""
    
    def __init__(self, api_url: str = "http://10.4.16.36:8001"):
        self.api_url = api_url
        self.model_name = "Qwen2.5-72B-Instruct"
        self.session = None
        self.total_api_calls = 0
        self.successful_calls = 0
        self.json_parse_failures = 0
        
        # 新增：優化配置參數
        self.request_timeout = 180.0    # 3分鐘總超時
        self.connection_timeout = 30.0  # 30秒連接超時
        self.max_retries = 3           # 最大重試次數
        self.base_retry_delay = 2.0    # 基礎重試延遲
        self.max_tokens_keywords = 400  # 關鍵字生成token限制
        self.max_tokens_features = 800  # 技術特徵生成token限制

    async def initialize(self):
        """初始化 aiohttp session - 優化版本"""
        if self.session is None:
            # 優化超時設置
            timeout = aiohttp.ClientTimeout(
                total=self.request_timeout,      # 總超時
                connect=self.connection_timeout, # 連接超時
                sock_read=60.0                  # socket讀取超時
            )
            
            # 優化連接器設置
            connector = aiohttp.TCPConnector(
                limit=20,              # 增加連接池大小
                limit_per_host=8,      # 每主機連接數
                ttl_dns_cache=300,     # DNS緩存時間
                use_dns_cache=True,
                keepalive_timeout=30,  # 保持連接時間
                enable_cleanup_closed=True
            )
            
            self.session = aiohttp.ClientSession(
                timeout=timeout, 
                connector=connector,
                headers={
                    'User-Agent': 'Patent-Search-System/1.0',
                    'Connection': 'keep-alive'
                }
            )
            logger.info(f"Qwen API服務已初始化 - 連接到: {self.api_url}")
            logger.info(f"超時配置: 總超時={self.request_timeout}s, 連接超時={self.connection_timeout}s")

    async def close(self):
        """關閉session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def generate_keywords_from_description(self, description: str, num_keywords: int = 5) -> Dict:
        """
        從技術描述生成關鍵字 - 移除信心度
        返回: {"keywords": [...]}
        """
        try:
            # 限制描述長度以避免超時
            description = self._truncate_text(description, 1500)
            prompt = self._build_keyword_generation_prompt(description, num_keywords)

            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是專業的專利技術分析專家，擅長從技術描述中提取關鍵字用於專利檢索。請嚴格按照JSON格式回答，不要添加任何額外解釋。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": self.max_tokens_keywords,
                "stream": False,
                "top_p": 0.8,
                "frequency_penalty": 0.1,
                "presence_penalty": 0.1
            }

            # 使用帶重試的API調用
            result = await self._call_qwen_api_with_retry(payload, operation="關鍵字生成")

            if result.get('success', False):
                parsed_data = self._parse_json_response(result['content'])
                if parsed_data and 'keywords' in parsed_data:
                    keywords = parsed_data['keywords'][:num_keywords]
                    # 驗證關鍵字質量
                    validated_keywords = self._validate_keywords(keywords, description)
                    return {
                        "keywords": validated_keywords,
                        "source": "qwen_api"
                    }

            # Fallback
            logger.warning("Qwen關鍵字生成失敗，使用fallback方法")
            return self._generate_keywords_fallback(description, num_keywords)

        except Exception as e:
            logger.error(f"關鍵字生成失敗: {e}")
            return self._generate_keywords_fallback(description, num_keywords)

    async def generate_keywords_with_synonyms(self, description: str, num_keywords: int = 3, num_synonyms: int = 5) -> Dict:
        """
        從技術描述生成關鍵字和對應的同義詞
        返回: {
            "keywords_with_synonyms": [
                {
                    "keyword": "主關鍵字",
                    "synonyms": ["同義詞1", "同義詞2", "同義詞3"]
                }
            ]
        }
        """
        try:
            # 限制描述長度
            description = self._truncate_text(description, 1500)
            prompt = self._build_keyword_synonyms_generation_prompt(description, num_keywords, num_synonyms)

            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是專業的專利技術分析專家，擅長從技術描述中提取關鍵字及其同義詞用於專利檢索。請嚴格按照JSON格式回答，不要添加任何額外解釋。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": self.max_tokens_keywords * 2,  # 增加token數量以容納同義詞
                "stream": False,
                "top_p": 0.8,
                "frequency_penalty": 0.1,
                "presence_penalty": 0.1
            }

            # 使用帶重試的API調用
            result = await self._call_qwen_api_with_retry(payload, operation="關鍵字和同義詞生成")

            if result.get('success', False):
                parsed_data = self._parse_json_response(result['content'])
                if parsed_data and 'keywords_with_synonyms' in parsed_data:
                    keywords_data = parsed_data['keywords_with_synonyms'][:num_keywords]
                    # 驗證和清理數據
                    validated_data = self._validate_keywords_with_synonyms(keywords_data, description)
                    return {
                        "keywords_with_synonyms": validated_data,
                        "source": "qwen_api"
                    }

            # Fallback
            logger.warning("Qwen關鍵字和同義詞生成失敗，使用fallback方法")
            return self._generate_keywords_synonyms_fallback(description, num_keywords, num_synonyms)

        except Exception as e:
            logger.error(f"關鍵字和同義詞生成失敗: {e}")
            return self._generate_keywords_synonyms_fallback(description, num_keywords, num_synonyms)

    async def generate_technical_features_and_effects(self, patent_data: Dict) -> Dict:
        try:
            # 組合專利內容並限制長度
            title = patent_data.get('title', '')
            abstract = patent_data.get('abstract', '')
            claims = patent_data.get('claims', '')
        
            # 智能文本預處理，限制總長度
            processed_content = self._prepare_patent_text_for_processing(title, abstract, claims)

            if not processed_content.strip():
                logger.warning("專利內容為空，使用fallback方法")
                return self._generate_features_fallback(patent_data)

            # 構建優化的提示詞
            prompt = self._build_tech_features_prompt_optimized(title, abstract[:1000], claims[:1000])

            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是專業的專利技術分析專家，擅長從專利內容中提取技術特徵和功效。請仔細分析專利內容，識別核心技術特徵和實際效果。你必須嚴格按照要求的JSON格式回答。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": self.max_tokens_features,
                "stream": False,
                "top_p": 0.8
            }

            # 使用帶重試的API調用
            result = await self._call_qwen_api_with_retry(payload, operation="技術特徵生成")

            if result.get('success', False):
                parsed_data = self._parse_json_response(result['content'])
                if parsed_data and 'technical_features' in parsed_data:
                    # 後處理結果，確保質量
                    features = self._post_process_features(parsed_data.get('technical_features', []))
                    effects = self._post_process_effects(parsed_data.get('technical_effects', []))

                    return {
                        "technical_features": features[:5],  # 最多5個特徵
                        "technical_effects": effects[:5],    # 最多5個功效
                        "source": "qwen_api"
                    }

            # Fallback
            logger.warning("Qwen技術特徵生成失敗，使用fallback方法")
            return self._generate_features_fallback(patent_data)

        except Exception as e:
            logger.error(f"技術特徵生成失敗: {e}")
            return self._generate_features_fallback(patent_data)

    async def _call_qwen_api_with_retry(self, payload: Dict, operation: str = "API調用") -> Dict:
        """調用Qwen API並支持重試機制"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # 記錄嘗試次數
                if attempt > 0:
                    logger.info(f"{operation} - 重試第 {attempt} 次")
                
                result = await self._call_qwen_api(payload)
                
                if result.get('success', False):
                    if attempt > 0:
                        logger.info(f"{operation} - 重試成功")
                    return result
                else:
                    # API調用失敗但沒有異常
                    error_msg = result.get('error', 'Unknown error')
                    last_exception = Exception(f"{operation}失敗: {error_msg}")
                    
                    # 如果是429錯誤（限流），增加等待時間
                    if '429' in error_msg or 'rate limit' in error_msg.lower():
                        wait_time = self.base_retry_delay * (3 ** attempt)  # 針對限流使用更長等待
                        logger.warning(f"API限流，等待 {wait_time:.1f} 秒後重試...")
                        await asyncio.sleep(wait_time)
                        continue
                    
            except asyncio.TimeoutError as e:
                last_exception = e
                logger.warning(f"{operation} - API調用超時 (嘗試 {attempt + 1}/{self.max_retries + 1})")
                
            except aiohttp.ClientError as e:
                last_exception = e
                logger.warning(f"{operation} - 網絡錯誤 (嘗試 {attempt + 1}/{self.max_retries + 1}): {e}")
                
            except Exception as e:
                last_exception = e
                logger.warning(f"{operation} - API調用異常 (嘗試 {attempt + 1}/{self.max_retries + 1}): {e}")
            
            # 如果不是最後一次嘗試，等待後重試
            if attempt < self.max_retries:
                wait_time = self.base_retry_delay * (2 ** attempt)  # 指數退避
                logger.info(f"等待 {wait_time:.1f} 秒後重試...")
                await asyncio.sleep(wait_time)
        
        # 所有重試都失敗
        logger.error(f"{operation} - 最終失敗，已達最大重試次數: {last_exception}")
        return {"success": False, "error": str(last_exception)}

    async def _call_qwen_api(self, payload: Dict) -> Dict:
        """調用Qwen API - 基礎方法"""
        self.total_api_calls += 1
        
        try:
            if not self.session:
                await self.initialize()
            
            # 記錄請求詳情（僅在DEBUG模式）
            logger.debug(f"發送Qwen API請求，payload大小: {len(str(payload))} 字符")
            
            async with self.session.post(
                f"{self.api_url}/v1/chat/completions",
                json=payload,
                headers={'Content-Type': 'application/json'}
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    self.successful_calls += 1
                    
                    if 'choices' in data and len(data['choices']) > 0:
                        content = data['choices'][0]['message']['content']
                        usage = data.get('usage', {})
                        
                        # 記錄使用情況（僅在DEBUG模式）
                        logger.debug(f"API調用成功，使用token: {usage.get('total_tokens', 'N/A')}")
                        
                        return {
                            "success": True,
                            "content": content,
                            "usage": usage
                        }
                    else:
                        logger.error(f"API回應格式異常: {data}")
                        return {"success": False, "error": "Invalid response format"}
                        
                elif response.status == 429:
                    # 限流錯誤，特殊處理
                    error_text = await response.text()
                    logger.warning("API限流，請求過於頻繁")
                    return {"success": False, "error": f"Rate limit exceeded: {error_text}"}
                    
                elif response.status >= 500:
                    # 服務器錯誤
                    error_text = await response.text()
                    logger.error(f"服務器錯誤 - Status: {response.status}")
                    return {"success": False, "error": f"Server error {response.status}: {error_text}"}
                    
                else:
                    error_text = await response.text()
                    logger.error(f"API請求失敗 - Status: {response.status}, Error: {error_text}")
                    return {"success": False, "error": f"HTTP {response.status}: {error_text}"}
                    
        except asyncio.TimeoutError:
            logger.error("API請求超時")
            raise  # 重新拋出以便重試機制處理
        except aiohttp.ClientError as e:
            logger.error(f"網絡連接錯誤: {e}")
            raise
        except Exception as e:
            logger.error(f"API調用異常: {e}")
            raise

    async def generate_keywords_with_synonyms(self, description: str, num_keywords: int = 3, num_synonyms: int = 5) -> Dict:
        try:
            # 限制描述長度
            description = self._truncate_text(description, 1500)
            prompt = self._build_keyword_synonyms_generation_prompt(description, num_keywords, num_synonyms)

            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": f'''
                        你是一位資深的技術關鍵詞提取專家。你的任務是：
                            - 從用戶提供的技術描述中，抽取最具檢索價值的核心關鍵字，且**關鍵字本身的語言**必須與技術描述的語言保持一致。
                            - 為每個關鍵字生成指定數量的同義詞（技術別名、對應詞、相關技術詞彙），且**同義詞本身的語言**必須與技術描述的語言保持一致。
                            - 同義詞要避免過於通用的詞彙，如「系統」「方法」等。
                            請嚴格按照JSON格式回答，不要添加任何額外解釋。'''
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": self.max_tokens_keywords * 2,  # 增加token數量以容納同義詞
                "stream": False,
                "top_p": 0.8,
                "frequency_penalty": 0.1,
                "presence_penalty": 0.1
            }

            # 使用帶重試的API調用
            result = await self._call_qwen_api_with_retry(payload, operation="關鍵字和同義詞生成")

            if result.get('success', False):
                parsed_data = self._parse_json_response(result['content'])
                if parsed_data and 'keywords_with_synonyms' in parsed_data:
                    keywords_data = parsed_data['keywords_with_synonyms'][:num_keywords]
                    # 驗證和清理數據
                    validated_data = self._validate_keywords_with_synonyms(keywords_data, description)
                    return {
                        "keywords_with_synonyms": validated_data,
                        "source": "qwen_api"
                    }

            # Fallback
            logger.warning("Qwen關鍵字和同義詞生成失敗，使用fallback方法")
            return self._generate_keywords_synonyms_fallback(description, num_keywords, num_synonyms)

        except Exception as e:
            logger.error(f"關鍵字和同義詞生成失敗: {e}")
            return self._generate_keywords_synonyms_fallback(description, num_keywords, num_synonyms)

    def _validate_keywords_with_synonyms(self, keywords_data: List[Dict], original_description: str) -> List[Dict]:
        """驗證和優化關鍵字及同義詞質量"""
        validated = []
        description_lower = original_description.lower()

        for item in keywords_data:
            if not isinstance(item, dict) or 'keyword' not in item:
                continue
                
            keyword = item.get('keyword', '').strip()
            synonyms = item.get('synonyms', [])

            if not keyword or len(keyword.strip()) < 2:
                continue
                
            # 過濾太通用的主關鍵字
            generic_words = ['系統', 'system', '方法', 'method', '裝置', 'device', '技術', 'technology']
            if keyword.lower() in generic_words:
                continue
                
            # 清理和驗證同義詞
            cleaned_synonyms = []
            for synonym in synonyms:
                if isinstance(synonym, str) and len(synonym.strip()) >= 2:
                    synonym = synonym.strip()
                    if synonym != keyword and synonym not in cleaned_synonyms:
                        cleaned_synonyms.append(synonym)

            validated.append({
                "keyword": keyword,
                "synonyms": cleaned_synonyms[:5]  # 限制同義詞數量
            })

        return validated

    def _generate_keywords_synonyms_fallback(self, description: str, num_keywords: int, num_synonyms: int) -> Dict:
        """Fallback方法生成關鍵字和同義詞"""
        # 基本的技術詞彙對應表
        tech_synonyms = {
            "測試": ["test", "檢測", "測量", "檢驗", "驗證"],
            "控制": ["control", "控制器", "調節", "管理", "操控"],
            "自動化": ["automation", "自動", "智能化", "無人化", "機械化"],
            "半導體": ["semiconductor", "晶片", "IC", "芯片", "電子元件"],
            "探針": ["probe", "測試針", "探測器", "檢測器", "測試頭"],
            "精密": ["precision", "精確", "高精度", "微米級", "準確"],
            "系統": ["system", "設備", "裝置", "機台", "平台"],
            "處理": ["processing", "處理器", "加工", "操作", "運算"]
        }

        # 從描述中提取關鍵詞
        keywords_found = []
        for main_word, synonyms in tech_synonyms.items():
            if main_word in description:
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

    def _prepare_patent_text_for_processing(self, title: str, abstract: str, claims: str) -> str:
        """準備專利文本用於處理，智能限制長度以避免超時"""
        # 清理和截斷文本
        title = self._clean_text(title or "")[:200]
        abstract = self._clean_text(abstract or "")[:1000]
        claims = self._clean_text(claims or "")[:800]
        
        # 組合文本
        combined = f"{title} {abstract} {claims}".strip()
        
        # 最終長度限制（確保不會超過API限制）
        if len(combined) > 2000:
            combined = combined[:2000]
            logger.debug("專利文本已截斷以避免超時")
        
        return combined

    def _clean_text(self, text: str) -> str:
        """清理文本，移除多餘空白和特殊字符"""
        if not text:
            return ""
        
        # 移除多餘的空白字符
        text = re.sub(r'\s+', ' ', text)
        # 移除特殊的控制字符
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        return text.strip()

    def _truncate_text(self, text: str, max_length: int) -> str:
        """智能截斷文本，保持語義完整性"""
        if len(text) <= max_length:
            return text
        
        # 嘗試在句號、逗號或空格處截斷
        truncated = text[:max_length]
        for delimiter in ['.', '。', ',', '，', ' ']:
            last_pos = truncated.rfind(delimiter)
            if last_pos > max_length * 0.8:  # 只要保留80%以上內容就可以
                return text[:last_pos + 1]
        
        # 如果找不到合適的截斷點，直接截斷
        return text[:max_length]

    def _build_keyword_synonyms_generation_prompt(self, description: str, num_keywords: int, num_synonyms: int) -> str:
        """構建關鍵字和同義詞生成的prompt"""
        return f"""
請根據以下技術描述，生成 {num_keywords} 個最重要的技術關鍵字，每個關鍵字配搭 {num_synonyms} 個同義詞。

技術描述：
{description}

要求：
1. 關鍵字應該是技術核心概念，具有檢索價值
2. 同義詞包括：技術別名、**英文**對應詞、相關技術詞彙
3. 避免過於通用的詞彙（如"系統"、"方法"）
4. 重點關注專業技術術語

請嚴格按照以下JSON格式回答：
{{
    "keywords_with_synonyms": [
        {{
            "keyword": "主關鍵字1",
            "synonyms": ["同義詞1", "同義詞2", "同義詞3", "同義詞4", "同義詞5"]
        }},
        {{
            "keyword": "主關鍵字2", 
            "synonyms": ["同義詞1", "同義詞2", "同義詞3", "同義詞4", "同義詞5"]
        }},
        {{
            "keyword": "主關鍵字3",
            "synonyms": ["同義詞1", "同義詞2", "同義詞3", "同義詞4", "同義詞5"]
        }}
    ]
}}
"""

    def _validate_keywords(self, keywords: List[str], original_description: str) -> List[str]:
        """驗證和優化關鍵字質量"""
        validated = []
        description_lower = original_description.lower()
        
        for kw in keywords:
            if not kw or len(kw.strip()) < 2:
                continue
            
            kw = kw.strip()
            
            # 過濾太通用的詞
            generic_words = ['系統', 'system', '方法', 'method', '裝置', 'device', '技術', 'technology', '設備', 'equipment']
            if kw.lower() in generic_words:
                continue
            
            # 過濾太長的句子片段
            if len(kw) > 25:
                # 嘗試提取核心詞彙
                core_terms = self._extract_core_terms(kw)
                validated.extend(core_terms)
                continue
            
            validated.append(kw)
        
        # 如果驗證後關鍵字太少，補充一些
        if len(validated) < 3:
            backup_keywords = self._extract_backup_keywords(original_description)
            for backup in backup_keywords:
                if backup not in validated and len(validated) < 5:
                    validated.append(backup)
        
        return validated[:5]

    def _extract_core_terms(self, long_text: str) -> List[str]:
        """從長文本中提取核心技術詞彙"""
        # 技術相關的關鍵詞模式
        tech_patterns = [
            r'測試|test', r'檢測|detection', r'控制|control',
            r'自動化|automation', r'精密|precision', r'智能|intelligent',
            r'半導體|semiconductor', r'探針|probe', r'系統|system'
        ]
        
        core_terms = []
        for pattern in tech_patterns:
            matches = re.findall(pattern, long_text, re.IGNORECASE)
            core_terms.extend(matches[:2])  # 每種模式最多取2個
        
        return core_terms[:3]

    def _extract_backup_keywords(self, description: str) -> List[str]:
        """從描述中提取備用關鍵字"""
        backup = []
        
        # 技術相關詞彙模式
        tech_patterns = [
            r'半導體|semiconductor', r'測試|test', r'自動化|automation',
            r'控制|control', r'檢測|detection', r'精密|precision',
            r'智能|intelligent', r'分析|analysis', r'處理|processing'
        ]
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            for match in matches:
                if match not in backup:
                    backup.append(match)
        
        return backup[:3]

    def _post_process_features(self, features: List[str]) -> List[str]:
        """後處理技術特徵，確保質量"""
        processed = []
        
        for feature in features:
            if not feature or len(feature.strip()) < 5:
                continue
            
            # 清理格式
            feature = feature.strip()
            if feature.startswith(('特徵', '功能', '1.', '2.', '3.', '-')):
                feature = re.sub(r'^[特徵功能\d\.\-\s]*[:：]?\s*', '', feature)
            
            # 限制長度
            if len(feature) > 100:
                feature = feature[:97] + "..."
            
            processed.append(feature)
        
        return processed

    def _post_process_effects(self, effects: List[str]) -> List[str]:
        """後處理技術功效，確保質量"""
        processed = []
        
        for effect in effects:
            if not effect or len(effect.strip()) < 5:
                continue
            
            # 清理格式
            effect = effect.strip()
            if effect.startswith(('功效', '效果', '1.', '2.', '3.', '-')):
                effect = re.sub(r'^[功效果\d\.\-\s]*[:：]?\s*', '', effect)
            
            # 限制長度
            if len(effect) > 100:
                effect = effect[:97] + "..."
            
            processed.append(effect)
        
        return processed

    def _build_keyword_generation_prompt(self, description: str, num_keywords: int) -> str:
        """構建關鍵字生成提示詞 - 移除信心度"""
        return f"""
請分析以下技術描述，生成{num_keywords}個最重要的技術關鍵字，這些關鍵字將用於專利檢索。

技術描述：
{description}

請嚴格按照以下JSON格式回答，只返回JSON，不要添加任何其他文字：
{{
    "keywords": ["關鍵字1", "關鍵字2", "關鍵字3", "關鍵字4", "關鍵字5"]
}}

重要要求：
1. 關鍵字應該是核心技術概念，避免太通用的詞彙
2. 每個關鍵字長度2-20個字符
3. 優先使用專業術語
4. 關鍵字要能準確反映技術特徵
5. 確保返回有效的JSON格式
"""

    def _build_tech_features_prompt_optimized(self, title: str, abstract: str, claims: str) -> str:
        """構建技術特徵和功效提取提示詞 - 移除信心度"""
        return f"""
請分析以下專利內容，提取技術特徵和技術功效。

專利標題：{title}
專利摘要：{abstract}
專利範圍：{claims}

請按照以下JSON格式回答，只返回JSON：
{{
    "technical_features": [
        "特徵1：具體的技術組成或創新點",
        "特徵2：核心技術機制或結構",
        "特徵3：關鍵技術參數或特性"
    ],
    "technical_effects": [
        "功效1：具體的技術效果或優勢",
        "功效2：性能提升或問題解決",
        "功效3：應用價值或實用效果"
    ]
}}

要求：
1. 技術特徵：專利的核心技術組成、創新點、技術機制
2. 技術功效：專利能達到的具體效果、性能提升、解決的問題
3. 每項特徵和功效要簡潔明確，每項20-50字
4. 基於實際專利內容提取，不要編造
5. 每類最多3項，確保質量
"""

    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """解析JSON格式的API回應 - 優化版本"""
        if not response_text:
            return None
        
        try:
            # 清理回應文本
            clean_text = response_text.strip()
            
            # 移除markdown代碼塊標記
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]
            elif clean_text.startswith('```'):
                clean_text = clean_text[3:]
            
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]
            
            clean_text = clean_text.strip()
            
            # 尋找JSON部分
            json_start = clean_text.find('{')
            json_end = clean_text.rfind('}')
            
            if json_start != -1 and json_end != -1 and json_end > json_start:
                json_text = clean_text[json_start:json_end+1]
                
                try:
                    parsed_data = json.loads(json_text)
                    logger.debug(f"JSON解析成功")
                    return parsed_data
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON解析失敗: {e}")
                    self.json_parse_failures += 1
            
            # 嘗試修復常見的JSON問題
            fixed_text = self._fix_common_json_issues(clean_text)
            if fixed_text:
                try:
                    parsed_data = json.loads(fixed_text)
                    logger.debug("修復後JSON解析成功")
                    return parsed_data
                except json.JSONDecodeError:
                    pass
            
            logger.warning("JSON解析完全失敗")
            return None
            
        except Exception as e:
            logger.error(f"解析回應時發生錯誤: {e}")
            return None

    def _fix_common_json_issues(self, text: str) -> Optional[str]:
        """修復常見的JSON格式問題"""
        try:
            # 移除多餘的逗號
            text = re.sub(r',\s*}', '}', text)
            text = re.sub(r',\s*]', ']', text)
            
            # 確保數組和對象正確閉合
            open_braces = text.count('{') - text.count('}')
            if open_braces > 0:
                text += '}' * open_braces
            
            open_brackets = text.count('[') - text.count(']')
            if open_brackets > 0:
                text += ']' * open_brackets
            
            return text
        except:
            return None

    def _generate_keywords_fallback(self, description: str, num_keywords: int) -> Dict:
        """Fallback關鍵字生成方法 - 移除信心度"""
        keywords = []
        description_lower = description.lower()
    
        # 預定義的技術關鍵字庫（擴展版）
        tech_keywords = {
            '測試': ['test', 'testing', '測試'],
            '檢測': ['detection', 'inspection', '檢測'],
            '自動化': ['automation', 'automatic', '自動化'],
            '控制': ['control', 'controlling', '控制'],
            '精密': ['precision', 'precise', '精密'],
            '半導體': ['semiconductor', 'wafer', '半導體', '晶圓'],
            '探針': ['probe', 'pin', '探針'],
            '機械手臂': ['handler', 'robot arm', '機械手臂'],
            '電路': ['circuit', 'pcb', '電路'],
            '介面': ['interface', 'connector', '介面'],
            '材料': ['material', 'substrate', '材料'],
            '智能': ['intelligent', 'smart', 'AI'],
            '分析': ['analysis', 'analytics', '分析']
        }

        # 檢測技術關鍵字
        for category, terms in tech_keywords.items():
            for term in terms:
                if term in description_lower:
                    if category not in keywords:
                        keywords.append(category)
                    break
                    
        # 如果關鍵字不足，添加通用關鍵字
        if len(keywords) < num_keywords:
            fallback_keywords = ['測試設備', '自動化', '控制系統', '精密測量', '檢測技術']
            for kw in fallback_keywords:
                if kw not in keywords and len(keywords) < num_keywords:
                    keywords.append(kw)

        return {
            "keywords": keywords[:num_keywords],
            "source": "fallback"
        }

    def _generate_features_fallback(self, patent_data: Dict) -> Dict:
        """Fallback技術特徵生成方法 - 移除信心度"""
        title = patent_data.get('title', '')
        abstract = patent_data.get('abstract', '')

        features = []
        effects = []

        # 基於標題和摘要的分析
        text = (title + ' ' + abstract).lower()

        # 擴展的特徵推斷規則
        feature_rules = {
            ('測試', 'test'): ('測試功能模組', '提升測試效率'),
            ('自動', 'auto'): ('自動化控制系統', '減少人工操作'),
            ('精密', 'precision'): ('精密定位機構', '提高操作精度'),
            ('控制', 'control'): ('智能控制算法', '增強系統穩定性'),
            ('檢測', 'detection'): ('檢測分析模組', '提高檢測準確性'),
            ('機械', 'mechanical'): ('機械傳動機構', '改善機械性能'),
            ('電路', 'circuit'): ('電路設計結構', '優化電路性能'),
            ('介面', 'interface'): ('介面連接機制', '提升連接可靠性')
        }

        for keywords, (feature, effect) in feature_rules.items():
            if any(kw in text for kw in keywords):
                if feature not in features:
                    features.append(feature)
                if effect not in effects:
                    effects.append(effect)

        # 如果沒有找到特徵，使用通用特徵
        if not features:
            features = ['創新技術架構', '優化設計方案', '系統整合機制']
            effects = ['技術性能提升', '應用效果改善', '運作效率增強']

        return {
            "technical_features": features[:3],
            "technical_effects": effects[:3],
            "source": "fallback"
        }

    def get_service_stats(self) -> Dict:
        """獲取服務統計資訊 - 移除信心度相關"""
        success_rate = (self.successful_calls / self.total_api_calls * 100) if self.total_api_calls > 0 else 0
        failure_rate = (self.json_parse_failures / self.total_api_calls * 100) if self.total_api_calls > 0 else 0

        return {
            "api_url": self.api_url,
            "model_name": self.model_name,
            "total_calls": self.total_api_calls,
            "successful_calls": self.successful_calls,
            "success_rate": f"{success_rate:.1f}%",
            "json_parse_failures": self.json_parse_failures,
            "json_failure_rate": f"{failure_rate:.1f}%",
            "session_active": self.session is not None,
            "confidence_tracking_removed": True,  # 標示已移除信心度追蹤
            "configuration": {
                "request_timeout": self.request_timeout,
                "connection_timeout": self.connection_timeout,
                "max_retries": self.max_retries,
                "max_tokens_keywords": self.max_tokens_keywords,
                "max_tokens_features": self.max_tokens_features
            }
        }

    # 保持向後兼容的方法
    async def generate_keywords(self, patent_data: Dict) -> List[str]:
        """向後兼容的關鍵字生成方法"""
        description = patent_data.get('abstract', '') or patent_data.get('title', '')
        result = await self.generate_keywords_from_description(description)
        return result.get('keywords', [])