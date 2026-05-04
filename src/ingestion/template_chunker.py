"""
模板化Chunking优化

基于RAGFlow的表格智能分块
"""
from typing import List, Dict, Optional
import re
import logging

logger = logging.getLogger(__name__)


class TemplateChunker:
    """模板化分块器"""

    CHUNK_TEMPLATES = {
        "spec_table": {
            "pattern": r"参数\s*[:：]\s*(.+)",
            "fields": ["参数名", "参数值", "单位"],
            "chunk_format": "{参数名}: {参数值} {单位}",
            "description": "规格参数表"
        },
        "fault_table": {
            "pattern": r"故障代码\s*[:：]\s*(.+)",
            "fields": ["故障代码", "症状", "原因", "解决方案"],
            "chunk_format": "故障{故障代码}: {症状}，原因: {原因}，解决: {解决方案}",
            "description": "故障诊断表"
        },
        "compatibility_matrix": {
            "pattern": r"兼容性\s*[:：]\s*(.+)",
            "fields": ["产品A", "产品B", "兼容类型"],
            "chunk_format": "{产品A}与{产品B}兼容性: {兼容类型}",
            "description": "兼容性矩阵"
        },
        "version_table": {
            "pattern": r"版本\s*[:：]\s*(.+)",
            "fields": ["版本号", "发布日期", "更新内容"],
            "chunk_format": "版本{版本号} ({发布日期}): {更新内容}",
            "description": "版本历史表"
        }
    }

    def __init__(self):
        """初始化模板分块器"""
        logger.info(f"TemplateChunker initialized with {len(self.CHUNK_TEMPLATES)} templates")

    def detect_table_type(self, table_data: Dict) -> str:
        """
        检测表格类型

        Args:
            table_data: 表格数据

        Returns:
            表格类型
        """
        headers = table_data.get("headers", [])

        # 检查表头匹配
        for table_type, template in self.CHUNK_TEMPLATES.items():
            expected_fields = template["fields"]

            # 计算字段匹配度
            match_count = 0
            for expected_field in expected_fields:
                for header in headers:
                    if expected_field in header or header in expected_field:
                        match_count += 1
                        break

            # 如果匹配度超过50%，认为是该类型
            if match_count >= len(expected_fields) * 0.5:
                logger.info(f"Detected table type: {table_type} (match={match_count}/{len(expected_fields)})")
                return table_type

        # 默认类型
        return "spec_table"

    def chunk_table(self, table_data: Dict, table_type: Optional[str] = None) -> List[str]:
        """
        按模板分块表格

        Args:
            table_data: 表格数据
            table_type: 表格类型（可选，自动检测）

        Returns:
            分块列表
        """
        # 自动检测表格类型
        if table_type is None:
            table_type = self.detect_table_type(table_data)

        template = self.CHUNK_TEMPLATES.get(table_type, self.CHUNK_TEMPLATES["spec_table"])
        chunks = []

        rows = table_data.get("rows", [])
        for row in rows:
            # 字段映射
            field_values = {}
            for i, field in enumerate(template["fields"]):
                if i < len(row):
                    field_values[field] = str(row[i]).strip()
                else:
                    field_values[field] = ""

            # 格式化chunk
            try:
                chunk = template["chunk_format"].format(**field_values)
                chunks.append(chunk)
            except KeyError as e:
                logger.warning(f"Failed to format chunk: missing field {e}")
                # 降级：直接拼接
                chunk = " | ".join([str(cell) for cell in row])
                chunks.append(chunk)

        logger.info(f"Chunked table: type={table_type}, rows={len(rows)}, chunks={len(chunks)}")
        return chunks

    def chunk_text_with_structure(self, text: str, structure_type: str) -> List[str]:
        """
        按结构分块文本

        Args:
            text: 文本内容
            structure_type: 结构类型

        Returns:
            分块列表
        """
        chunks = []

        if structure_type == "spec_table":
            # 提取参数行
            pattern = r"([^\s:：]+)\s*[:：]\s*([^\s:：]+)\s*([^\s:：]*)?"
            matches = re.findall(pattern, text)

            for match in matches:
                param_name, param_value, unit = match
                chunk = f"{param_name}: {param_value} {unit}".strip()
                chunks.append(chunk)

        elif structure_type == "fault_table":
            # 提取故障信息
            pattern = r"故障代码\s*[:：]?\s*([A-Z0-9]+)[：:，,]?\s*([^，。]+?)[，,]?\s*原因\s*[:：]?\s*([^，。]+)"
            matches = re.findall(pattern, text, re.DOTALL)

            for match in matches:
                fault_code, symptom, cause = match
                chunk = f"故障{fault_code}: {symptom.strip()}，原因: {cause.strip()}"
                chunks.append(chunk)

        elif structure_type == "compatibility_matrix":
            # 提取兼容性信息
            pattern = r"([A-Z]{3,5}-\d{3,5}).*?([A-Z]{3,5}-\d{3,5}).*?(兼容|不兼容|部分兼容)"
            matches = re.findall(pattern, text)

            for match in matches:
                product_a, product_b, compat_type = match
                chunk = f"{product_a}与{product_b}兼容性: {compat_type}"
                chunks.append(chunk)

        else:
            # 默认：按段落分块
            paragraphs = text.split("\n\n")
            chunks = [p.strip() for p in paragraphs if p.strip()]

        logger.info(f"Chunked text: type={structure_type}, chunks={len(chunks)}")
        return chunks

    def smart_chunk(self, content: str, content_type: str = "text") -> List[str]:
        """
        智能分块（自动识别内容类型）

        Args:
            content: 内容
            content_type: 内容类型

        Returns:
            分块列表
        """
        # 检测内容类型
        if "故障代码" in content or "症状" in content:
            detected_type = "fault_table"
        elif "兼容" in content and ("PROD-" in content or "产品" in content):
            detected_type = "compatibility_matrix"
        elif "参数" in content or "规格" in content:
            detected_type = "spec_table"
        elif "版本" in content and "发布" in content:
            detected_type = "version_table"
        else:
            detected_type = "spec_table"

        # 分块
        chunks = self.chunk_text_with_structure(content, detected_type)

        return chunks


# 全局实例
template_chunker = TemplateChunker()
