# src/database.py - 增強版資料庫模組

import asyncio
import logging
import json
import hashlib
import uuid
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, func, select, JSON
from datetime import datetime
from src.config import settings
from datetime import timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# 創建異步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True
)

# 創建會話工廠
async_session_maker = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

class Base(DeclarativeBase):
    """數據庫基類"""
    pass

class SearchHistory(Base):
    """搜索歷史表"""
    __tablename__ = "search_history"
    
    id = Column(Integer, primary_key=True, index=True)
    search_type = Column(String(50), nullable=False)  # tech_description, condition, excel_analysis
    query_text = Column(Text, nullable=True)
    search_params = Column(Text, nullable=True)  # JSON格式
    results_count = Column(Integer, default=0)
    execution_time = Column(Float, default=0.0)
    user_code_hash = Column(String(64), nullable=True)  # 加密後的用戶代碼
    created_at = Column(DateTime, default=datetime.utcnow)

class PatentCache(Base):
    """專利緩存表"""
    __tablename__ = "patent_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    patent_number = Column(String(100), unique=True, index=True)
    title = Column(Text, nullable=True)
    abstract = Column(Text, nullable=True)
    claims = Column(Text, nullable=True)
    applicants = Column(Text, nullable=True)  # JSON格式
    technical_features = Column(Text, nullable=True)  # JSON格式 - 技術特徵
    technical_effects = Column(Text, nullable=True)   # JSON格式 - 技術功效
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 🆕 新增：技術描述查詢歷史表
class TechQueryHistory(Base):
    """技術描述查詢歷史表"""
    __tablename__ = "tech_query_history"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), nullable=False, index=True, unique=True)
    tech_description = Column(Text, nullable=False)  # 原始技術描述
    generated_keywords = Column(JSON, nullable=True)  # Qwen生成的關鍵字
    selected_keywords = Column(JSON, nullable=True)   # 用戶選擇的關鍵字
    custom_keywords = Column(JSON, nullable=True)     # 用戶自定義關鍵字
    final_keywords = Column(JSON, nullable=True)      # 最終使用的關鍵字
    search_logic = Column(String(20), default='traditional')  # traditional, and_or
    results_count = Column(Integer, default=0)
    execution_time = Column(Float, default=0.0)
    user_code_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# 🆕 新增：檢索結果暫存表
class SearchResultCache(Base):
    """檢索結果暫存表 - 用於問答功能"""
    __tablename__ = "search_result_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), nullable=False, index=True)  # 會話ID
    search_type = Column(String(50), nullable=False)  # tech_description, condition, excel_analysis
    patent_sequence = Column(Integer, nullable=False)  # 專利序號
    patent_title = Column(Text, nullable=True)         # 專利名稱
    patent_number = Column(String(100), nullable=True) # 公開公告號
    applicants = Column(Text, nullable=True)           # 申請人
    country = Column(String(10), nullable=True)        # 國家
    abstract = Column(Text, nullable=True)             # 摘要
    claims = Column(Text, nullable=True)               # 專利範圍
    technical_features = Column(JSON, nullable=True)   # 技術特徵
    technical_effects = Column(JSON, nullable=True)    # 技術功效
    full_data = Column(JSON, nullable=True)            # 完整數據（JSON格式）
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)       # 過期時間（7天後）

# 🆕 新增：問答歷史表
class QAHistory(Base):
    """問答歷史表"""
    __tablename__ = "qa_history"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), nullable=False, index=True)  # 關聯的檢索會話ID
    question = Column(Text, nullable=False)                      # 用戶問題
    answer = Column(Text, nullable=True)                         # QWEN回答
    referenced_patents = Column(JSON, nullable=True)             # 引用的專利序號列表
    execution_time = Column(Float, default=0.0)                 # 執行時間
    created_at = Column(DateTime, default=datetime.utcnow)

