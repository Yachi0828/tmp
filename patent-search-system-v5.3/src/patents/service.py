# src/patents/service.py

from typing import Dict, List
import asyncio
import time
import logging
from datetime import datetime
from src.ai_services.bert_service import PatentBERTService
from src.ai_services.qwen_service import QwenAPIService
from src.patents.search_engine import PatentSearchEngine
from src.patents.classification import PatentClassificationService

logger = logging.getLogger(__name__)

class PatentSearchService:
    def __init__(self, 
                 bert_service: PatentBERTService, 
                 qwen_service: QwenAPIService, 
                 search_engine: PatentSearchEngine):
        self.bert_service = bert_service
        self.qwen_service = qwen_service
        self.search_engine = search_engine
        self.classifier = PatentClassificationService(self.bert_service)

    async def tech_description_search(self, tech_description: str, max_results: int) -> Dict:
        """
        技術描述檢索主流程：
        1. Qwen 產生關鍵字和同義詞
        2. 擴展關鍵字列表
        3. Elasticsearch 檢索
        4. BERT 分類 + 相關性排序
        5. 統整回傳格式
        """
        start_time = time.time()
        
        try:
            # 步驟1：使用Qwen生成關鍵字和同義詞
            logger.info(f"開始技術描述檢索，描述長度: {len(tech_description)}")
            
            keywords = await self.qwen_service.generate_keywords({
                'title': '',
                'abstract': tech_description,
                'main_claim': ''
            })
            
            # 獲取包含同義詞的完整資料
            keywords_with_synonyms = await self.qwen_service.get_keywords_with_synonyms()
            
            # 擴展關鍵字列表（包含同義詞）
            expanded_keywords = []
            keyword_groups = {}  # 儲存關鍵字分組，供後續權重計算
            
            for kw_data in keywords_with_synonyms:
                main_keyword = kw_data.get('keyword', '')
                synonyms = kw_data.get('synonyms', [])
                
                if main_keyword:
                    expanded_keywords.append(main_keyword)
                    keyword_groups[main_keyword] = [main_keyword] + synonyms
                    expanded_keywords.extend(synonyms)
            
            # 去重但保持順序
            seen = set()
            unique_expanded_keywords = []
            for kw in expanded_keywords:
                if kw not in seen and kw.strip():
                    seen.add(kw)
                    unique_expanded_keywords.append(kw)
            
            logger.info(f"生成關鍵字: {keywords[:5]}")  # 只記錄前5個
            logger.info(f"擴展後關鍵字數量: {len(unique_expanded_keywords)}")
            
            # 步驟2：執行檢索
            search_keywords = unique_expanded_keywords[:20]  # 限制數量避免查詢過長
            
            patents = await self.search_engine.search_patents(
                keywords=search_keywords,
                query_text=tech_description,
                max_results=max_results * 2  # 多檢索一些，後續會過濾
            )
            
            if not patents:
                logger.warning("檢索未返回任何結果")
                return self._empty_result(tech_description, keywords, start_time)
            
            logger.info(f"檢索到 {len(patents)} 筆專利")
            
            # 步驟3：並行處理分類和相關性計算
            classified_results = await self._process_patents_parallel(
                patents, 
                tech_description, 
                keywords, 
                keyword_groups
            )
            
            # 步驟4：排序和篩選
            # 按相關性分數排序
            sorted_results = sorted(
                classified_results, 
                key=lambda x: x.get('relevance_score', 0), 
                reverse=True
            )
            
            # 只返回請求的數量
            final_results = sorted_results[:max_results]
            
            # 步驟5：生成統計資訊
            classification_stats = self._calculate_classification_stats(final_results)
            
            elapsed_time = time.time() - start_time
            logger.info(f"檢索完成，耗時: {elapsed_time:.2f}秒")
            
            return {
                "query_info": {
                    "original_description": tech_description,
                    "generated_keywords": keywords,
                    "expanded_keywords": unique_expanded_keywords[:10],  # 只返回前10個擴展關鍵字
                    "keyword_groups": keyword_groups,
                    "search_time": elapsed_time,
                    "total_processed": len(patents)
                },
                "results": final_results,
                "total_found": len(final_results),
                "classification_stats": classification_stats,
                "ai_enhanced": True,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"技術描述檢索失敗: {e}")
            return self._error_result(tech_description, str(e), time.time() - start_time)
    
    async def _process_patents_parallel(self, patents: List[Dict], 
                                      tech_description: str, 
                                      keywords: List[str],
                                      keyword_groups: Dict) -> List[Dict]:
        """並行處理專利分類和相關性計算"""
        tasks = []
        
        for patent in patents:
            task = self._process_single_patent(
                patent, 
                tech_description, 
                keywords, 
                keyword_groups
            )
            tasks.append(task)
        
        # 使用 gather 並行執行所有任務
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 過濾掉失敗的結果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"處理專利失敗 (索引 {i}): {result}")
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _process_single_patent(self, patent: Dict, 
                                   tech_description: str, 
                                   keywords: List[str],
                                   keyword_groups: Dict) -> Dict:
        """處理單一專利：分類和相關性計算"""
        try:
            # 執行 BERT 分類
            classification_result = None
            if self.bert_service and (patent.get('abstract') or patent.get('title')):
                try:
                    # 組合文本進行分類
                    text_for_classification = ' '.join(filter(None, [
                        patent.get('title', ''),
                        patent.get('abstract', ''),
                        patent.get('claims', '')[:500]  # 限制 claims 長度
                    ]))
                    
                    classification_result = await self.classifier.classify_patent_document({
                        'title': patent.get('title', ''),
                        'abstract': patent.get('abstract', ''),
                        'claims': patent.get('claims', '')
                    })
                except Exception as e:
                    logger.warning(f"BERT分類失敗: {e}")
            
            # 計算相關性分數
            relevance_score = self._calculate_relevance_score(
                tech_description, 
                patent, 
                keywords,
                keyword_groups,
                classification_result
            )
            
            # 組合結果
            result = {
                "patent_id": patent.get('id', patent.get('patent_number', '')),
                "patent_number": patent.get('patent_number', ''),
                "title": patent.get('title', ''),
                "abstract": self._truncate_text(patent.get('abstract', ''), 500),
                "applicants": self._ensure_list(patent.get('applicants', patent.get('applicant', ''))),
                "inventors": self._ensure_list(patent.get('inventors', patent.get('inventor', ''))),
                "application_date": patent.get('application_date', ''),
                "publication_date": patent.get('publication_date', ''),
                "ipc_classes": self._ensure_list(patent.get('ipc_classes', patent.get('ipc_classification', ''))),
                "country": patent.get('country', ''),
                "relevance_score": relevance_score
            }
            
            # 添加分類結果
            if classification_result:
                result["ai_classification"] = {
                    "primary_classifications": classification_result.get('primary_classifications', []),
                    "secondary_classifications": classification_result.get('secondary_classifications', []),
                    "confidence_score": classification_result.get('confidence_score', 0),
                    "method": classification_result.get('classification_method', 'BERT')
                }
            else:
                result["ai_classification"] = {
                    "primary_classifications": [],
                    "secondary_classifications": [],
                    "confidence_score": 0,
                    "method": "none"
                }
            
            return result
            
        except Exception as e:
            logger.error(f"處理專利時發生錯誤: {e}")
            # 返回基本資訊
            return {
                "patent_id": patent.get('id', 'unknown'),
                "patent_number": patent.get('patent_number', ''),
                "title": patent.get('title', ''),
                "relevance_score": 0,
                "error": str(e)
            }
    
    def _calculate_relevance_score(self, query: str, patent: Dict, 
                                 keywords: List[str], 
                                 keyword_groups: Dict,
                                 classification_result: Dict = None) -> float:
        """
        計算相關性分數，考慮多個因素：
        1. 文本相似度
        2. 關鍵字匹配度（包含同義詞）
        3. AI分類置信度
        4. 日期新穎性
        """
        scores = {}
        
        # 1. 文本相似度（使用簡化的方法）
        text_similarity = self._calculate_text_similarity(
            query,
            patent.get('title', '') + ' ' + patent.get('abstract', '')
        )
        scores['text_similarity'] = text_similarity * 0.3
        
        # 2. 關鍵字匹配度（考慮同義詞）
        keyword_score = self._calculate_keyword_match_score(
            patent, 
            keywords, 
            keyword_groups
        )
        scores['keyword_match'] = keyword_score * 0.4
        
        # 3. AI分類置信度
        if classification_result and classification_result.get('confidence_score'):
            scores['ai_confidence'] = classification_result['confidence_score'] * 0.2
        else:
            scores['ai_confidence'] = 0.1  # 預設低分
        
        # 4. 日期新穎性（越新的專利分數越高）
        date_score = self._calculate_date_score(patent)
        scores['date_relevance'] = date_score * 0.1
        
        # 計算總分
        total_score = sum(scores.values())
        
        # 記錄詳細分數（用於除錯）
        logger.debug(f"專利 {patent.get('patent_number', 'unknown')} 相關性分數: {scores}")
        
        return min(total_score, 1.0)  # 確保分數在0-1之間
    
    def _calculate_text_similarity(self, query: str, patent_text: str) -> float:
        """簡化的文本相似度計算"""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        try:
            if not query or not patent_text:
                return 0.0
            
            # 使用 TF-IDF 計算相似度
            vectorizer = TfidfVectorizer(
                max_features=100,
                ngram_range=(1, 2)
            )
            
            tfidf_matrix = vectorizer.fit_transform([query, patent_text])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return float(similarity)
            
        except Exception as e:
            logger.warning(f"文本相似度計算失敗: {e}")
            return 0.5  # 返回中等分數
    
    def _calculate_keyword_match_score(self, patent: Dict, 
                                     keywords: List[str], 
                                     keyword_groups: Dict) -> float:
        """計算關鍵字匹配分數（考慮同義詞）"""
        patent_text = ' '.join([
            patent.get('title', ''),
            patent.get('abstract', ''),
            patent.get('claims', '')[:1000]  # 限制 claims 長度
        ]).lower()
        
        if not patent_text:
            return 0.0
        
        total_score = 0.0
        matched_groups = 0
        
        # 檢查每個關鍵字組（主關鍵字及其同義詞）
        for main_keyword, synonyms in keyword_groups.items():
            group_matched = False
            group_score = 0.0
            
            # 主關鍵字匹配權重更高
            if main_keyword.lower() in patent_text:
                group_matched = True
                group_score = 1.0
            else:
                # 檢查同義詞
                for synonym in synonyms[1:]:  # 跳過第一個（主關鍵字）
                    if synonym.lower() in patent_text:
                        group_matched = True
                        group_score = max(group_score, 0.8)  # 同義詞權重稍低
            
            if group_matched:
                matched_groups += 1
                total_score += group_score
        
        # 正規化分數
        if keyword_groups:
            return (total_score / len(keyword_groups)) * (matched_groups / len(keyword_groups))
        else:
            # 如果沒有關鍵字組，使用簡單匹配
            matched = sum(1 for kw in keywords if kw.lower() in patent_text)
            return matched / max(len(keywords), 1)
    
    def _calculate_date_score(self, patent: Dict) -> float:
        """計算日期新穎性分數"""
        try:
            pub_date = patent.get('publication_date', '')
            if not pub_date:
                return 0.5
            
            # 解析日期
            from datetime import datetime
            if len(pub_date) >= 4:
                year = int(pub_date[:4])
                current_year = datetime.now().year
                
                # 最近5年內的專利得分較高
                years_old = current_year - year
                if years_old <= 0:
                    return 1.0
                elif years_old <= 2:
                    return 0.9
                elif years_old <= 5:
                    return 0.7
                elif years_old <= 10:
                    return 0.5
                else:
                    return 0.3
            
            return 0.5
            
        except Exception:
            return 0.5
    
    def _calculate_classification_stats(self, results: List[Dict]) -> Dict:
        """計算分類統計資訊"""
        stats = {
            "total_classified": 0,
            "classification_distribution": {},
            "avg_confidence": 0.0,
            "top_classifications": []
        }
        
        classification_count = {}
        total_confidence = 0.0
        classified_count = 0
        
        for result in results:
            ai_classification = result.get('ai_classification', {})
            primary_classifications = ai_classification.get('primary_classifications', [])
            
            if primary_classifications:
                classified_count += 1
                total_confidence += ai_classification.get('confidence_score', 0)
                
                for cls in primary_classifications:
                    if isinstance(cls, dict):
                        cpc_code = cls.get('cpc_code', '')
                    else:
                        cpc_code = str(cls)
                    
                    if cpc_code:
                        classification_count[cpc_code] = classification_count.get(cpc_code, 0) + 1
        
        stats['total_classified'] = classified_count
        stats['classification_distribution'] = classification_count
        
        if classified_count > 0:
            stats['avg_confidence'] = total_confidence / classified_count
        
        # 找出最常見的分類
        if classification_count:
            sorted_classifications = sorted(
                classification_count.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            stats['top_classifications'] = [
                {"code": code, "count": count} 
                for code, count in sorted_classifications[:5]
            ]
        
        return stats
    
    def _ensure_list(self, value) -> List[str]:
        """確保值是列表格式"""
        if isinstance(value, list):
            return value
        elif isinstance(value, str):
            # 處理可能的分隔符
            if ';' in value:
                return [v.strip() for v in value.split(';') if v.strip()]
            elif ',' in value:
                return [v.strip() for v in value.split(',') if v.strip()]
            else:
                return [value] if value else []
        else:
            return []
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """截斷文本到指定長度"""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    def _empty_result(self, query: str, keywords: List[str], start_time: float) -> Dict:
        """返回空結果"""
        return {
            "query_info": {
                "original_description": query,
                "generated_keywords": keywords,
                "expanded_keywords": [],
                "keyword_groups": {},
                "search_time": time.time() - start_time,
                "total_processed": 0
            },
            "results": [],
            "total_found": 0,
            "classification_stats": {
                "total_classified": 0,
                "classification_distribution": {},
                "avg_confidence": 0.0,
                "top_classifications": []
            },
            "ai_enhanced": True,
            "timestamp": datetime.now().isoformat(),
            "message": "未找到相關專利"
        }
    
    def _error_result(self, query: str, error_msg: str, elapsed_time: float) -> Dict:
        """返回錯誤結果"""
        return {
            "query_info": {
                "original_description": query,
                "generated_keywords": [],
                "expanded_keywords": [],
                "keyword_groups": {},
                "search_time": elapsed_time,
                "total_processed": 0
            },
            "results": [],
            "total_found": 0,
            "classification_stats": {},
            "ai_enhanced": False,
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "message": "檢索過程發生錯誤"
        }

    async def log_search_history(self, user_id: str, search_type: str, query_data: Dict):
        """記錄檢索歷史（需要實作）"""
        # TODO: 實作檢索歷史記錄功能
        logger.info(f"記錄檢索歷史 - 用戶: {user_id}, 類型: {search_type}")
        pass