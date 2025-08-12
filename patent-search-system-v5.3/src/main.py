import uvicorn
import logging
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from src.config import settings
from src.patents.router import router as patents_router
from src.services.improved_patent_processing_service import improved_patent_processing_service
from src.exceptions import APIException
from src.services.enhanced_patent_qa_service import enhanced_patent_qa_service

# 新增：導入資料庫相關模組
from src.database import init_db, close_db, DatabaseManager

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, 'INFO'),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(settings.LOG_FILE_PATH, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="智能專利檢索系統 API（純技術特徵版本）",
    description="LLM(Qwen) + GPSS API 整合系統 - 技術特徵生成",
    version="6.0.0",  # 版本升級
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    import time
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.options("/{full_path:path}")
async def options_handler(request: Request, full_path: str):
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )

@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail["error"],
            "message": exc.detail["message"],
            "timestamp": exc.detail["timestamp"]
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "message": str(exc.detail),
            "status_code": exc.status_code
        }
    )

@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception):
    logger.error(f"內部伺服器錯誤: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "內部伺服器錯誤，請稍後再試"
        }
    )

@app.get("/", summary="根路由")
async def root():
    return {
        "message": "智能專利檢索系統 API v6.0.0（純技術特徵版本）",
        "description": "LLM(Qwen) + GPSS API 整合系統 - 技術特徵生成",
        "version": "6.0.0",
        "status": "running",
        "features": [
            "■ 技術描述智能檢索-流程A（含關鍵字確認）",
            "■ 條件查詢檢索-流程B（擴展條件支持）",
            "■ Qwen技術特徵和功效生成",
            "■ Excel批量分析功能",
            "■ Excel報告匯出",
            "■ GPSS API密鑰驗證",
            "🆕 AND/OR關鍵字搜索邏輯",
            "🆕 完全移除分類功能",
            "🆕 專注於技術特徵提取"
        ],
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "patents": "/api/v1/patents/",
            "feedback": "/api/v1/patents/feedback/"
        },
        "services": {
            "qwen_api": settings.QWEN_API_URL,
            "qwen_model": settings.QWEN_MODEL,
            "gpss_api": "Taiwan Patent Database",
            "database": "SQLite with feedback support"
        }
    }

@app.get("/ping")
async def ping():
    return {
        "ping": "pong",
        "service": "intelligent-patent-search-api-tech-features-only",
        "version": "6.0.0",
        "timestamp": "2025-07-03",
        "cors_enabled": True,
        "database_enabled": True,
        "classification_removed": True,
        "focus": "technical_features_and_effects"
    }

@app.get("/health")
async def health_check():
    try:
        health_status = {
            "status": "healthy",
            "version": "6.0.0",
            "timestamp": "2025-07-03",
            "classification_removed": True,
            "configuration": {
                "debug_mode": settings.DEBUG,
                "environment": settings.ENVIRONMENT,
                "qwen_api_url": settings.QWEN_API_URL,
                "qwen_model": settings.QWEN_MODEL,
                "use_real_gpss": settings.USE_REAL_GPSS,
                "require_api_validation": settings.REQUIRE_API_VALIDATION,
                "database_url": settings.DATABASE_URL
            },
            "services": {}
        }
        
        # 檢查專利處理服務
        if not improved_patent_processing_service.initialized:
            try:
                await improved_patent_processing_service.initialize()
                health_status["services"]["patent_processing"] = "ready"
            except Exception as e:
                health_status["services"]["patent_processing"] = f"error: {str(e)}"
                health_status["status"] = "degraded"
        else:
            health_status["services"]["patent_processing"] = "ready"

        # 檢查各個AI服務
        if improved_patent_processing_service.qwen_service:
            health_status["services"]["qwen"] = "connected"
        else:
            health_status["services"]["qwen"] = "unavailable"

        if improved_patent_processing_service.gpss_service:
            health_status["services"]["gpss"] = "available"
        else:
            health_status["services"]["gpss"] = "unavailable"

        # 檢查資料庫狀態
        try:
            # 嘗試獲取反饋統計來測試資料庫連接
            stats = await DatabaseManager.get_feedback_statistics()
            health_status["services"]["database"] = "connected"
            health_status["database_stats"] = stats
        except Exception as e:
            health_status["services"]["database"] = f"error: {str(e)}"
            health_status["status"] = "degraded"

        return health_status

    except Exception as e:
        logger.error(f"健康檢查失敗: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2025-07-03",
            "bert_removed": True
        }

