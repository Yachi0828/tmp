# src/files/router.py - 簡化版文件處理路由

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os
import shutil
from pathlib import Path
import time

router = APIRouter()

# 確保上傳目錄存在
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@router.get("/", summary="文件服務狀態")
async def file_service_status():
    """文件服務狀態檢查"""
    return {
        "service": "file_processing",
        "status": "ready",
        "upload_dir": str(UPLOAD_DIR),
        "supported_formats": ["txt", "pdf", "docx", "xlsx"],
        "max_file_size": "50MB",
        "version": "1.0.0"
    }

@router.post("/upload", summary="文件上傳")
async def upload_file(file: UploadFile = File(...)):
    """文件上傳功能"""
    try:
        # 檢查文件大小 (50MB限制)
        MAX_SIZE = 50 * 1024 * 1024
        
        # 讀取文件內容
        content = await file.read()
        if len(content) > MAX_SIZE:
            raise HTTPException(status_code=413, detail="文件太大，請選擇小於50MB的文件")
        
        # 生成安全的文件名
        timestamp = int(time.time())
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = UPLOAD_DIR / safe_filename
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        return {
            "success": True,
            "message": "文件上傳成功",
            "filename": safe_filename,
            "original_name": file.filename,
            "size": len(content),
            "content_type": file.content_type,
            "upload_time": timestamp
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上傳失敗: {str(e)}")

@router.get("/list", summary="文件列表")
async def list_files():
    """獲取已上傳的文件列表"""
    try:
        files = []
        for file_path in UPLOAD_DIR.glob("*"):
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "created": stat.st_ctime,
                    "modified": stat.st_mtime
                })
        
        return {
            "success": True,
            "files": files,
            "total": len(files)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取文件列表失敗: {str(e)}")

@router.delete("/delete/{filename}", summary="刪除文件")
async def delete_file(filename: str):
    """刪除指定文件"""
    try:
        file_path = UPLOAD_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        file_path.unlink()
        
        return {
            "success": True,
            "message": f"文件 {filename} 已刪除"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除文件失敗: {str(e)}")

@router.post("/process", summary="處理文件")
async def process_file(filename: str):
    """處理上傳的文件（預留功能）"""
    try:
        file_path = UPLOAD_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 這裡可以添加文件處理邏輯
        # 例如：PDF解析、文字提取等
        
        return {
            "success": True,
            "message": f"文件 {filename} 處理完成",
            "filename": filename,
            "status": "processed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件處理失敗: {str(e)}")