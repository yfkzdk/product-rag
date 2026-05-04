from src.config import get_settings
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class PromptTemplates:
    """提示词模板管理"""

    def __init__(self):
        """初始化模板"""
        self._templates = {
            "spec_query": """基于以下产品信息回答用户查询。

产品信息：
{context}

用户查询：{query}

请提供准确的产品规格信息，如果信息不足请明确说明。""",

            "troubleshoot": """基于以下故障排查信息回答用户查询。

相关故障信息：
{context}

用户描述的故障：{query}

请提供：
1. 可能的故障原因
2. 推荐的排查步骤
3. 解决方案

如果信息不足请明确说明。""",

            "compatibility": """基于以下兼容性信息回答用户查询。

兼容性数据：
{context}

用户查询：{query}

请提供准确的产品兼容性信息，包括是否兼容、升级路径、替换方案等。""",

            "general": """基于以下信息回答用户查询。

相关信息：
{context}

用户查询：{query}

请提供准确、有用的回答。如果信息不足请明确说明。"""
        }

    def get_template(self, intent: str) -> str:
        """获取模板"""
        return self._templates.get(intent, self._templates["general"])

    def format_prompt(self, intent: str, context: str, query: str) -> str:
        """格式化提示词"""
        template = self.get_template(intent)
        return template.format(context=context, query=query)

    def get_model(self) -> str:
        """获取LLM模型名称"""
        settings = get_settings()
        return settings.CLAUDE_MODEL_SONNET

    def get_system_prompt(self, intent: str) -> str:
        """获取系统提示词"""
        prompts = {
            "spec": "你是一个产品规格查询助手，专注于提供准确的产品技术参数和规格信息。",
            "troubleshoot": "你是一个故障排查助手，专注于帮助用户诊断和解决产品故障问题。",
            "compatibility": "你是一个产品兼容性查询助手，专注于提供产品间的兼容性和替换信息。",
            "general": "你是一个产品知识助手，帮助用户查询产品相关信息。"
        }
        return prompts.get(intent, prompts["general"])


# Lazy singleton accessor
_templates: Optional[PromptTemplates] = None


def get_templates() -> PromptTemplates:
    """获取模板管理器（延迟初始化）"""
    global _templates
    if _templates is None:
        _templates = PromptTemplates()
    return _templates