@app.on_event("startup")
async def on_startup():
    try:
        logger.info("🦄 智能專利檢索系統正在啟動（純技術特徵版本）...")
        logger.info(f"⚙ 環境: {settings.ENVIRONMENT}")
        logger.info(f"⚙ 調試模式: {settings.DEBUG}")
        logger.info(f"⚙ CORS設定: {len(settings.CORS_ORIGINS)} 個來源")
        logger.info(f"⚙ 使用真實GPSS API: {settings.USE_REAL_GPSS}")
        logger.info(f"⚙ 需要API驗證: {settings.REQUIRE_API_VALIDATION}")
        logger.info("✅ 分類功能已完全移除，專注於技術特徵提取")
        
        # 創建必要目錄
        Path("logs").mkdir(exist_ok=True)
        Path("uploads").mkdir(exist_ok=True)
        Path("exports").mkdir(exist_ok=True)
        await enhanced_patent_qa_service.initialize()
        logger.info("🧠 增強版問答服務已初始化（支持對話記憶）")
        # 初始化資料庫
        try:
            await init_db()
            logger.info("🗄️ 資料庫初始化完成")
        except Exception as e:
            logger.error(f"🗄️ 資料庫初始化失敗: {e}")
            # 可以選擇繼續運行但功能受限
        
        # 初始化專利處理服務
        try:
            await improved_patent_processing_service.initialize()
            logger.info("🎃 專利處理服務初始化完成（純技術特徵版本）")

            if improved_patent_processing_service.qwen_service:
                logger.info(f"🎃 Qwen API服務已連接: {settings.QWEN_API_URL}")
                logger.info(f"🎃 Qwen模型: {settings.QWEN_MODEL}")
            
            if improved_patent_processing_service.gpss_service:
                logger.info(f"🎃 GPSS API服務已準備")

        except Exception as e:
            logger.error(f"🎭 專利處理服務初始化失敗: {e}")

        logger.info("🎃 智能專利檢索系統啟動完成（純技術特徵版本）！")
        logger.info(" 系統功能:")
        logger.info("   1. 流程A: 技術描述查詢 (AND/OR關鍵字邏輯)")
        logger.info("   2. 流程B: 條件查詢 (擴展條件支持)")
        logger.info("   3. AI: Qwen技術特徵和功效提取")
        logger.info("   4. Excel: 批量分析和匯出功能")
        logger.info("   5. 🆕 完全移除分類功能")
        logger.info("   6. 🆕 專注於技術特徵生成")
        logger.info("   7. 🆕 Excel編碼問題已修復")
        logger.info(f"📖 API文檔: http://localhost:{settings.PORT}/docs")

    except Exception as e:
        logger.error(f"🎭 啟動過程發生嚴重錯誤: {e}")

@app.on_event("shutdown")
async def on_shutdown():
    try:
        logger.info("🎃 智能專利檢索系統正在關閉...")
        
        # 關閉專利處理服務
        await improved_patent_processing_service.close()
        logger.info("🗂 專利處理服務已關閉")
        await enhanced_patent_qa_service.close()
        # 關閉資料庫連接
        try:
            await close_db()
            logger.info("🗄️ 資料庫連接已關閉")
        except Exception as e:
            logger.error(f"關閉資料庫連接失敗: {e}")
        
        logger.info("👋 智能專利檢索系統已安全關閉")
    except Exception as e:
        logger.error(f"關閉過程發生錯誤: {e}")

