from openai import OpenAI
from src.config import get_settings
from src.generation.prompt_templates import get_templates
from typing import Dict, Optional, AsyncIterator
import logging

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """响应生成器 — 支持 DeepSeek (OpenAI 兼容) / Anthropic"""

    def __init__(self):
        self._client = None
        self._initialized = False

    def _ensure_client(self):
        if self._initialized:
            return

        settings = get_settings()
        api_key = settings.LLM_API_KEY or settings.ANTHROPIC_API_KEY
        if not api_key:
            logger.warning("LLM_API_KEY not set, response generation will use rule fallback")
            self._client = None
            self._initialized = True
            return

        try:
            self._client = OpenAI(api_key=api_key, base_url=settings.LLM_BASE_URL)
            self._initialized = True
            logger.info(f"LLM client initialized for generation: {settings.LLM_PROVIDER}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            self._client = None
            self._initialized = True

    def _rule_based_generate(self, query: str, context: str, intent: str) -> Dict:
        """Rule-based fallback when LLM is unavailable — build answer from retrieved context."""
        import re

        context_stripped = context.strip()
        sources = []

        blocks = re.findall(r'\[(\w+)\]\s*([^\[]+)', context_stripped)
        if not blocks and context_stripped:
            blocks = [("document", context_stripped)]

        if intent == "spec" and blocks:
            detail_parts = []
            for src, text in blocks:
                sources.append(src)
                pairs = re.findall(r'(\S+?)[：:]\s*(\S+)', text)
                for k, v in pairs[:6]:
                    detail_parts.append(f"- {k}：{v}")
            if detail_parts:
                answer = "根据知识库信息，找到以下规格参数：\n" + "\n".join(detail_parts)
            else:
                answer = f"根据知识库检索到 {len(blocks)} 条相关信息：\n" + "\n".join(
                    f"- [{src}] {text[:120]}..." if len(text) > 120 else f"- [{src}] {text}"
                    for src, text in blocks[:3]
                )
            return {"answer": answer, "intent": intent, "sources": sources}

        if intent == "troubleshoot" and blocks:
            parts = []
            for src, text in blocks:
                sources.append(src)
                if "解决" in text or "方案" in text or "步骤" in text:
                    parts.append(text[:200])
            if parts:
                answer = "根据故障知识库，建议如下：\n" + "\n".join(f"- {p}" for p in parts[:3])
            else:
                answer = "未找到该故障的具体解决方案，建议联系技术支持并提供故障代码。"
            return {"answer": answer, "intent": intent, "sources": sources}

        if blocks:
            for src, text in blocks:
                sources.append(src)
            lines = []
            for src, text in blocks[:3]:
                snippet = text[:150] + ("..." if len(text) > 150 else "")
                lines.append(f"[{src}] {snippet}")
            answer = "以下是相关信息摘要：\n" + "\n\n".join(lines)
        else:
            answer = f"关于「{query[:50]}」，暂时没有找到相关信息。请尝试使用产品型号（如 PROD-001）或故障代码（如 E001）进行查询。"

        return {"answer": answer, "intent": intent, "sources": sources}

    def generate(self, query: str, context: str, intent: str = "general") -> Dict:
        self._ensure_client()

        if self._client is None:
            return self._rule_based_generate(query, context, intent)

        settings = get_settings()
        templates = get_templates()

        try:
            prompt = templates.format_prompt(intent, context, query)
            system_prompt = templates.get_system_prompt(intent)

            response = self._client.chat.completions.create(
                model=settings.LLM_MODEL_CHAT,
                max_tokens=2048,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ]
            )

            answer = response.choices[0].message.content

            # Extract sources from context blocks
            import re
            sources = [m.group(1) for m in re.finditer(r'\[(\w+)\]', context)]

            return {
                "answer": answer,
                "intent": intent,
                "sources": list(set(sources)) if sources else [],
                "model": settings.LLM_MODEL_CHAT,
            }

        except Exception as e:
            logger.error(f"LLM generation failed, falling back to rule: {e}")
            return self._rule_based_generate(query, context, intent)

    async def generate_stream(self, query: str, context: str, intent: str = "general") -> AsyncIterator[str]:
        self._ensure_client()

        if self._client is None:
            result = self._rule_based_generate(query, context, intent)
            yield result["answer"]
            return

        settings = get_settings()
        templates = get_templates()

        try:
            prompt = templates.format_prompt(intent, context, query)
            system_prompt = templates.get_system_prompt(intent)

            stream = self._client.chat.completions.create(
                model=settings.LLM_MODEL_CHAT,
                max_tokens=2048,
                stream=True,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ]
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Stream generation failed: {e}")
            result = self._rule_based_generate(query, context, intent)
            yield result["answer"]


_generator: Optional[ResponseGenerator] = None


def get_generator() -> ResponseGenerator:
    global _generator
    if _generator is None:
        _generator = ResponseGenerator()
    return _generator
