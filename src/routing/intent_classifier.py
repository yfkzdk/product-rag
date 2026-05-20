from openai import OpenAI
from src.config import get_settings
from typing import Dict, Optional
import logging
import json

logger = logging.getLogger(__name__)


class IntentClassifier:
    """意图分类器"""

    INTENTS = {
        "spec": "产品规格查询",
        "troubleshoot": "故障排查",
        "compatibility": "兼容性查询",
        "general": "一般查询"
    }

    def __init__(self):
        self._client = None
        self._initialized = False

    def _ensure_client(self):
        if self._initialized:
            return

        settings = get_settings()
        api_key = settings.LLM_API_KEY or settings.ANTHROPIC_API_KEY
        if not api_key:
            logger.warning("LLM_API_KEY not set, intent classification will use keyword fallback")
            self._client = None
            self._initialized = True
            return

        try:
            self._client = OpenAI(api_key=api_key, base_url=settings.LLM_BASE_URL, timeout=10.0)
            self._initialized = True
            logger.info(f"LLM client initialized: {settings.LLM_PROVIDER} ({settings.LLM_BASE_URL})")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            self._client = None
            self._initialized = True

    def classify(self, query: str) -> Dict:
        self._ensure_client()

        settings = get_settings()
        if settings.DEMO_MODE or self._client is None:
            return self._keyword_fallback(query)

        try:
            response = self._client.chat.completions.create(
                model=settings.LLM_MODEL_LIGHT,
                max_tokens=256,
                messages=[{
                    "role": "user",
                    "content": f"""分析以下用户查询的意图，返回JSON格式：
{{
  "intent": "spec|troubleshoot|compatibility|general",
  "confidence": 0.0-1.0,
  "keywords": ["关键词1", "关键词2"]
}}

用户查询：{query}"""
                }]
            )

            text = response.choices[0].message.content.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            result = json.loads(text)
            logger.info(f"Intent classified via LLM: {result}")
            return result

        except Exception as e:
            logger.error(f"LLM intent classification failed: {e}")
            return self._keyword_fallback(query)

    def _keyword_fallback(self, query: str) -> Dict:
        query_lower = query.lower()
        if any(kw in query_lower for kw in ["规格", "参数", "型号", "功率", "电压", "电流", "重量", "尺寸", "spec", "parameter"]):
            return {"intent": "spec", "confidence": 0.7, "keywords": []}
        elif any(kw in query_lower for kw in ["故障", "报错", "无法", "启动", "停止", "异常", "fault", "error", "troubleshoot", "fix", "broken", "wont", "doesnt", "not working", "not start"]):
            return {"intent": "troubleshoot", "confidence": 0.7, "keywords": []}
        elif any(kw in query_lower for kw in ["兼容", "替换", "升级", "compat", "upgrade", "replace"]):
            return {"intent": "compatibility", "confidence": 0.7, "keywords": []}
        else:
            return {"intent": "general", "confidence": 0.65, "keywords": []}


_classifier: Optional[IntentClassifier] = None


def get_classifier() -> IntentClassifier:
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier
