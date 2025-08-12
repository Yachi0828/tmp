# src/exceptions.py - 異常處理模塊

from fastapi import HTTPException
from datetime import datetime
from typing import Dict, Any, Optional

class APIException(HTTPException):
    """自定義API異常類"""
    
    def __init__(
        self, 
        status_code: int, 
        error_code: str = "API_ERROR",
        message: str = "API請求發生錯誤",
        details: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        
        detail = {
            "error": error_code,
            "message": message,
            "details": self.details,
            "timestamp": datetime.now().isoformat()
        }
        
        super().__init__(status_code=status_code, detail=detail)

class PatentSearchException(APIException):
    """專利檢索相關異常"""
    
    def __init__(self, message: str = "專利檢索失敗", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=400,
            error_code="PATENT_SEARCH_ERROR",
            message=message,
            details=details
        )

class APIValidationException(APIException):
    """API驗證異常"""
    
    def __init__(self, message: str = "API驗證失敗", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=401,
            error_code="API_VALIDATION_ERROR",
            message=message,
            details=details
        )

class ServiceUnavailableException(APIException):
    """服務不可用異常"""
    
    def __init__(self, service_name: str, message: str = None):
        message = message or f"{service_name}服務暫時不可用"
        super().__init__(
            status_code=503,
            error_code="SERVICE_UNAVAILABLE",
            message=message,
            details={"service": service_name}
        )

class FileProcessingException(APIException):
    """文件處理異常"""
    
    def __init__(self, message: str = "文件處理失敗", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=400,
            error_code="FILE_PROCESSING_ERROR",
            message=message,
            details=details
        )

class ConfigurationException(APIException):
    """配置異常"""
    
    def __init__(self, message: str = "系統配置錯誤", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=500,
            error_code="CONFIGURATION_ERROR",
            message=message,
            details=details
        )