class UserFeedback(Base):
    """用戶反饋表"""
    __tablename__ = "user_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    tech_description = Column(Text, nullable=False)
    tech_description_hash = Column(String(64), nullable=False, index=True)
    generated_keywords = Column(Text, nullable=True)  # JSON格式：Qwen生成的關鍵字
    selected_keywords = Column(Text, nullable=True)   # JSON格式：用戶選擇的關鍵字
    custom_keywords = Column(Text, nullable=True)     # JSON格式：用戶自定義關鍵字
    final_keywords = Column(Text, nullable=True)      # JSON格式：最終使用的關鍵字
    search_results_count = Column(Integer, default=0)  # 搜索結果數量
    execution_time = Column(Float, default=0.0)       # 執行時間
    satisfaction_score = Column(Integer, nullable=True)  # 滿意度評分(1-5)
    user_comment = Column(Text, nullable=True)        # 用戶評論
    created_at = Column(DateTime, default=datetime.utcnow)

class KeywordQuality(Base):
    """關鍵字質量評估表"""
    __tablename__ = "keyword_quality"
    
    id = Column(Integer, primary_key=True, index=True)
    tech_description_hash = Column(String(64), nullable=False, index=True)
    generated_keyword = Column(String(100), nullable=False, index=True)
    selected_by_user = Column(Boolean, default=False)
    selection_count = Column(Integer, default=0)
    rejection_count = Column(Integer, default=0)
    quality_score = Column(Float, default=0.5)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

async def init_db():
    """初始化資料庫"""
    try:
        logger.info("🗄️ 開始初始化增強版資料庫...")
        
        # 創建所有表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ 增強版資料庫初始化完成")
        logger.info("🆕 新增功能：檢索歷史存儲、結果暫存、問答功能")
        
    except Exception as e:
        logger.error(f"❌ 資料庫初始化失敗: {e}")
        raise

