# src/patents/search_engine.py
'''
當多個條件同時出現時，是否需要更複雜的 bool 組合邏輯？例如 must + should + filter 的比例權重調整。
若檢索結果量暴增，Elasticsearch 分頁效能是否足以支撐？是否需要使用 Scroll API 或 Search After 機制？
'''
import logging
from typing import List, Dict
from elasticsearch import AsyncElasticsearch
from src.config import settings
from src.patents.schemas import AdvancedSearchRequest

logger = logging.getLogger(__name__)

class PatentSearchEngine:
    def __init__(self):
        self.client: AsyncElasticsearch = AsyncElasticsearch(
            hosts=[settings.ELASTICSEARCH_URL],
            timeout=30,
            max_retries=3,
            retry_on_timeout=True
        )
        self.index = settings.ELASTICSEARCH_INDEX

    async def search_patents(self, keywords: List[str], query_text: str, max_results: int = 50) -> List[Dict]:
        """
        簡易技術描述檢索：使用 keywords +全文 match ，返回專利資訊（建議 field: id, patent_number, title, abstract, claims, applicants, inventors, ipc_classes, application_date, publication_date）
        """
        # 構建 should 子句的 match 關鍵字
        should_clauses = [{"match": {"abstract": kw}} for kw in keywords]
        # 可加入更複雜的多 field 檢索
        query_body = {
            "query": {
                "bool": {
                    "should": should_clauses,
                    "must": [{"match": {"abstract": query_text}}]
                }
            },
            "size": max_results
        }

        try:
            res = await self.client.search(index=self.index, body=query_body)
            hits = res["hits"]["hits"]
            patents = []
            for hit in hits:
                src = hit["_source"]
                patents.append({
                    "id": hit["_id"],
                    "patent_number": src.get("patent_number"),
                    "title": src.get("title"),
                    "abstract": src.get("abstract"),
                    "claims": src.get("claims", ""),
                    "applicants": src.get("applicants", []),
                    "inventors": src.get("inventors", []),
                    "ipc_classes": src.get("ipc_classes", []),
                    "application_date": src.get("application_date"),
                    "publication_date": src.get("publication_date")
                })
            return patents
        except Exception as e:
            logger.error(f"Elasticsearch 技術檢索失敗: {e}")
            return []

    async def advanced_search(self, request: AdvancedSearchRequest) -> List[Dict]:
        """
        高級檢索：根據 AdvancedSearchRequest 構建複合查詢
        """
        must_clauses = []
        filter_clauses = []
        should_clauses = []

        if request.title_keywords:
            must_clauses.append({"match": {"title": request.title_keywords}})
        if request.abstract_keywords:
            should_clauses.append({"match": {"abstract": request.abstract_keywords}})

        if request.applicants:
            filter_clauses.append({"terms": {"applicants": request.applicants}})
        if request.ipc_classes:
            filter_clauses.append({"terms": {"ipc_classes": request.ipc_classes}})

        # 處理日期範圍
        date_filter = {}
        if request.application_date_from or request.application_date_to:
            date_range = {}
            if request.application_date_from:
                date_range["gte"] = request.application_date_from.isoformat()
            if request.application_date_to:
                date_range["lte"] = request.application_date_to.isoformat()
            filter_clauses.append({"range": {"application_date": date_range}})

        # 組合最終查詢
        bool_query = {"must": must_clauses, "filter": filter_clauses}
        if should_clauses:
            bool_query["should"] = should_clauses

        body = {
            "query": {"bool": bool_query},
            "size": request.max_results,
            "sort": self._build_sort(request.sort_by)
        }

        try:
            res = await self.client.search(index=self.index, body=body)
            hits = res["hits"]["hits"]
            patents = []
            for hit in hits:
                src = hit["_source"]
                patents.append({
                    "id": hit["_id"],
                    "patent_number": src.get("patent_number"),
                    "title": src.get("title"),
                    "abstract": src.get("abstract"),
                    "claims": src.get("claims", ""),
                    "applicants": src.get("applicants", []),
                    "inventors": src.get("inventors", []),
                    "ipc_classes": src.get("ipc_classes", []),
                    "application_date": src.get("application_date"),
                    "publication_date": src.get("publication_date")
                })
            return patents
        except Exception as e:
            logger.error(f"Elasticsearch 高級檢索失敗: {e}")
            return []

    def _build_sort(self, sort_by: str) -> List[Dict]:
        """
        根據傳入的排序欄位決定 Elasticsearch sort 條件
        目前僅支援 relevance、application_date、publication_date
        """
        if sort_by == "application_date":
            return [{"application_date": {"order": "desc"}}]
        elif sort_by == "publication_date":
            return [{"publication_date": {"order": "desc"}}]
        else:
            # relevance 預設由 Elasticsearch 決定
            return []