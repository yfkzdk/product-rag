from openai import OpenAI
from src.config import get_settings
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class ClarificationGenerator:
    """澄清问题生成器"""

    def __init__(self):
        self._client = None
        self._initialized = False

    def _ensure_client(self):
        if self._initialized:
            return

        settings = get_settings()
        api_key = settings.LLM_API_KEY or settings.ANTHROPIC_API_KEY
        if not api_key:
            self._client = None
            self._initialized = True
            return

        try:
            self._client = OpenAI(api_key=api_key, base_url=settings.LLM_BASE_URL, timeout=10.0)
            self._initialized = True
            logger.info(f"LLM client initialized for clarification: {settings.LLM_PROVIDER}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            self._client = None
            self._initialized = True

    def generate(self, query: str, intent: str, confidence: float) -> Optional[List[str]]:
        if confidence >= 0.8:
            return None

        self._ensure_client()

        if self._client is None:
            return self._rule_based_clarification(query, intent)

        settings = get_settings()

        try:
            response = self._client.chat.completions.create(
                model=settings.LLM_MODEL_LIGHT,
                max_tokens=256,
                messages=[{
                    "role": "user",
                    "content": f"""用户查询不够明确，请生成1-2个澄清问题。

用户查询：{query}
意图类型：{intent}
置信度：{confidence}

请返回JSON数组格式的澄清问题列表："""
                }]
            )

            import json
            text = response.choices[0].message.content.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            questions = json.loads(text)
            return questions if isinstance(questions, list) else [str(questions)]

        except Exception as e:
            logger.error(f"澄清问题生成失败: {e}")
            return self._rule_based_clarification(query, intent)

    def _rule_based_clarification(self, query: str, intent: str) -> List[str]:
        """基于规则的澄清问题"""
        questions = []

        if intent == "spec":
            questions.append("请问您要查询哪个产品型号的规格？")
        elif intent == "troubleshoot":
            questions.append("请问您遇到了什么具体的故障现象？")
        elif intent == "compatibility":
            questions.append("请问您要查询哪两个产品之间的兼容性？")
        else:
            questions.append("请问您能提供更多具体信息吗？")

        return questions


    def detect_missing_info(self, query: str, intent: str) -> Dict:
        """检测查询中缺失的关键信息"""
        missing = {}

        if intent == "spec":
            import re
            product_pattern = r'[A-Z]{2,5}-\d{3,5}'
            if not re.search(product_pattern, query):
                missing["missing_product"] = "未提供产品型号"

        elif intent == "troubleshoot":
            import re
            fault_pattern = r'E\d{3,5}'
            if not re.search(fault_pattern, query):
                missing["missing_fault_code"] = "未提供故障代码"

        elif intent == "compatibility":
            import re
            product_pattern = r'[A-Z]{2,5}-\d{3,5}'
            products = re.findall(product_pattern, query)
            if len(products) < 2:
                missing["missing_second_product"] = "需要两个产品型号进行兼容性比较"

        return missing

    def _template_generate(self, query: str, missing_keys: List[str], context: Optional[Dict] = None) -> Dict:
        """基于模板生成澄清问题"""
        questions = []
        for key in missing_keys:
            if "product" in key:
                questions.append("请问您要查询哪个产品型号？")
            elif "fault" in key:
                questions.append("请问您遇到了什么故障现象或故障代码？")
            else:
                questions.append("请问您能提供更多具体信息吗？")

        return {
            "question": " ".join(questions) if questions else "请提供更多信息",
            "missing_fields": missing_keys,
            "original_query": query
        }


# Lazy singleton accessor
_generator: Optional[ClarificationGenerator] = None


def get_clarification_generator() -> ClarificationGenerator:
    """获取澄清问题生成器（延迟初始化）"""
    global _generator
    if _generator is None:
        _generator = ClarificationGenerator()
    return _generator