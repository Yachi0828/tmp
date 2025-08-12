# src/files/service.py

import pandas as pd
import json
from io import BytesIO
import openpyxl
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class FileExportService:
    async def export_search_results(self, results: List[Dict], format: str, filename: str) -> BytesIO:
        """
        根據 format 生成對應檔案流（Excel/JSON/PDF），並返回 BytesIO 供下載
        支援智能專利檢索系統的專利資料格式
        """
        fmt = format.lower()
        try:
            if fmt == "excel":
                return await self._export_to_excel(results, filename)
            elif fmt == "json":
                return await self._export_to_json(results)
            elif fmt == "pdf":
                return await self._export_to_pdf(results, filename)
            else:
                raise ValueError(f"不支援的匯出格式：{format}")
        except Exception as e:
            logger.error(f"匯出失敗 ({format}): {e}")
            raise

    async def _export_to_excel(self, results: List[Dict], filename: str) -> BytesIO:
        """
        將專利檢索結果轉為 Excel 檔案
        包含主要資料頁面和統計分析頁面
        """
        try:
            # 準備主要資料
            rows = []
            for patent in results:
                row = {
                    "序號": patent.get("sequence_number", ""),
                    "專利名稱": patent.get("patent_title", patent.get("title", "")),
                    "申請人": self._format_list_field(patent.get("applicants", [])),
                    "國家": patent.get("country", ""),
                    "申請號": patent.get("application_number", ""),
                    "公開公告號": patent.get("publication_number", ""),
                    "摘要": self._truncate_text(patent.get("abstract", ""), 500),
                    "專利範圍": self._truncate_text(patent.get("claims", ""), 300),
                    "技術特徵": self._format_list_field(patent.get("technical_features", [])),
                    "技術功效": self._format_list_field(patent.get("technical_effects", [])),
                    "一階分類": patent.get("primary_classification", ""),
                    "二階分類": patent.get("secondary_classification", ""),
                    "三階分類": patent.get("tertiary_classification", ""),
                    "分類置信度": self._format_confidence(patent.get("classification_confidence", 0.0))
                }
                rows.append(row)

            df = pd.DataFrame(rows)
            
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                # 主要資料頁面
                df.to_excel(writer, sheet_name="專利檢索結果", index=False)
                
                # 統計分析頁面
                stats = self._generate_statistics(results)
                if stats:
                    stats_df = pd.DataFrame(stats)
                    stats_df.to_excel(writer, sheet_name="統計分析", index=False)
                
                # 分類統計頁面
                classification_stats = self._generate_classification_stats(results)
                if classification_stats:
                    cls_df = pd.DataFrame(classification_stats)
                    cls_df.to_excel(writer, sheet_name="分類統計", index=False)
                
                # 設定欄位寬度
                self._adjust_excel_columns(writer)

            buffer.seek(0)
            logger.info(f"✅ Excel匯出完成，包含 {len(results)} 筆專利")
            return buffer
            
        except Exception as e:
            logger.error(f"Excel匯出失敗: {e}")
            raise

    async def _export_to_json(self, results: List[Dict]) -> BytesIO:
        """
        將結果轉為 JSON 格式
        """
        try:
            export_data = {
                "export_info": {
                    "format": "json",
                    "total_patents": len(results),
                    "export_timestamp": pd.Timestamp.now().isoformat()
                },
                "patents": results
            }
            
            buffer = BytesIO()
            json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
            buffer.write(json_str.encode("utf-8"))
            buffer.seek(0)
            
            logger.info(f"✅ JSON匯出完成，包含 {len(results)} 筆專利")
            return buffer
            
        except Exception as e:
            logger.error(f"JSON匯出失敗: {e}")
            raise

    async def _export_to_pdf(self, results: List[Dict], filename: str) -> BytesIO:
        """
        將結果以 PDF 報告形式匯出
        包含摘要統計和重點專利清單
        """
        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=50, bottomMargin=50)
            styles = getSampleStyleSheet()
            story = []
            
            # 標題
            title = Paragraph(f"<b>智能專利檢索報告</b>", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 20))
            
            # 摘要統計
            summary_text = f"""
            <b>檢索摘要</b><br/>
            總專利數量：{len(results)}<br/>
            匯出時間：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
            """
            story.append(Paragraph(summary_text, styles['Normal']))
            story.append(Spacer(1, 20))
            
            # 分類統計
            if results:
                classification_summary = self._get_classification_summary(results)
                story.append(Paragraph("<b>分類分佈統計</b>", styles['Heading2']))
                story.append(Paragraph(classification_summary, styles['Normal']))
                story.append(Spacer(1, 20))
            
            # 重點專利清單（取前10筆）
            story.append(Paragraph("<b>重點專利清單</b>", styles['Heading2']))
            
            for i, patent in enumerate(results[:10], 1):
                patent_info = f"""
                <b>{i}. {patent.get('patent_title', '未知標題')}</b><br/>
                申請人：{self._format_list_field(patent.get('applicants', []))}<br/>
                國家：{patent.get('country', '')}<br/>
                申請號：{patent.get('application_number', '')}<br/>
                一階分類：{patent.get('primary_classification', '')}<br/>
                摘要：{self._truncate_text(patent.get('abstract', ''), 200)}<br/>
                """
                story.append(Paragraph(patent_info, styles['Normal']))
                story.append(Spacer(1, 15))
            
            doc.build(story)
            buffer.seek(0)
            
            logger.info(f"✅ PDF匯出完成，包含 {len(results)} 筆專利")
            return buffer
            
        except Exception as e:
            logger.error(f"PDF匯出失敗: {e}")
            raise

    def _generate_statistics(self, results: List[Dict]) -> List[Dict]:
        """
        生成統計分析：申請人、國家、年份分佈等
        """
        try:
            stats = []
            
            # 申請人統計
            applicant_count = {}
            country_count = {}
            classification_count = {}
            
            for patent in results:
                # 申請人統計
                for applicant in patent.get("applicants", []):
                    if isinstance(applicant, str) and applicant.strip():
                        applicant_count[applicant] = applicant_count.get(applicant, 0) + 1
                
                # 國家統計
                country = patent.get("country", "")
                if country:
                    country_count[country] = country_count.get(country, 0) + 1
                
                # 分類統計
                primary_cls = patent.get("primary_classification", "")
                if primary_cls and primary_cls != "Unknown":
                    classification_count[primary_cls] = classification_count.get(primary_cls, 0) + 1
            
            # 前10名申請人
            top_applicants = sorted(applicant_count.items(), key=lambda x: x[1], reverse=True)[:10]
            for applicant, count in top_applicants:
                stats.append({
                    "統計類型": "主要申請人",
                    "項目": applicant,
                    "數量": count,
                    "比例": f"{count/len(results)*100:.1f}%"
                })
            
            # 國家分佈
            top_countries = sorted(country_count.items(), key=lambda x: x[1], reverse=True)[:5]
            for country, count in top_countries:
                stats.append({
                    "統計類型": "國家分佈",
                    "項目": country,
                    "數量": count,
                    "比例": f"{count/len(results)*100:.1f}%"
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"統計生成失敗: {e}")
            return []

    def _generate_classification_stats(self, results: List[Dict]) -> List[Dict]:
        """
        生成分類統計資料
        """
        try:
            classification_stats = []
            
            # 統計各階分類
            primary_count = {}
            secondary_count = {}
            tertiary_count = {}
            
            for patent in results:
                primary = patent.get("primary_classification", "")
                secondary = patent.get("secondary_classification", "")
                tertiary = patent.get("tertiary_classification", "")
                
                if primary and primary != "Unknown":
                    primary_count[primary] = primary_count.get(primary, 0) + 1
                
                if secondary:
                    secondary_count[secondary] = secondary_count.get(secondary, 0) + 1
                
                if tertiary:
                    tertiary_count[tertiary] = tertiary_count.get(tertiary, 0) + 1
            
            # 組裝統計結果
            for classification, count in sorted(primary_count.items(), key=lambda x: x[1], reverse=True):
                classification_stats.append({
                    "分類階層": "一階分類",
                    "分類名稱": classification,
                    "專利數量": count,
                    "佔比": f"{count/len(results)*100:.1f}%"
                })
            
            return classification_stats
            
        except Exception as e:
            logger.error(f"分類統計生成失敗: {e}")
            return []

    def _adjust_excel_columns(self, writer):
        """調整Excel欄位寬度"""
        try:
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                
                # 設定欄位寬度
                column_widths = {
                    'A': 8,   # 序號
                    'B': 30,  # 專利名稱
                    'C': 25,  # 申請人
                    'D': 8,   # 國家
                    'E': 15,  # 申請號
                    'F': 15,  # 公開公告號
                    'G': 50,  # 摘要
                    'H': 40,  # 專利範圍
                    'I': 30,  # 技術特徵
                    'J': 30,  # 技術功效
                    'K': 15,  # 一階分類
                    'L': 15,  # 二階分類
                    'M': 15,  # 三階分類
                    'N': 12   # 分類置信度
                }
                
                for column, width in column_widths.items():
                    worksheet.column_dimensions[column].width = width
                    
        except Exception as e:
            logger.warning(f"調整Excel欄位寬度失敗: {e}")

    def _format_list_field(self, field_list) -> str:
        """格式化清單欄位為字串"""
        if isinstance(field_list, list):
            return "; ".join(str(item) for item in field_list if item)
        elif isinstance(field_list, str):
            return field_list
        else:
            return ""

    def _format_confidence(self, confidence) -> str:
        """格式化置信度"""
        try:
            if isinstance(confidence, (int, float)):
                return f"{confidence:.3f}"
            else:
                return str(confidence)
        except:
            return "0.000"

    def _truncate_text(self, text: str, max_length: int) -> str:
        """截斷文字到指定長度"""
        if not text:
            return ""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."

    def _get_classification_summary(self, results: List[Dict]) -> str:
        """獲取分類摘要文字"""
        try:
            classification_count = {}
            for patent in results:
                primary = patent.get("primary_classification", "Unknown")
                classification_count[primary] = classification_count.get(primary, 0) + 1
            
            # 取前5名
            top_classifications = sorted(classification_count.items(), key=lambda x: x[1], reverse=True)[:5]
            
            summary_parts = []
            for cls, count in top_classifications:
                percentage = count / len(results) * 100
                summary_parts.append(f"{cls}: {count}筆 ({percentage:.1f}%)")
            
            return "<br/>".join(summary_parts)
            
        except Exception as e:
            logger.error(f"分類摘要生成失敗: {e}")
            return "統計資料產生錯誤"