# 註冊路由
app.include_router(
    patents_router,
    prefix="/api/v1/patents",
    tags=["Patents"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

# 如果files模組存在，則註冊files路由
try:
    from src.files.router import router as files_router
    app.include_router(
        files_router,
        prefix="/api/v1/files",
        tags=["Files"],
        responses={
            404: {"description": "Not found"},
            500: {"description": "Internal server error"}
        }
    )
except ImportError:
    logger.info("Files模組不存在，跳過註冊")

# 靜態文件服務
try:
    static_path = Path("static")
    if static_path.exists():
        app.mount("/static", StaticFiles(directory="static"), name="static")
        logger.info("🎃 靜態文件服務已啟用")
except Exception as e:
    logger.debug(f"靜態文件服務未啟用: {e}")

# 新增：反饋統計端點
@app.get("/api/v1/system/feedback-dashboard")
async def feedback_dashboard():
    """反饋統計儀表板"""
    try:
        feedback_stats = await DatabaseManager.get_feedback_statistics()
        
        return {
            "success": True,
            "dashboard": {
                "title": "用戶反饋統計儀表板",
                "version": "6.0.0",
                "classification_removed": True,
                "statistics": feedback_stats,
                "summary": {
                    "total_sessions": feedback_stats.get("total_feedback", 0),
                    "keyword_quality": f"{feedback_stats.get('keyword_quality', {}).get('average_score', 0) * 100:.1f}%"
                }
            },
            "timestamp": "2025-07-03"
        }
        
    except Exception as e:
        logger.error(f"獲取反饋儀表板失敗: {e}")
        raise HTTPException(status_code=500, detail=f"獲取反饋儀表板失敗: {str(e)}")

# 系統診斷端點
@app.get("/api/v1/system/diagnostics")
async def system_diagnostics():
    """系統診斷工具"""
    try:
        diagnostics = {
            "system_status": "running",
            "version": "6.0.0",
            "timestamp": "2025-07-03",
            "classification_removed": True,
            "configuration": {
                "debug_mode": settings.DEBUG,
                "environment": settings.ENVIRONMENT,
                "qwen_api_url": settings.QWEN_API_URL,
                "qwen_model": settings.QWEN_MODEL,
                "use_mock_gpss": settings.USE_MOCK_GPSS,
                "require_api_validation": settings.REQUIRE_API_VALIDATION,
                "database_url": settings.DATABASE_URL
            },
            "services": {},
            "verified_api_keys": len(improved_patent_processing_service.verified_api_keys),
            "database_stats": {}
        }

        if improved_patent_processing_service.initialized:
            diagnostics["services"]["patent_processing"] = "initialized"

            if improved_patent_processing_service.qwen_service:
                qwen_stats = improved_patent_processing_service.qwen_service.get_service_stats()
                diagnostics["services"]["qwen"] = qwen_stats

            if improved_patent_processing_service.gpss_service:
                gpss_stats = improved_patent_processing_service.gpss_service.get_service_stats()
                diagnostics["services"]["gpss"] = gpss_stats

        else:
            diagnostics["services"]["patent_processing"] = "not_initialized"

        # 獲取資料庫統計
        try:
            db_stats = await DatabaseManager.get_feedback_statistics()
            diagnostics["database_stats"] = db_stats
        except Exception as e:
            diagnostics["database_stats"] = {"error": str(e)}

        return diagnostics

    except Exception as e:
        logger.error(f"系統診斷失敗: {e}")
        raise HTTPException(status_code=500, detail=f"診斷失敗: {str(e)}")

def create_app():
    """創建應用實例"""
    return app

if __name__ == "__main__":
    port = getattr(settings, 'PORT', 8005)  # 保持原端口
    host = getattr(settings, 'HOST', '0.0.0.0')

    logger.info(f"▨ 準備啟動智能專利檢索系統 v6.0.0（純技術特徵版本）")
    logger.info(f"▨ 服務地址: http://{host}:{port}")
    logger.info(f"▨ API文檔: http://{host}:{port}/docs")
    logger.info(f"▨ Debug模式: {settings.DEBUG}")
    logger.info(f"▨ 環境: {settings.ENVIRONMENT}")
    logger.info(f"▨ 新功能: 純技術特徵提取 + Excel編碼修復")
    logger.info(f"▨ 移除: 所有分類功能")

    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else 4,
        log_level="info",
        access_log=True
    )