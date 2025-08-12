# src/external_apis/gpss_client.py

import asyncio
import aiohttp
import logging
from typing import List, Dict, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class GPSSAPIClient(ABC):
    """GPSS API客戶端抽象基類"""
    
    @abstractmethod
    async def initialize(self):
        """初始化客戶端"""
        pass
    
    @abstractmethod
    async def close(self):
        """關閉客戶端"""
        pass
    
    @abstractmethod
    async def search_patents(self, **kwargs) -> List[Dict]:
        """搜尋專利"""
        pass

class RealGPSSClient(GPSSAPIClient):
    """真實的GPSS API客戶端"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = None
        from src.ai_services.gpss_service import GPSSAPIService
        self.gpss_service = GPSSAPIService()
    
    async def initialize(self):
        """初始化HTTP會話"""
        await self.gpss_service.initialize()
        logger.info("真實GPSS客戶端初始化完成")
    
    async def close(self):
        """關閉HTTP會話"""
        await self.gpss_service.close()
    
    async def search_patents(
        self, 
        keywords: Optional[List[str]] = None,
        databases: Optional[List[str]] = None,
        patent_types: Optional[List[str]] = None,
        max_results: int = 50,
        **kwargs
    ) -> List[Dict]:
        """使用真實GPSS API搜尋專利"""
        try:
            # 組裝搜尋參數
            search_params = {
                'expQty': str(max_results),
                'expFmt': 'json'
            }
            
            if databases:
                search_params['patDB'] = ','.join(databases)
            
            if patent_types:
                search_params['patTY'] = ','.join(patent_types)
            
            # 合併額外參數
            search_params.update(kwargs)
            
            # 調用GPSS API
            result = await self.gpss_service.search_patents_raw( 
                user_code=self.api_key,
                keywords=keywords,
                search_params=search_params
            )
            
            # 解析結果
            return self._parse_gpss_result(result)
            
        except Exception as e:
            logger.error(f"真實GPSS搜尋失敗: {e}")
            return []
    
    def _parse_gpss_result(self, gpss_result: Dict) -> List[Dict]:
        """解析GPSS API結果"""
        try:
            if 'gpss-API' not in gpss_result:
                return []
            
            # 根據實際GPSS API回應格式解析
            # 這裡需要根據實際API回應調整
            api_data = gpss_result['gpss-API']
            
            if 'patents' in api_data:
                return api_data['patents']
            elif 'results' in api_data:
                return api_data['results']
            else:
                return []
                
        except Exception as e:
            logger.error(f"解析GPSS結果失敗: {e}")
            return []

class MockGPSSClient(GPSSAPIClient):
    """模擬的GPSS API客戶端（用於測試和開發）"""
    
    def __init__(self, api_key: str = "mock"):
        self.api_key = api_key
        self.mock_patents = self._generate_mock_patents()
    
    async def initialize(self):
        """初始化模擬客戶端"""
        logger.info("模擬GPSS客戶端初始化完成")
    
    async def close(self):
        """關閉模擬客戶端"""
        pass
    
    async def search_patents(
        self, 
        keywords: Optional[List[str]] = None,
        databases: Optional[List[str]] = None,
        patent_types: Optional[List[str]] = None,
        max_results: int = 50,
        **kwargs
    ) -> List[Dict]:
        """模擬專利搜尋"""
        try:
            # 模擬搜尋延遲
            await asyncio.sleep(0.2)
            
            # 根據關鍵字過濾模擬專利
            filtered_patents = []
            
            if keywords:
                logger.info(f"🔍 模擬搜尋關鍵字: {keywords}")
                
                # 更智能的關鍵字匹配
                for patent in self.mock_patents:
                    title = patent.get('title', '').lower()
                    abstract = patent.get('abstract', '').lower()
                    content = f"{title} {abstract}"
                    
                    # 檢查關鍵字匹配
                    match_score = 0
                    for keyword in keywords:
                        keyword_lower = keyword.lower()
                        
                        # 直接匹配
                        if keyword_lower in content:
                            match_score += 2
                        
                        # 相關詞匹配
                        related_matches = {
                            '半導體': ['semiconductor', 'chip', 'wafer', '晶圓'],
                            'semiconductor': ['半導體', '晶圓', 'chip', 'wafer'],
                            '測試': ['test', 'testing', 'measurement', '檢測'],
                            'test': ['測試', '檢測', 'testing', 'measurement'],
                            '自動': ['automatic', 'automation', 'automated'],
                            'automatic': ['自動', 'automation', '自動化'],
                            '系統': ['system', 'equipment', 'apparatus'],
                            'system': ['系統', '設備', 'equipment'],
                            '控制': ['control', 'controller', 'management'],
                            'control': ['控制', '管理', 'controller'],
                            '檢測': ['detection', 'inspection', 'analysis'],
                            'detection': ['檢測', '檢查', 'inspection'],
                            '機械': ['mechanical', 'robot', 'robotic'],
                            'mechanical': ['機械', '機器人', 'robot']
                        }
                        
                        if keyword_lower in related_matches:
                            for related_word in related_matches[keyword_lower]:
                                if related_word in content:
                                    match_score += 1
                                    break
                    
                    # 如果有匹配，加入結果
                    if match_score > 0:
                        patent_copy = patent.copy()
                        patent_copy['match_score'] = match_score
                        filtered_patents.append(patent_copy)
                
                # 按匹配分數排序
                filtered_patents.sort(key=lambda x: x.get('match_score', 0), reverse=True)
                
            else:
                # 如果沒有關鍵字，返回所有專利
                filtered_patents = self.mock_patents.copy()
            
            # 限制結果數量
            result = filtered_patents[:max_results]
            
            logger.info(f"✅ 模擬GPSS搜尋完成，關鍵字: {keywords}, 結果: {len(result)} 筆")
            return result
            
        except Exception as e:
            logger.error(f"❌ 模擬GPSS搜尋失敗: {e}")
            return []
    
    def _generate_mock_patents(self) -> List[Dict]:
        """生成模擬專利資料"""
        return [
            {
                "id": "TW202436881A",
                "title": "用來校正被測器件介面的系統及方法",
                "abstract": "本發明揭示一種用來校準被測器件介面的系統，包含測試頭端、DUT單元及計算單元，透過信號產生器與測量單元實現高精度校準，可有效提升測試精確度並降低測試時間。該系統具備自動化校準功能，能適應不同類型的被測器件，並提供即時校準結果反饋。",
                "claims": "1. 一種用來校正被測器件介面的系統，其特徵在於包含：測試頭端，用於與被測器件電性連接；DUT單元，包含多個測試通道；計算單元，用於控制校準程序；信號產生器，產生測試信號；測量單元，量測回傳信號；其中該計算單元根據測量結果進行校準補償。",
                "applicants": ["愛德萬測試股份有限公司"],
                "inventors": ["張偉明", "李雅婷"],
                "application_number": "TW113115234",
                "publication_number": "TW202436881A",
                "country": "TW",
                "application_date": "20240515",
                "publication_date": "20240901",
                "ipc_classes": ["G01R1/20", "G01R31/28"]
            },
            {
                "id": "TW202436046A",
                "title": "測試系統以及機械手臂裝置",
                "abstract": "一種測試系統及機械手臂裝置，包括取像單元、處理單元、端效器模組和通訊模組，用於自動化測試流程管理與控制，具備高精度定位和多軸協調控制能力。該系統能自動識別待測物件，執行精確的抓取和定位操作。",
                "claims": "1. 一種測試系統，其特徵在於包含：機械手臂裝置，具有多個關節；取像單元，用於識別待測物件；處理單元，控制機械手臂動作；端效器模組，用於抓取物件；通訊模組，與外部系統通訊；其中該處理單元根據取像結果控制機械手臂執行測試程序。",
                "applicants": ["愛德萬測試股份有限公司"],
                "inventors": ["王建華", "趙美玲", "李志強"],
                "application_number": "TW113114987",
                "publication_number": "TW202436046A",
                "country": "TW",
                "application_date": "20240420",
                "publication_date": "20240815",
                "ipc_classes": ["B25J9/18", "G01R31/26"]
            },
            {
                "id": "US20240123456A1",
                "title": "Automated Semiconductor Testing System with AI-Enhanced Analysis",
                "abstract": "An automated testing system for semiconductor devices comprising a test head, device under test interface, and control unit with artificial intelligence capabilities. The system performs comprehensive electrical testing, thermal analysis, and failure mode detection with enhanced accuracy and reduced test time.",
                "claims": "1. An automated testing system comprising: a test head configured to interface with semiconductor devices; an AI-enhanced control unit for test sequence optimization; multiple test channels for parallel testing; thermal monitoring subsystem; data analysis engine with machine learning algorithms; wherein the system automatically adapts test parameters based on device characteristics.",
                "applicants": ["Intel Corporation"],
                "inventors": ["John Smith", "Sarah Johnson"],
                "application_number": "US17/123456",
                "publication_number": "US20240123456A1",
                "country": "US",
                "application_date": "20240210",
                "publication_date": "20240720",
                "ipc_classes": ["G01R31/28", "H01L21/66"]
            },
            {
                "id": "JP2024567890A",
                "title": "高精度半導体検査装置および検査方法",
                "abstract": "高精度な半導体検査を実現する検査装置および検査方法に関し、プローブカード、測定ユニット、制御部を含む。AI技術を活用した不良解析機能により、検査効率と精度の向上を図る。多様な半導体デバイスに対応可能な柔軟な検査システムを提供する。",
                "claims": "1. 半導体検査装置であって：被検査デバイスと接続するプローブカード；電気的特性を測定する測定ユニット；検査シーケンスを制御する制御部；AI解析モジュール；を備え、前記制御部は測定結果に基づいて検査パラメータを自動調整することを特徴とする半導体検査装置。",
                "applicants": ["株式会社アドバンテスト"],
                "inventors": ["田中太郎", "佐藤花子"],
                "application_number": "JP2024-567890",
                "publication_number": "JP2024567890A",
                "country": "JP",
                "application_date": "20240315",
                "publication_date": "20240925",
                "ipc_classes": ["G01R31/28", "G01R1/073"]
            },
            {
                "id": "EP2024789123A1",
                "title": "Smart Test Handler with Adaptive Control System",
                "abstract": "A smart test handler system incorporating adaptive control algorithms for semiconductor device handling and testing. The system features real-time optimization capabilities, predictive maintenance functions, and enhanced throughput management. Machine learning algorithms enable continuous improvement of handling precision and test efficiency.",
                "claims": "1. A test handler system comprising: a device handling mechanism with multi-axis control; adaptive control algorithms for optimizing handling sequences; sensor arrays for monitoring device positioning; machine learning module for performance optimization; communication interface for integration with test equipment; wherein the system continuously adapts handling parameters based on operational feedback.",
                "applicants": ["ASML Netherlands B.V."],
                "inventors": ["Hans Mueller", "Maria Garcia"],
                "application_number": "EP24789123",
                "publication_number": "EP2024789123A1",
                "country": "EP",
                "application_date": "20240125",
                "publication_date": "20240805",
                "ipc_classes": ["H01L21/67", "G01R31/28"]
            }
        ]

def create_gpss_client(use_mock: bool = True, api_key: str = "") -> GPSSAPIClient:
    """
    工廠方法：創建GPSS客戶端
    
    Args:
        use_mock: 是否使用模擬客戶端
        api_key: GPSS API密鑰
        
    Returns:
        GPSSAPIClient實例
    """
    if use_mock:
        return MockGPSSClient(api_key)
    else:
        if not api_key:
            raise ValueError("真實GPSS客戶端需要提供API密鑰")
        return RealGPSSClient(api_key)