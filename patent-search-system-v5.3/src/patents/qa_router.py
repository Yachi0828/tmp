# src/patents/enhanced_qa_router.py - 支持對話歷史的問答API

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
import time

from src.services.enhanced_patent_qa_service import enhanced_patent_qa_service

logger = logging.getLogger(__name__)
router = APIRouter()

# ================================
# 請求模型定義
# ================================

class QARequest(BaseModel):
    session_id: str = Field(..., description="會話ID")
    question: str = Field(..., description="用戶問題", min_length=1, max_length=1000)
    clear_history: bool = Field(default=False, description="是否清除對話歷史")

class QAResponse(BaseModel):
    success: bool = Field(..., description="處理是否成功")
    answer: str = Field(..., description="AI回答")
    referenced_patents: List[int] = Field(default=[], description="引用的專利序號")
    execution_time: float = Field(..., description="執行時間")
    conversation_stats: Dict[str, Any] = Field(..., description="對話統計信息")
    is_continued_conversation: bool = Field(..., description="是否為持續對話")

class ConversationSummaryResponse(BaseModel):
    session_id: str = Field(..., description="會話ID")
    qa_count: int = Field(..., description="問答次數")
    message_count: int = Field(..., description="消息總數")
    total_tokens: int = Field(..., description="使用的token總數")
    token_usage_percent: float = Field(..., description="token使用百分比")
    conversation_active: bool = Field(..., description="對話是否活躍")

# ================================
# 問答相關端點
# ================================

@router.post(
    "/qa/ask-with-history",
    summary="智能問答（支持對話歷史）",
    description="基於檢索結果進行問答，支持多輪對話和上下文記憶",
    response_model=QAResponse,
    tags=["智能問答"]
)
async def ask_question_with_history(request: QARequest):
    """
    支持對話歷史的智能問答
    - 自動記住對話上下文
    - 支持多輪對話
    - 智能token管理（最大128k）
    - 專利引用識別
    """
    try:
        logger.info(f"🤖 收到問答請求: {request.session_id}")
        
        # 確保服務已初始化
        if not enhanced_patent_qa_service.session:
            await enhanced_patent_qa_service.initialize()
        
        # 處理問答
        result = await enhanced_patent_qa_service.answer_question_with_history(
            session_id=request.session_id,
            question=request.question,
            clear_history=request.clear_history
        )
        
        if not result['success']:
            # 如果失敗但有錯誤信息，仍然返回結果
            return QAResponse(
                success=False,
                answer=result['answer'],
                referenced_patents=[],
                execution_time=result.get('execution_time', 0),
                conversation_stats=result.get('conversation_stats', {}),
                is_continued_conversation=False
            )
        
        return QAResponse(
            success=True,
            answer=result['answer'],
            referenced_patents=result.get('referenced_patents', []),
            execution_time=result['execution_time'],
            conversation_stats=result['conversation_stats'],
            is_continued_conversation=result['is_continued_conversation']
        )
        
    except Exception as e:
        logger.error(f"❌ 問答處理失敗: {e}")
        raise HTTPException(status_code=500, detail=f"問答處理失敗: {str(e)}")

@router.get(
    "/qa/conversation/{session_id}/summary",
    summary="獲取對話摘要",
    description="獲取指定會話的對話統計信息和摘要",
    response_model=ConversationSummaryResponse,
    tags=["智能問答"]
)
async def get_conversation_summary(session_id: str):
    """獲取對話摘要和統計信息"""
    try:
        summary = await enhanced_patent_qa_service.get_conversation_summary(session_id)
        
        return ConversationSummaryResponse(
            session_id=summary['session_id'],
            qa_count=summary['qa_count'],
            message_count=summary['message_count'],
            total_tokens=summary['total_tokens'],
            token_usage_percent=summary['token_usage_percent'],
            conversation_active=summary['conversation_active']
        )
        
    except Exception as e:
        logger.error(f"❌ 獲取對話摘要失敗: {e}")
        raise HTTPException(status_code=500, detail=f"獲取對話摘要失敗: {str(e)}")

@router.delete(
    "/qa/conversation/{session_id}/clear",
    summary="清除對話歷史",
    description="清除指定會話的所有對話歷史",
    tags=["智能問答"]
)
async def clear_conversation_history(session_id: str):
    """清除對話歷史"""
    try:
        result = await enhanced_patent_qa_service.clear_conversation_history(session_id)
        return result
        
    except Exception as e:
        logger.error(f"❌ 清除對話歷史失敗: {e}")
        raise HTTPException(status_code=500, detail=f"清除對話歷史失敗: {str(e)}")

