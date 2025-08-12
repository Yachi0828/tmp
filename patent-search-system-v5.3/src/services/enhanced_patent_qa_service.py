# src/services/enhanced_patent_qa_service.py - 支持對話記憶和多重搜尋結果的問答服務

import asyncio
import aiohttp
import logging
import json
import re
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from src.database import DatabaseManager
from src.config import settings

logger = logging.getLogger(__name__)

class ConversationManager:
    """對話管理器 - 處理對話歷史和token控制"""
    
    def __init__(self, max_tokens: int = 128000):
        self.max_tokens = max_tokens
        self.system_prompt_tokens = 500  # 預估系統提示詞token數
        self.context_tokens = 2000       # 預估專利上下文token數  
        self.response_tokens = 1000      # 預留回應token數
        self.safety_margin = 1000        # 安全邊界
        
        # 可用於對話歷史的token數
        self.available_history_tokens = (
            self.max_tokens - 
            self.system_prompt_tokens - 
            self.context_tokens - 
            self.response_tokens - 
            self.safety_margin
        )
    
    def estimate_tokens(self, text: str) -> int:
        """估算文本token數量（簡化方法）"""
        # 中文約1.5個字符=1個token，英文約4個字符=1個token
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_chars = len(text) - chinese_chars
        
        estimated_tokens = (chinese_chars / 1.5) + (english_chars / 4)
        return int(estimated_tokens * 1.2)  # 加20%安全邊界
    
    def trim_conversation_history(self, history: List[Dict]) -> List[Dict]:
        """修剪對話歷史以適應token限制"""
        if not history:
            return []
        
        trimmed_history = []
        current_tokens = 0
        
        # 從最新的對話開始往前添加
        for item in reversed(history):
            question_tokens = self.estimate_tokens(item.get('question', ''))
            answer_tokens = self.estimate_tokens(item.get('answer', ''))
            total_tokens = question_tokens + answer_tokens
            
            if current_tokens + total_tokens <= self.available_history_tokens:
                current_tokens += total_tokens
                trimmed_history.insert(0, item)  # 插入到開頭保持順序
            else:
                break
        
        logger.info(f"對話歷史修剪: 保留 {len(trimmed_history)}/{len(history)} 輪對話，約 {current_tokens} tokens")
        return trimmed_history
    
    def build_messages_with_history(self, 
                                  system_prompt: str,
                                  context: str, 
                                  current_question: str,
                                  history: List[Dict]) -> List[Dict]:
        """構建包含對話歷史的messages"""
        messages = [
            {
                "role": "system",
                "content": system_prompt + f"\n\n專利檢索結果：\n{context}"
            }
        ]
        
        # 添加修剪後的對話歷史
        trimmed_history = self.trim_conversation_history(history)
        
        for item in trimmed_history:
            messages.append({
                "role": "user",
                "content": item['question']
            })
            messages.append({
                "role": "assistant", 
                "content": item['answer']
            })
        
        # 添加當前問題
        messages.append({
            "role": "user",
            "content": current_question
        })
        
        return messages

