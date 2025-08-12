# start_server.py - 智能專利檢索系統啟動腳本

import uvicorn
import socket
import psutil
import logging
from pathlib import Path
from src.config import settings

def get_network_info():
    """獲取網路信息"""
    network_info = {
        "local_ip": "127.0.0.1",
        "external_ip": None,
        "all_ips": []
    }
    
    try:
        # 獲取所有網路介面
        for interface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET:  # IPv4
                    ip = addr.address
                    if ip != "127.0.0.1" and not ip.startswith("169.254"):
                        network_info["all_ips"].append({
                            "interface": interface,
                            "ip": ip
                        })
                        if network_info["external_ip"] is None:
                            network_info["external_ip"] = ip
    except Exception as e:
        print(f"⚠️ 獲取網路信息失敗: {e}")
    
    return network_info

def print_connection_info():
    """顯示連接信息"""
    print("\n" + "="*80)
    print("🚀 智能專利檢索系統 - 啟動成功!")
    print("="*80)
    
    network_info = get_network_info()
    
    print(f"📡 伺服器設定:")
    print(f"   主機: {settings.HOST}")
    print(f"   端口: {settings.PORT}")
    print(f"   環境: {settings.ENVIRONMENT}")
    print(f"   調試模式: {settings.DEBUG}")
    
    print(f"\n🌐 API訪問地址:")
    print(f"   本機訪問:")
    print(f"   ├── http://localhost:{settings.PORT}")
    print(f"   └── http://127.0.0.1:{settings.PORT}")
    
    if network_info["external_ip"]:
        print(f"\n   🌍 外部訪問 (其他電腦可用):")
        print(f"   └── http://{network_info['external_ip']}:{settings.PORT}")
    
    if network_info["all_ips"]:
        print(f"\n   📋 所有可用IP地址:")
        for ip_info in network_info["all_ips"]:
            print(f"   ├── {ip_info['interface']}: http://{ip_info['ip']}:{settings.PORT}")
    
    print(f"\n📖 API文檔:")
    if network_info["external_ip"]:
        print(f"   ├── 本機: http://localhost:{settings.PORT}/docs")
        print(f"   └── 外部: http://{network_info['external_ip']}:{settings.PORT}/docs")
    else:
        print(f"   └── http://localhost:{settings.PORT}/docs")
    
    print(f"\n🔧 主要功能端點:")
    base_url = f"http://{network_info['external_ip'] or 'localhost'}:{settings.PORT}"
    print(f"   ├── 健康檢查: {base_url}/health")
    print(f"   ├── 流程A(技術描述): {base_url}/api/v1/patents/search/tech-description")
    print(f"   ├── 流程B(條件查詢): {base_url}/api/v1/patents/search/conditions")
    print(f"   ├── GPSS測試: {base_url}/api/v1/patents/test/gpss")
    print(f"   └── Excel匯出: {base_url}/api/v1/patents/export/excel")
    
    print(f"\n🤖 AI服務設定:")
    print(f"   ├── Qwen API: {settings.QWEN_API_URL}")
    print(f"   ├── Qwen模型: {settings.QWEN_MODEL}")
    print(f"   ├── BERT分類: 20個自訂標籤")
    print(f"   └── GPSS API: 台灣專利資料庫")
    
    print(f"\n🛡️ 防火牆設定提醒:")
    print(f"   如果其他電腦無法訪問，請確保:")
    print(f"   ├── 防火牆開放端口 {settings.PORT}")
    print(f"   ├── 路由器開放端口轉發 (如需要)")
    print(f"   └── 網路安全群組允許訪問 (雲端)")
    
    print("="*80)
    print("🎉 系統就緒，等待API請求...")
    print("="*80 + "\n")

def setup_logging():
    """設置日誌"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(settings.LOG_FILE_PATH, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def check_dependencies():
    """檢查依賴項"""
    print("🔍 檢查系統依賴項...")
    
    try:
        import aiohttp
        import torch
        import transformers
        import pandas
        import openpyxl
        print("✅ 所有主要依賴項已安裝")
    except ImportError as e:
        print(f"❌ 缺少依賴項: {e}")
        print("請運行: pip install -r requirements.txt")
        return False
    
    return True

def create_directories():
    """創建必要目錄"""
    directories = ["logs", "uploads", "exports", "models"]
    for dir_name in directories:
        Path(dir_name).mkdir(exist_ok=True)
    print("✅ 目錄結構已創建")

def main():
    """主函數"""
    print("🚀 啟動智能專利檢索系統...")
    
    # 檢查依賴
    if not check_dependencies():
        return
    
    # 創建目錄
    create_directories()
    
    # 設置日誌
    setup_logging()
    
    # 顯示連接信息
    print_connection_info()
    
    # 啟動伺服器
    try:
        uvicorn.run(
            "src.main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG,
            workers=1 if settings.DEBUG else 4,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n👋 系統已停止")
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")

if __name__ == "__main__":
    main()