async def get_db_session():
    """獲取資料庫會話"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

async def close_db():
    """關閉資料庫連接"""
    await engine.dispose()
    logger.info("🔚 資料庫連接已關閉")

class DatabaseManager:
    """增強版資料庫管理器"""
    
    @staticmethod
    def _hash_text(text: str) -> str:
        """生成文本的MD5 hash"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    @staticmethod
    async def save_search_history(
        search_type: str,
        query_text: str = None,
        search_params: dict = None,
        results_count: int = 0,
        execution_time: float = 0.0,
        user_code_hash: str = None
    ):
        """保存搜索歷史"""
        try:
            async with async_session_maker() as session:
                history = SearchHistory(
                    search_type=search_type,
                    query_text=query_text,
                    search_params=json.dumps(search_params, ensure_ascii=False) if search_params else None,
                    results_count=results_count,
                    execution_time=execution_time,
                    user_code_hash=user_code_hash
                )
                session.add(history)
                await session.commit()
                logger.debug(f"搜索歷史已保存: {search_type}")
        except Exception as e:
            logger.error(f"保存搜索歷史失敗: {e}")

    # 🆕 新增：保存技術描述查詢歷史
    @staticmethod
    async def save_tech_query_history(
        session_id: str,
        tech_description: str,
        generated_keywords: list,
        selected_keywords: list,
        custom_keywords: list,
        final_keywords: list,
        search_logic: str,
        results_count: int,
        execution_time: float,
        user_code_hash: str = None
    ):
        """保存技術描述查詢歷史"""
        try:
            async with async_session_maker() as session:
                tech_query = TechQueryHistory(
                    session_id=session_id,
                    tech_description=tech_description,
                    generated_keywords=generated_keywords,
                    selected_keywords=selected_keywords,
                    custom_keywords=custom_keywords,
                    final_keywords=final_keywords,
                    search_logic=search_logic,
                    results_count=results_count,
                    execution_time=execution_time,
                    user_code_hash=user_code_hash
                )
                session.add(tech_query)
                await session.commit()
                logger.info(f"技術描述查詢歷史已保存: {session_id}")
        except Exception as e:
            logger.error(f"保存技術描述查詢歷史失敗: {e}")

   # 修改 database.py 中的 save_search_results_to_cache 方法

    # 修改 database.py 中的 save_search_results_to_cache 方法

    @staticmethod
    async def save_search_results_to_cache(
        session_id: str,
        search_type: str,
        results: list,
        expires_days: int = 7
    ):
        """保存檢索結果到暫存，按搜尋類型分別保存"""
        try:
            async with async_session_maker() as session:
                expires_at = datetime.utcnow() + timedelta(days=expires_days)

                # 🆕 修改：只刪除相同搜尋類型的舊數據，不是全部刪除
                existing_results = await session.execute(
                    select(SearchResultCache)
                    .where(SearchResultCache.session_id == session_id)
                    .where(SearchResultCache.search_type == search_type)  # 🔧 加入搜尋類型條件
                )
            
                for result in existing_results.scalars():
                    await session.delete(result)

                # 保存新結果
                for i, result in enumerate(results):
                    cache_entry = SearchResultCache(
                        session_id=session_id,
                        search_type=search_type,
                        patent_sequence=result.get('序號', i + 1),
                        patent_title=result.get('專利名稱', ''),
                        patent_number=result.get('公開公告號', ''),
                        applicants=result.get('申請人', ''),
                        country=result.get('國家', ''),
                        abstract=result.get('摘要', ''),
                        claims=result.get('專利範圍', ''),
                        technical_features=result.get('技術特徵', []),
                        technical_effects=result.get('技術功效', []),
                        full_data=result,
                        expires_at=expires_at
                    )
                    session.add(cache_entry)

                await session.commit()
                logger.info(f"檢索結果已暫存: {session_id}, 類型: {search_type}, {len(results)} 筆專利")

        except Exception as e:
            logger.error(f"保存檢索結果到暫存失敗: {e}")

    # 🆕 新增：根據搜尋類型獲取暫存結果
    @staticmethod
    async def get_cached_search_results_by_type(
        session_id: str, 
        search_type: str = None
    ) -> List[Dict]:
        """根據搜尋類型獲取暫存結果"""
        try:
            async with async_session_maker() as session:
                query = select(SearchResultCache)\
                    .where(SearchResultCache.session_id == session_id)\
                    .where(SearchResultCache.expires_at > datetime.utcnow())

                if search_type:
                    query = query.where(SearchResultCache.search_type == search_type)

                query = query.order_by(SearchResultCache.search_type, SearchResultCache.patent_sequence)

                result = await session.execute(query)
                cached_results = result.scalars().all()

                if not cached_results:
                    logger.info(f"未找到有效的暫存結果: {session_id}, 類型: {search_type}")
                    return []

                # 轉換為字典格式
                results = []
                for cache_entry in cached_results:
                    if cache_entry.full_data:
                        # 🆕 加入搜尋類型標記
                        result_data = cache_entry.full_data.copy()
                        result_data['_search_type'] = cache_entry.search_type
                        results.append(result_data)
                    else:
                    # 從個別欄位重建
                        results.append({
                            '序號': cache_entry.patent_sequence,
                            '專利名稱': cache_entry.patent_title,
                            '公開公告號': cache_entry.patent_number,
                            '申請人': cache_entry.applicants,
                            '國家': cache_entry.country,
                            '摘要': cache_entry.abstract,
                            '專利範圍': cache_entry.claims,
                            '技術特徵': cache_entry.technical_features or [],
                            '技術功效': cache_entry.technical_effects or [],
                            '_search_type': cache_entry.search_type  # 🆕 標記搜尋類型
                        })

                logger.info(f"獲取暫存結果: {session_id}, 類型: {search_type or '全部'}, {len(results)} 筆專利")
                return results

        except Exception as e:
            logger.error(f"獲取暫存檢索結果失敗: {e}")
            return []

    # 🆕 新增：獲取可用的搜尋類型
    @staticmethod
    async def get_available_search_types(session_id: str) -> List[str]:
        """獲取該session可用的搜尋類型"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(SearchResultCache.search_type)
                    .where(SearchResultCache.session_id == session_id)
                    .where(SearchResultCache.expires_at > datetime.utcnow())
                    .distinct()
                )

                search_types = [row[0] for row in result.all()]
                return search_types

        except Exception as e:
            logger.error(f"獲取可用搜尋類型失敗: {e}")
            return []

    # 🆕 新增：獲取暫存的檢索結果
    @staticmethod
    async def get_cached_search_results(session_id: str) -> List[Dict]:
        """獲取暫存的檢索結果"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(SearchResultCache)
                    .where(SearchResultCache.session_id == session_id)
                    .where(SearchResultCache.expires_at > datetime.utcnow())
                    .order_by(SearchResultCache.patent_sequence)
                )
                
                cached_results = result.scalars().all()
                
                if not cached_results:
                    logger.info(f"未找到有效的暫存結果: {session_id}")
                    return []
                
                # 轉換為字典格式
                results = []
                for cache_entry in cached_results:
                    if cache_entry.full_data:
                        results.append(cache_entry.full_data)
                    else:
                        # 從個別欄位重建
                        results.append({
                            '序號': cache_entry.patent_sequence,
                            '專利名稱': cache_entry.patent_title,
                            '公開公告號': cache_entry.patent_number,
                            '申請人': cache_entry.applicants,
                            '國家': cache_entry.country,
                            '摘要': cache_entry.abstract,
                            '專利範圍': cache_entry.claims,
                            '技術特徵': cache_entry.technical_features or [],
                            '技術功效': cache_entry.technical_effects or []
                        })
                
                logger.info(f"獲取暫存結果: {session_id}, {len(results)} 筆專利")
                return results
                
        except Exception as e:
            logger.error(f"獲取暫存檢索結果失敗: {e}")
            return []

    # 🆕 新增：根據序號獲取特定專利
    @staticmethod
    async def get_patent_by_sequence(session_id: str, sequence: int) -> Optional[Dict]:
        """根據序號獲取特定專利"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(SearchResultCache)
                    .where(SearchResultCache.session_id == session_id)
                    .where(SearchResultCache.patent_sequence == sequence)
                    .where(SearchResultCache.expires_at > datetime.utcnow())
                )
                
                cache_entry = result.scalar_one_or_none()
                
                if cache_entry:
                    if cache_entry.full_data:
                        return cache_entry.full_data
                    else:
                        return {
                            '序號': cache_entry.patent_sequence,
                            '專利名稱': cache_entry.patent_title,
                            '公開公告號': cache_entry.patent_number,
                            '申請人': cache_entry.applicants,
                            '國家': cache_entry.country,
                            '摘要': cache_entry.abstract,
                            '專利範圍': cache_entry.claims,
                            '技術特徵': cache_entry.technical_features or [],
                            '技術功效': cache_entry.technical_effects or []
                        }
                
                return None
                
        except Exception as e:
            logger.error(f"根據序號獲取專利失敗: {e}")
            return None

    # 🆕 新增：保存問答歷史
    @staticmethod
    async def save_qa_history(
        session_id: str,
        question: str,
        answer: str,
        referenced_patents: List[int] = None,
        execution_time: float = 0.0
    ):
        """保存問答歷史"""
        try:
            async with async_session_maker() as session:
                qa_entry = QAHistory(
                    session_id=session_id,
                    question=question,
                    answer=answer,
                    referenced_patents=referenced_patents or [],
                    execution_time=execution_time
                )
                session.add(qa_entry)
                await session.commit()
                logger.info(f"問答歷史已保存: {session_id}")
                
        except Exception as e:
            logger.error(f"保存問答歷史失敗: {e}")

    # 🆕 新增：獲取問答歷史
    @staticmethod
    async def get_qa_history(session_id: str, limit: int = 10) -> List[Dict]:
        """獲取問答歷史"""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(QAHistory)
                    .where(QAHistory.session_id == session_id)
                    .order_by(QAHistory.created_at.desc())
                    .limit(limit)
                )
                
                qa_entries = result.scalars().all()
                
                history = []
                for entry in reversed(qa_entries):  # 反轉以時間順序排列
                    history.append({
                        'question': entry.question,
                        'answer': entry.answer,
                        'referenced_patents': entry.referenced_patents,
                        'execution_time': entry.execution_time,
                        'created_at': entry.created_at.isoformat()
                    })
                
                return history
                
        except Exception as e:
            logger.error(f"獲取問答歷史失敗: {e}")
            return []

    # 🆕 新增：清理過期的暫存結果
    @staticmethod
    async def cleanup_expired_cache():
        """清理過期的暫存結果"""
        try:
            async with async_session_maker() as session:
                # 刪除過期的搜索結果暫存
                result = await session.execute(
                    select(SearchResultCache)
                    .where(SearchResultCache.expires_at <= datetime.utcnow())
                )
                expired_entries = result.scalars().all()
                
                for entry in expired_entries:
                    await session.delete(entry)
                
                await session.commit()
                
                if expired_entries:
                    logger.info(f"清理了 {len(expired_entries)} 筆過期的暫存結果")
                
        except Exception as e:
            logger.error(f"清理過期暫存失敗: {e}")

    # 保留原有方法...
    @staticmethod
    async def cache_patent(patent_data: dict):
        """緩存專利數據"""
        try:
            async with async_session_maker() as session:
                patent_number = patent_data.get('publication_number')
                if not patent_number:
                    return
                
                # 查找現有記錄
                result = await session.execute(
                    select(PatentCache).where(PatentCache.patent_number == patent_number)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # 更新現有記錄
                    existing.title = patent_data.get('title')
                    existing.abstract = patent_data.get('abstract')
                    existing.claims = patent_data.get('claims')
                    existing.technical_features = json.dumps(patent_data.get('technical_features', []), ensure_ascii=False)
                    existing.technical_effects = json.dumps(patent_data.get('technical_effects', []), ensure_ascii=False)
                    existing.updated_at = datetime.utcnow()
                else:
                    # 創建新記錄
                    cache_entry = PatentCache(
                        patent_number=patent_number,
                        title=patent_data.get('title'),
                        abstract=patent_data.get('abstract'),
                        claims=patent_data.get('claims'),
                        applicants=json.dumps(patent_data.get('applicants', []), ensure_ascii=False),
                        technical_features=json.dumps(patent_data.get('technical_features', []), ensure_ascii=False),
                        technical_effects=json.dumps(patent_data.get('technical_effects', []), ensure_ascii=False)
                    )
                    session.add(cache_entry)
                
                await session.commit()
                logger.debug(f"專利緩存已更新: {patent_number}")
                
        except Exception as e:
            logger.error(f"緩存專利數據失敗: {e}")

    @staticmethod
    async def save_user_feedback(
        session_id: str,
        tech_description: str,
        generated_keywords: list,
        selected_keywords: list,
        custom_keywords: list,
        final_keywords: list,
        search_results_count: int = 0,
        execution_time: float = 0.0,
        satisfaction_score: int = None,
        user_comment: str = None
    ):
        """保存用戶反饋數據"""
        try:
            async with async_session_maker() as session:
                tech_hash = DatabaseManager._hash_text(tech_description)
                
                feedback = UserFeedback(
                    session_id=session_id,
                    tech_description=tech_description,
                    tech_description_hash=tech_hash,
                    generated_keywords=json.dumps(generated_keywords, ensure_ascii=False),
                    selected_keywords=json.dumps(selected_keywords, ensure_ascii=False),
                    custom_keywords=json.dumps(custom_keywords, ensure_ascii=False),
                    final_keywords=json.dumps(final_keywords, ensure_ascii=False),
                    search_results_count=search_results_count,
                    execution_time=execution_time,
                    satisfaction_score=satisfaction_score,
                    user_comment=user_comment
                )
                session.add(feedback)
                await session.commit()
                logger.info(f"用戶反饋已保存: session_id={session_id}")
                
                # 同時更新關鍵字質量數據
                await DatabaseManager._update_keyword_quality(
                    tech_description, generated_keywords, selected_keywords
                )
                
        except Exception as e:
            logger.error(f"保存用戶反饋失敗: {e}")
    
    @staticmethod
    async def _update_keyword_quality(
        tech_description: str, 
        generated_keywords: list, 
        selected_keywords: list
    ):
        """更新關鍵字質量統計"""
        try:
            desc_hash = DatabaseManager._hash_text(tech_description)
            
            async with async_session_maker() as session:
                for keyword in generated_keywords:
                    # 查找現有記錄
                    result = await session.execute(
                        select(KeywordQuality).where(
                            KeywordQuality.tech_description_hash == desc_hash,
                            KeywordQuality.generated_keyword == keyword
                        )
                    )
                    quality_record = result.scalar_one_or_none()
                    
                    if quality_record:
                        # 更新現有記錄
                        if keyword in selected_keywords:
                            quality_record.selection_count += 1
                            quality_record.selected_by_user = True
                        else:
                            quality_record.rejection_count += 1
                        
                        # 重新計算質量分數
                        total = quality_record.selection_count + quality_record.rejection_count
                        quality_record.quality_score = quality_record.selection_count / total if total > 0 else 0.5
                        quality_record.updated_at = datetime.utcnow()
                    else:
                        # 創建新記錄
                        selected = keyword in selected_keywords
                        quality_record = KeywordQuality(
                            tech_description_hash=desc_hash,
                            generated_keyword=keyword,
                            selected_by_user=selected,
                            selection_count=1 if selected else 0,
                            rejection_count=0 if selected else 1,
                            quality_score=1.0 if selected else 0.0
                        )
                        session.add(quality_record)
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"更新關鍵字質量失敗: {e}")

    @staticmethod
    async def get_feedback_statistics():
        """獲取反饋統計數據"""
        try:
            async with async_session_maker() as session:
                stats = {}
                
                # 統計總反饋數量
                total_feedback_result = await session.execute(
                    select(func.count(UserFeedback.id))
                )
                stats["total_feedback"] = total_feedback_result.scalar()
                
                # 獲取關鍵字質量統計
                keyword_quality_result = await session.execute(
                    select(
                        func.avg(KeywordQuality.quality_score),
                        func.count(KeywordQuality.id)
                    )
                )
                avg_quality, keyword_count = keyword_quality_result.first()
                stats["keyword_quality"] = {
                    "average_score": float(avg_quality) if avg_quality else 0.0,
                    "total_keywords": keyword_count
                }
                
                # 獲取技術描述查詢統計
                tech_query_result = await session.execute(
                    select(
                        func.count(TechQueryHistory.id),
                        func.avg(TechQueryHistory.execution_time),
                        func.avg(TechQueryHistory.results_count)
                    )
                )
                total_queries, avg_time, avg_results = tech_query_result.first()
                stats["tech_queries"] = {
                    "total_queries": total_queries or 0,
                    "average_execution_time": float(avg_time) if avg_time else 0.0,
                    "average_results_count": float(avg_results) if avg_results else 0.0
                }
                
                # 獲取問答統計
                qa_result = await session.execute(
                    select(
                        func.count(QAHistory.id),
                        func.avg(QAHistory.execution_time)
                    )
                )
                total_qa, avg_qa_time = qa_result.first()
                stats["qa_interactions"] = {
                    "total_questions": total_qa or 0,
                    "average_response_time": float(avg_qa_time) if avg_qa_time else 0.0
                }
                
                return stats
                
        except Exception as e:
            logger.error(f"獲取反饋統計失敗: {e}")
            return {}

    @staticmethod
    async def get_search_statistics():
        """獲取搜索統計"""
        try:
            async with async_session_maker() as session:
                # 統計搜索類型分布
                search_type_result = await session.execute(
                    select(SearchHistory.search_type, func.count(SearchHistory.id))
                    .group_by(SearchHistory.search_type)
                )
                
                search_distribution = {
                    row[0]: row[1] for row in search_type_result.fetchall()
                }
                
                # 統計平均執行時間
                avg_time_result = await session.execute(
                    select(
                        SearchHistory.search_type,
                        func.avg(SearchHistory.execution_time)
                    ).group_by(SearchHistory.search_type)
                )
                
                avg_execution_times = {
                    row[0]: float(row[1]) if row[1] else 0.0 
                    for row in avg_time_result.fetchall()
                }
                
                return {
                    "search_distribution": search_distribution,
                    "average_execution_times": avg_execution_times
                }
                
        except Exception as e:
            logger.error(f"獲取搜索統計失敗: {e}")
            return {}