class EnhancedPatentQAService:
    """增強版專利問答服務 - 支持對話記憶和多重搜尋結果"""
    
    def __init__(self):
        self.qwen_api_url = settings.QWEN_API_URL
        self.qwen_model = settings.QWEN_MODEL
        self.session = None
        self.conversation_manager = ConversationManager(max_tokens=128000)
        
        # 會話對話緩存（內存中）
        self.session_conversations = {}
        
    async def initialize(self):
        """初始化HTTP會話"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=120.0)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logger.info("增強版問答服務已初始化（支持對話記憶和多重搜尋結果）")
    
    async def close(self):
        """關閉HTTP會話"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def answer_question_with_memory(
        self, 
        session_id: str, 
        question: str, 
        context_patents: List[Dict] = None,
        use_memory: bool = True
    ) -> Dict:
        """
        回答問題並支持對話記憶 - 支援多重搜尋結果版本

        Args:
            session_id: 會話ID
            question: 用戶問題
            context_patents: 上下文專利數據
            use_memory: 是否使用對話記憶
        """
        start_time = time.time()

        try:
            logger.info(f"🤖 處理問答請求（記憶模式: {use_memory}）: {session_id}")
            logger.info(f"❓ 問題: {question}")

            # 🆕 檢查可用的搜尋類型
            available_types = await DatabaseManager.get_available_search_types(session_id)

            if not available_types:
                return {
                    'success': True,
                    'answer': self._generate_no_search_results_response(question),
                    'context_info': {
                        'memory_enabled': use_memory,
                        'has_search_cache': False,
                        'search_results_count': 0,
                        'available_search_types': [],
                        'response_type': 'no_search_data_guidance'
                    },
                    'session_id': session_id
                }
        
            # 🆕 智能判斷用戶想詢問哪種搜尋結果
            target_search_type = self._determine_target_search_type(question, available_types)

            # 🆕 獲取對應的搜尋結果
            if target_search_type:
                context_patents = await DatabaseManager.get_cached_search_results_by_type(
                    session_id, target_search_type
                )
            else:
                # 如果無法判斷，獲取所有結果
                context_patents = await DatabaseManager.get_cached_search_results_by_type(session_id)

            if not context_patents:
                return {
                    'success': False,
                    'answer': '抱歉，沒有找到相關的專利數據。請先進行專利檢索。',
                    'error': 'No cached patents found'
                }

            # 獲取對話歷史
            conversation_history = []
            if use_memory:
                # 先從內存緩存獲取
                if session_id in self.session_conversations:
                    conversation_history = self.session_conversations[session_id]
                else:
                    # 從數據庫獲取
                    db_history = await DatabaseManager.get_qa_history(session_id, limit=20)
                    conversation_history = db_history
                    # 緩存到內存
                    self.session_conversations[session_id] = conversation_history

            # 解析問題，確定需要引用的專利
            referenced_patents = self._extract_patent_references(question, context_patents)

            # 🆕 構建多重搜尋上下文
            context = self._build_multi_search_context(
                question, context_patents, referenced_patents, target_search_type
            )

            # 🆕 增強問題，加入搜尋類型信息
            enhanced_question = self._enhance_question_with_search_info(
                question, available_types, target_search_type, len(context_patents)
            )

            # 調用QWEN API（包含對話歷史）
            if not self.session:
                await self.initialize()

            answer = await self._call_qwen_api_with_memory(
                enhanced_question, 
                context, 
                conversation_history if use_memory else []
            )

            # 🆕 在回答後加入搜尋來源說明
            answer_with_source = self._add_source_info_to_answer(
                answer, available_types, target_search_type, len(context_patents)
            )

            execution_time = time.time() - start_time

            # 保存問答歷史到數據庫
            await DatabaseManager.save_qa_history(
                session_id=session_id,
                question=question,
                answer=answer_with_source,
                referenced_patents=referenced_patents,
                execution_time=execution_time
            )

            # 更新內存緩存
            if use_memory:
                if session_id not in self.session_conversations:
                    self.session_conversations[session_id] = []

                self.session_conversations[session_id].append({
                    'question': question,
                    'answer': answer_with_source,
                    'referenced_patents': referenced_patents,
                    'created_at': datetime.now().isoformat()
                })

                # 限制內存緩存大小
                if len(self.session_conversations[session_id]) > 50:
                    self.session_conversations[session_id] = self.session_conversations[session_id][-30:]

            logger.info(f"✅ 問答完成（使用記憶: {use_memory}），耗時: {execution_time:.2f}秒")

            return {
                'success': True,
                'answer': answer_with_source,
                'referenced_patents': referenced_patents,
                'execution_time': execution_time,
                'context_patent_count': len(context_patents),
                'conversation_history_used': len(conversation_history) if use_memory else 0,
                'memory_enabled': use_memory,
                # 🆕 新增多重搜尋相關信息
                'context_info': {
                    'available_search_types': available_types,
                    'target_search_type': target_search_type,
                    'search_results_count': len(context_patents),
                    'response_type': 'normal'
                }
            }

        except Exception as e:
            logger.error(f"❌ 問答處理失敗: {e}")
            return {
                'success': False,
                'answer': f'抱歉，處理您的問題時發生錯誤: {str(e)}',
                'error': str(e)
            }

    async def _call_qwen_api_with_memory(
        self, 
        question: str, 
        context: str,
        conversation_history: List[Dict]
    ) -> str:
        """調用QWEN API並包含對話歷史"""
        try:
            # 構建系統提示詞
            system_prompt = """你是一個專業的專利檢索助手。你能夠記住我們之前的對話內容，並基於檢索結果和對話歷史來回答問題。

回答要求：
1. 用繁體中文回答
2. 基於提供的專利檢索結果回答問題
3. 如果用戶問到特定專利（如"第3筆專利"），請根據序號找到對應的專利資料
4. 如果涉及翻譯，請提供準確的中英文對照
5. 如果是技術分析，請聚焦於技術特徵和功效
6. 記住我們之前討論的內容，可以參考前面的對話
7. 回答要簡潔明確，避免冗長
8. 如果用戶問題超出檢索結果範圍，請說明無法回答的原因"""

            # 使用對話管理器構建包含歷史的messages
            messages = self.conversation_manager.build_messages_with_history(
                system_prompt=system_prompt,
                context=context,
                current_question=question,
                history=conversation_history
            )
            
            # 估算總token數用於日誌
            total_estimated_tokens = sum(
                self.conversation_manager.estimate_tokens(str(msg)) 
                for msg in messages
            )
            logger.info(f"📊 預估總token數: {total_estimated_tokens}/128000")
            
            payload = {
                "model": self.qwen_model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 1500,  # 增加最大回應長度
                "stream": False
            }
            
            async with self.session.post(
                f"{self.qwen_api_url}/v1/chat/completions",
                json=payload,
                headers={'Content-Type': 'application/json'}
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    if 'choices' in data and len(data['choices']) > 0:
                        answer = data['choices'][0]['message']['content']
                        
                        # 記錄實際使用的token數
                        usage = data.get('usage', {})
                        actual_tokens = usage.get('total_tokens', 0)
                        logger.info(f"📊 實際使用token數: {actual_tokens}")
                        
                        return answer
                    else:
                        return "抱歉，AI回應格式異常，請稍後再試。"
                else:
                    error_text = await response.text()
                    logger.error(f"QWEN API錯誤: {response.status} - {error_text}")
                    return "抱歉，AI服務暫時不可用，請稍後再試。"
                    
        except Exception as e:
            logger.error(f"調用QWEN API失敗: {e}")
            return "抱歉，處理您的問題時發生錯誤，請稍後再試。"
    
    def _extract_patent_references(self, question: str, patents: List[Dict]) -> List[int]:
        """從問題中提取專利引用"""
        referenced_patents = []
        
        # 使用正則表達式匹配專利序號
        patterns = [
            r'第\s*(\d+)\s*筆',
            r'第\s*(\d+)\s*個',
            r'序號\s*(\d+)',
            r'專利\s*(\d+)',
            r'(\d+)\s*號專利',
            r'編號\s*(\d+)',
            r'前\s*(\d+)\s*筆',  # 新增：前N筆
            r'最後\s*(\d+)\s*筆', # 新增：最後N筆
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, question)
            for match in matches:
                try:
                    patent_num = int(match)
                    if 1 <= patent_num <= len(patents):
                        referenced_patents.append(patent_num)
                except ValueError:
                    continue
        
        # 特殊處理：如果問到"這些專利"、"所有專利"等
        if any(keyword in question for keyword in ['這些專利', '所有專利', '全部專利', '每筆專利']):
            referenced_patents = list(range(1, min(len(patents) + 1, 11)))  # 最多前10筆
        
        # 去重並排序
        referenced_patents = sorted(list(set(referenced_patents)))
        
        logger.info(f"🔍 識別到引用專利: {referenced_patents}")
        return referenced_patents
    
    def _format_patent_for_context(self, patent: Dict, sequence: int) -> str:
        """格式化單個專利用於上下文"""
        formatted = f"\n專利 {sequence}：\n"
        formatted += f"- 名稱：{patent.get('專利名稱', 'N/A')}\n"
        formatted += f"- 公開公告號：{patent.get('公開公告號', 'N/A')}\n"
        formatted += f"- 申請人：{patent.get('申請人', 'N/A')}\n"
        formatted += f"- 國家：{patent.get('國家', 'N/A')}\n"
        
        # 截取摘要
        abstract = patent.get('摘要', '')
        if abstract and abstract != 'N/A':
            abstract_short = abstract[:800] + "..." if len(abstract) > 800 else abstract
            formatted += f"- 摘要：{abstract_short}\n"
        
        # 技術特徵
        features = patent.get('技術特徵', [])
        if features:
            formatted += f"- 技術特徵：{'; '.join(features[:5])}\n"
        
        # 技術功效
        effects = patent.get('技術功效', [])
        if effects:
            formatted += f"- 技術功效：{'; '.join(effects[:5])}\n"
        
        return formatted
    
    def _format_patent_brief(self, patent: Dict, sequence: int) -> str:
        """格式化專利簡要信息"""
        title = patent.get('專利名稱', 'N/A')
        number = patent.get('公開公告號', 'N/A')
        return f"{sequence}. {title} ({number})\n"
    
    async def get_conversation_summary(self, session_id: str) -> Dict:
        """獲取對話摘要"""
        try:
            history = await DatabaseManager.get_qa_history(session_id, limit=50)
            
            if not history:
                return {
                    'success': True,
                    'summary': '尚無對話記錄',
                    'total_questions': 0
                }
            
            summary = {
                'success': True,
                'total_questions': len(history),
                'first_question_time': history[0]['created_at'] if history else None,
                'last_question_time': history[-1]['created_at'] if history else None,
                'common_topics': self._extract_common_topics(history),
                'recent_questions': [item['question'] for item in history[-5:]]
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"獲取對話摘要失敗: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_common_topics(self, history: List[Dict]) -> List[str]:
        """提取常見話題"""
        topics = []
        
        # 簡單的關鍵詞統計
        keyword_counts = {}
        for item in history:
            question = item['question'].lower()
            
            # 技術相關關鍵詞
            tech_keywords = ['技術', '特徵', '功效', '專利', '申請人', '翻譯', '比較', '分析']
            for keyword in tech_keywords:
                if keyword in question:
                    keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        # 返回出現次數最多的前3個話題
        sorted_topics = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        topics = [topic for topic, count in sorted_topics[:3] if count > 1]
        
        return topics
    
    async def clear_conversation_memory(self, session_id: str) -> bool:
        """清除對話記憶"""
        try:
            # 清除內存緩存
            if session_id in self.session_conversations:
                del self.session_conversations[session_id]
            
            logger.info(f"已清除會話 {session_id} 的對話記憶")
            return True
            
        except Exception as e:
            logger.error(f"清除對話記憶失敗: {e}")
            return False

    # 🆕 =============== 多重搜尋結果支援方法 ===============

    def _determine_target_search_type(self, question: str, available_types: List[str]) -> str:
        """智能判斷用戶想詢問哪種搜尋結果"""
        question_lower = question.lower()

        # 明確指定的關鍵字
        if any(keyword in question for keyword in ['條件查詢', '條件搜尋', '條件檢索']):
            if 'condition_search' in available_types:
                return 'condition_search'

        if any(keyword in question for keyword in ['技術描述', '技術查詢', '描述查詢']):
            if 'tech_description_search' in available_types:
                return 'tech_description_search'

        if any(keyword in question for keyword in ['excel分析', 'excel檔案', '批量分析']):
            if 'excel_analysis' in available_types:
                return 'excel_analysis'

        # 如果沒有明確指定，返回最新的搜尋類型
        search_type_priority = ['tech_description_search', 'condition_search', 'excel_analysis']
        for search_type in search_type_priority:
            if search_type in available_types:
                return search_type

        return None

    def _get_search_type_display_name(self, search_type: str) -> str:
        """獲取搜尋類型的顯示名稱"""
        type_names = {
            'tech_description_search': '技術描述查詢',
            'condition_search': '條件查詢',
            'excel_analysis': 'Excel分析'
        }
        return type_names.get(search_type, search_type)

    def _generate_no_search_results_response(self, question: str) -> str:
        """生成沒有搜尋結果時的友善回應"""
        if '翻譯' in question:
            return """很抱歉，我目前沒有找到任何專利資料可以翻譯。

請您先：
1. 🔍 使用「技術描述查詢」功能輸入技術描述，讓我搜尋相關專利
2. 📋 或使用「條件查詢」功能設定搜尋條件
3. 📊 或上傳Excel檔案進行批量分析

完成搜尋後，我就能幫您翻譯和分析專利內容了！有什麼其他問題我可以協助您嗎？"""

        elif '專利' in question:
            return """您好！我注意到您詢問專利相關內容，但目前系統中還沒有專利搜尋結果。

建議您可以：
• 🎯 **技術描述查詢**：描述您要找的技術，我會生成關鍵字並搜尋
• 🔍 **條件查詢**：設定申請人、專利號、時間範圍等條件搜尋  
• 📈 **Excel分析**：上傳專利清單進行批量分析

搜尋完成後，我就能回答關於專利內容、技術特徵、申請人等各種問題！"""

        else:
            return """您好！我是專利檢索系統的AI助手。

我可以幫您：
• 分析專利技術特徵和功效
• 翻譯專利內容
• 回答專利相關問題
• 協助搜尋策略建議

請先執行專利搜尋，然後我就能根據搜尋結果為您提供詳細分析！"""

    def _enhance_question_with_search_info(
        self, 
        question: str, 
        available_types: List[str], 
        target_search_type: str,
        results_count: int
    ) -> str:
        """增強問題，加入搜尋上下文信息"""

        type_info = []
        for search_type in available_types:
            type_name = self._get_search_type_display_name(search_type)
            type_info.append(type_name)

        enhanced = f"""
用戶問題：{question}

背景信息：
- 可用的搜尋結果類型：{', '.join(type_info)}
- 主要分析對象：{self._get_search_type_display_name(target_search_type) if target_search_type else '所有結果'}
- 專利總數：{results_count}筆

請根據上述搜尋結果回答用戶的問題。如果涉及特定筆數（如"第一筆"、"第二筆"），請確保按照正確的序號對應。
"""

        return enhanced

    def _add_source_info_to_answer(
        self, 
        answer: str, 
        available_types: List[str], 
        target_search_type: str,
        results_count: int
    ) -> str:
        """在回答後加入來源信息"""

        if not available_types:
            return answer

        source_info = "\n\n" + "\n"
        source_info += "**搜尋結果來源信息**\n"
    
        for search_type in available_types:
            type_name = self._get_search_type_display_name(search_type)
            if search_type == target_search_type:
                source_info += f"**{type_name}**（本次回答基於此結果）\n"
            else:
                source_info += f"{type_name}（可詢問相關問題）\n"

        source_info += f"\n您可以詢問：「{self._get_search_type_display_name(target_search_type) if target_search_type else '其他搜尋結果'}的第X筆專利」來獲得更精確的資訊。"

        return answer + source_info

    def _build_multi_search_context(
        self, 
        question: str, 
        patents: List[Dict], 
        referenced_patents: List[int], 
        target_search_type: str = None
    ) -> str:
        """構建多重搜尋結果的問答上下文"""
        context_parts = []
        
        # 檢查是否有搜尋類型標記
        results_by_type = {}
        for patent in patents:
            search_type = patent.get('_search_type', 'unknown')
            if search_type not in results_by_type:
                results_by_type[search_type] = []
            results_by_type[search_type].append(patent)
        
        # 如果只有一種搜尋類型，使用原有邏輯
        if len(results_by_type) == 1:
            context_parts.append(f"以下是檢索到的 {len(patents)} 筆專利資料：\n")
            
            # 如果有特定引用，只包含引用的專利
            if referenced_patents:
                context_parts.append("特別關注以下專利：\n")
                for patent_num in referenced_patents:
                    if 1 <= patent_num <= len(patents):
                        patent = patents[patent_num - 1]
                        context_parts.append(self._format_patent_for_context(patent, patent_num))
            else:
                # 如果沒有特定引用，提供所有專利的簡要信息
                context_parts.append("所有專利簡要信息：\n")
                for i, patent in enumerate(patents[:15]):
                    context_parts.append(self._format_patent_brief(patent, i + 1))
                
                if len(patents) > 15:
                    context_parts.append(f"\n...（還有 {len(patents) - 15} 筆專利）")
        
        else:
            # 多種搜尋類型，按類型分組顯示
            context_parts.append(f"以下是來自不同搜尋的專利資料（共 {len(patents)} 筆）：\n")
            
            for search_type, type_patents in results_by_type.items():
                if target_search_type and search_type != target_search_type:
                    continue  # 如果指定了搜尋類型，只處理該類型
                
                type_name = self._get_search_type_display_name(search_type)
                context_parts.append(f"\n=== {type_name}結果 ({len(type_patents)}筆) ===")
                
                # 重新計算這個類型中的序號
                for i, patent in enumerate(type_patents[:10]):  # 每種類型最多顯示10筆
                    global_index = patents.index(patent) + 1  # 在總列表中的位置
                    
                    if referenced_patents and global_index in referenced_patents:
                        context_parts.append(self._format_patent_for_context(patent, global_index))
                    else:
                        context_parts.append(self._format_patent_brief(patent, global_index))
        
        return '\n'.join(context_parts)

# 全局增強版問答服務實例
enhanced_patent_qa_service = EnhancedPatentQAService()