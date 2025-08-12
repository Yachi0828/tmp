from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List
import json

class Settings(BaseSettings):
    #應用基本設定  
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8005, env="PORT")

    #資料庫設定
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///patent_search.db", env="DATABASE_URL")
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    #AI服務設定
    QWEN_API_URL: str = Field(default="http://10.4.16.36:8001", env="QWEN_API_URL")
    QWEN_MODEL: str = Field(default="Qwen2.5-72B-Instruct", env="QWEN_MODEL")

    #Elasticsearch設定
    ELASTICSEARCH_URL: str = Field(default="http://localhost:9200", env="ELASTICSEARCH_URL")
    ELASTICSEARCH_INDEX: str = Field(default="patents", env="ELASTICSEARCH_INDEX")

    #檔案處理設定
    UPLOAD_PATH: str = Field(default="uploads", env="UPLOAD_PATH")
    MAX_FILE_SIZE: int = Field(default=52428800, env="MAX_FILE_SIZE")

    #API安全設定
    SECRET_KEY: str = Field(default="change-this-secret-key-in-production", env="SECRET_KEY")
    JWT_EXPIRE_MINUTES: int = Field(default=1440, env="JWT_EXPIRE_MINUTES")

    #真實API配置（保持向後兼容）
    ENABLE_CPC_CLASSIFICATION: bool = Field(default=False, env="ENABLE_CPC_CLASSIFICATION")
    REQUIRE_API_VALIDATION: bool = Field(default=True, env="REQUIRE_API_VALIDATION")
    ENABLE_DEMO_MODE: bool = Field(default=False, env="ENABLE_DEMO_MODE")
    USE_MOCK_GPSS: bool = Field(default=False, env="USE_MOCK_GPSS")  # 保留舊字段
    USE_REAL_GPSS: bool = Field(default=True, env="USE_REAL_GPSS")   # 新增字段

    #CORS設定
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8080", 
            "http://localhost:8081",
            "http://localhost:5500",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
            "http://127.0.0.1:8081", 
            "http://127.0.0.1:5500",
            "file://",
            "*" 
        ],
        env="CORS_ORIGINS"
    )
    
    #限流設定
    API_RATE_LIMIT: int = Field(default=100, env="API_RATE_LIMIT")

    #日誌設定
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE_PATH: str = Field(default="logs/app.log", env="LOG_FILE_PATH")

    class Config:
        env_file = ".env"
        case_sensitive = True
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        #處理CORS_ORIGINS
        if isinstance(self.CORS_ORIGINS, str):
            try:
                self.CORS_ORIGINS = json.loads(self.CORS_ORIGINS)
            except json.JSONDecodeError:
                self.CORS_ORIGINS = [origin.strip() for origin in self.CORS_ORIGINS.split(',')]

settings = Settings()