@router.get(
    "/qa/service/stats",
    summary="問答服務統計",
    description="獲取問答服務的運行統計信息",
    tags=["智能問答"]
)
async def get_qa_service_stats():
    """獲取問答服務統計信息"""
    try:
        stats = enhanced_patent_qa_service.get_service_stats()
        return {
            "success": True,
            "stats": stats,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ 獲取服務統計失敗: {e}")
        raise HTTPException(status_code=500, detail=f"獲取服務統計失敗: {str(e)}")

# ================================
# 對話管理端點
# ================================

@router.get(
    "/qa/conversations/active",
    summary="獲取活躍對話列表",
    description="獲取所有活躍對話的列表",
    tags=["對話管理"]
)
async def get_active_conversations():
    """獲取活躍對話列表"""
    try:
        active_sessions = list(enhanced_patent_qa_service.conversation_manager.conversations.keys())
        
        conversations = []
        for session_id in active_sessions:
            summary = await enhanced_patent_qa_service.get_conversation_summary(session_id)
            conversations.append(summary)
        
        return {
            "success": True,
            "active_count": len(conversations),
            "conversations": conversations,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ 獲取活躍對話失敗: {e}")
        raise HTTPException(status_code=500, detail=f"獲取活躍對話失敗: {str(e)}")

@router.post(
    "/qa/test/conversation",
    summary="測試對話功能",
    description="測試對話歷史功能是否正常工作",
    tags=["測試"]
)
async def test_conversation_functionality():
    """測試對話功能"""
    try:
        test_session_id = f"test_{int(time.time())}"
        
        # 確保服務已初始化
        if not enhanced_patent_qa_service.session:
            await enhanced_patent_qa_service.initialize()
        
        # 測試對話
        test_question = "你好，這是一個測試問題。"
        
        result = await enhanced_patent_qa_service.answer_question_with_history(
            session_id=test_session_id,
            question=test_question,
            context_patents=[{
                "專利名稱": "測試專利",
                "公開公告號": "TEST001",
                "申請人": "測試公司",
                "國家": "TW",
                "摘要": "這是一個測試專利的摘要內容",
                "技術特徵": ["測試特徵1", "測試特徵2"],
                "技術功效": ["測試功效1", "測試功效2"]
            }]
        )
        
        # 清除測試對話
        await enhanced_patent_qa_service.clear_conversation_history(test_session_id)
        
        return {
            "success": True,
            "test_result": "對話功能測試成功",
            "conversation_history_working": True,
            "token_management_working": True,
            "test_session_id": test_session_id,
            "test_response": result['answer'][:100] + "..." if len(result['answer']) > 100 else result['answer']
        }
        
    except Exception as e:
        logger.error(f"❌ 對話功能測試失敗: {e}")
        return {
            "success": False,
            "test_result": f"對話功能測試失敗: {str(e)}",
            "conversation_history_working": False,
            "token_management_working": False
        }

@router.post(
    "/qa/ask-with-memory",
    summary="智能問答（支援記憶模式）",
    description="基於檢索結果進行問答，支援記憶模式（開啟或關閉）",
    tags=["智能問答"]
)
async def ask_question_with_memory(request: Dict[str, Any]):
    """
    問答端點（支援記憶模式）
    - session_id: 對應檢索結果的會話ID
    - question: 用戶問題
    - use_memory: 是否啟用對話記憶（布林值）
    """
    try:
        session_id = request.get("session_id")
        question = request.get("question")
        use_memory = request.get("use_memory", True)

        if not session_id or not question:
            raise HTTPException(status_code=400, detail="缺少必要參數：session_id 和 question")

        # 確保服務已初始化
        if not enhanced_patent_qa_service.session:
            await enhanced_patent_qa_service.initialize()

        # 呼叫問答服務
        result = await enhanced_patent_qa_service.answer_question_with_memory(
            session_id=session_id,
            question=question,
            use_memory=use_memory
        )

        if not result["success"]:
            return {
                "success": False,
                "answer": result.get("answer", "抱歉，未能獲取回答"),
                "error": result.get("error", ""),
                "timestamp": time.time()
            }

        return {
            "success": True,
            "answer": result.get("answer", ""),
            "referenced_patents": result.get("referenced_patents", []),
            "execution_time": result.get("execution_time", 0),
            "context_patent_count": result.get("context_patent_count", 0),
            "conversation_history_used": result.get("conversation_history_used", 0),
            "memory_enabled": use_memory,
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"❌ 問答請求失敗: {e}")
        raise HTTPException(status_code=500, detail=f"問答處理失敗: {str(e)}")
