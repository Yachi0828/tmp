# src/patents/schemas.py
'''
SearchResultResponse 中的 query_info 是否需要更詳細欄位（如 request_id、執行耗時等）？
若未來要擴充分頁功能，是否要在回傳結構中加入 page、size、pages？
'''
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

class SearchType(str, Enum):
    SIMPLE = "simple"
    ADVANCED = "advanced"
    SEMANTIC = "semantic"
    TECHNICAL = "technical"

class TechSearchRequest(BaseModel):
    description: str = Field(..., description="技術描述文字")
    max_results: int = Field(50, ge=1, le=1000)

class AdvancedSearchRequest(BaseModel):
    title_keywords: Optional[str] = Field(None, description="標題關鍵字")
    abstract_keywords: Optional[str] = Field(None, description="摘要關鍵字")
    claims_keywords: Optional[str] = Field(None, description="權利要求關鍵字")

    applicants: List[str] = Field(default=[], description="申請人列表")
    inventors: List[str] = Field(default=[], description="發明人列表")

    patent_numbers: List[str] = Field(default=[], description="專利號列表")
    publication_numbers: List[str] = Field(default=[], description="公開號列表")
    ipc_classes: List[str] = Field(default=[], description="IPC 分類列表")
    cpc_classes: List[str] = Field(default=[], description="CPC 分類列表")

    application_date_from: Optional[datetime] = None
    application_date_to: Optional[datetime] = None
    publication_date_from: Optional[datetime] = None
    publication_date_to: Optional[datetime] = None

    countries: List[str] = Field(default=[], description="國家代碼列表")

    search_type: SearchType = Field(default=SearchType.ADVANCED)
    max_results: int = Field(default=100, ge=1, le=1000)
    sort_by: str = Field(default="relevance", description="排序欄位")

    @field_validator("application_date_to")
    def check_dates(cls, v, info):
        """
        驗證 application_date_to 不可早於 application_date_from。
        """
        start_date = info.data.get("application_date_from")
        if v and start_date and v < start_date:
            raise ValueError("申請日結束不能早於開始")
        return v

class PatentResult(BaseModel):
    patent_id: str
    patent_number: Optional[str]
    title: Optional[str]
    abstract: Optional[str]
    applicants: List[str] = []
    inventors: List[str] = []
    application_date: Optional[datetime]
    publication_date: Optional[datetime]
    ipc_classes: List[str] = []
    ai_classification: Optional[List[Dict]] = []
    relevance_score: Optional[float] = None

class SearchResultResponse(BaseModel):
    query_info: Dict
    results: List[PatentResult]
    total_found: int
    ai_enhanced: bool

class ClassificationResponse(BaseModel):
    patent_id: str
    primary_classifications: List[str]
    secondary_classifications: List[str]
    confidence_score: float
    classification_method: str