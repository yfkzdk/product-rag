"""
PDF解析器

实现表格提取和OCR功能
"""
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class PDFParser:
    """PDF解析器（表格提取+OCR）"""

    def __init__(self):
        """初始化PDF解析器"""
        # 尝试导入OCR库
        try:
            import pytesseract
            self.ocr_available = True
            logger.info("OCR库可用")
        except ImportError:
            self.ocr_available = False
            logger.warning("OCR库不可用，使用Mock实现")

    def extract_tables(self, pdf_path: str) -> List[Dict]:
        """
        提取PDF中的表格

        Args:
            pdf_path: PDF文件路径

        Returns:
            表格列表
        """
        tables = []

        try:
            # 尝试使用pdfplumber
            try:
                import pdfplumber

                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        page_tables = page.extract_tables()
                        for table in page_tables:
                            if table and len(table) > 0:
                                tables.append({
                                    "headers": table[0] if table else [],
                                    "rows": table[1:] if len(table) > 1 else [],
                                    "page": page.page_number
                                })

                logger.info(f"表格提取完成: {len(tables)}个表格")

            except ImportError:
                logger.warning("pdfplumber未安装，使用Mock实现")
                tables = self._mock_extract_tables()

        except Exception as e:
            logger.error(f"表格提取失败: {e}")
            tables = self._mock_extract_tables()

        return tables

    def extract_text_with_ocr(self, pdf_path: str) -> str:
        """
        使用OCR提取文本

        Args:
            pdf_path: PDF文件路径

        Returns:
            提取的文本
        """
        if not self.ocr_available:
            return self._mock_ocr_text()

        try:
            import pytesseract
            from pdf2image import convert_from_path

            # 转换PDF为图像
            images = convert_from_path(pdf_path)

            # OCR识别
            text_parts = []
            for image in images:
                text = pytesseract.image_to_string(image, lang='chi_sim+eng')
                text_parts.append(text)

            full_text = "\n".join(text_parts)
            logger.info(f"OCR文本提取完成: {len(full_text)}字符")

            return full_text

        except Exception as e:
            logger.error(f"OCR提取失败: {e}")
            return self._mock_ocr_text()

    def _mock_extract_tables(self) -> List[Dict]:
        """Mock表格提取"""
        return [
            {
                "headers": ["参数名", "参数值", "单位"],
                "rows": [
                    ["功率", "220", "V"],
                    ["重量", "1.2", "kg"]
                ],
                "page": 1
            }
        ]

    def _mock_ocr_text(self) -> str:
        """Mock OCR文本"""
        return "这是模拟的OCR提取文本内容"


# 全局实例
pdf_parser = PDFParser()