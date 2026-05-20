"""
VLM 视觉判断层 — 多提供商支持

- ollama:   本地 Ollama 视觉模型 (MiniCPM-V / Qwen2-VL)，免费，需显存
- anthropic: Claude API (Haiku 低价高效 / Sonnet 高精度)
- openai:    GPT-4o / 兼容 API

职责：不只是提取文字，而是"看懂"图片内容并做出判断
- 图片内容描述（这是什么图？）
- 产品型号/故障现象识别
- 图片质量评估（是否需要重拍）
- 与查询上下文的相关性判断
"""
from typing import Dict, Optional
import logging
import base64
import os
import json

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


VLM_JUDGE_PROMPT = """你是一个工业产品视觉分析专家。请仔细分析这张图片，按以下格式输出 JSON 判断结果：

{
  "category": "图片类别 (product_label|circuit_board|mechanical_parts|error_screen|diagram|document|photo|unclear|irrelevant)",
  "content_description": "图片内容的自然语言描述（中文，50-200字）",
  "extracted_entities": {
    "product_code": "识别到的产品型号，如 PROD-001，没有则 null",
    "fault_code": "识别到的故障代码，如 E001，没有则 null",
    "key_params": ["关键参数列表，如 220V、1.2kg 等"]
  },
  "quality_assessment": {
    "is_clear": true,
    "is_relevant_to_industrial": true,
    "issues": ["质量问题列表，如 模糊/过暗/遮挡/反光，没有则空数组"],
    "needs_rescan": false
  },
  "fault_indicators": ["可能的故障迹象，如 烧焦痕迹/液体泄漏/零件变形/腐蚀，没有则空数组"],
  "relevance_summary": "一句话总结这张图对工业产品查询的价值（中文）"
}

只返回 JSON，不要任何额外文字。"""


class VlmJudge:
    """VLM 视觉判断层 — 多提供商支持

    提供商:
    - ollama:   本地 Ollama (OpenAI兼容API)
    - anthropic: Claude API
    - openai:    GPT-4o / 兼容 API
    """

    def __init__(self, provider: str = "ollama",
                 base_url: str = "http://localhost:11434/v1",
                 model: str = "minicpm-v:8b",
                 api_key: Optional[str] = None):
        self.provider = provider
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self._client = None
        self._available: Optional[bool] = None

    def _ensure_client(self):
        if self._available is not None:
            return

        try:
            if self.provider == "ollama":
                self._init_ollama()
            elif self.provider == "openai":
                self._init_openai()
            elif self.provider == "anthropic":
                self._init_anthropic()
            else:
                self._available = False
                logger.warning("Unknown VLM provider: %s", self.provider)
        except Exception as e:
            self._available = False
            logger.warning("VLM init failed for %s: %s", self.provider, e)

    def _init_ollama(self):
        if not OPENAI_AVAILABLE:
            self._available = False
            return
        self._client = OpenAI(base_url=self.base_url, api_key="ollama", timeout=120.0)
        self._client.models.list()
        self._available = True
        logger.info("VLM: Ollama connected at %s (model=%s)", self.base_url, self.model)

    def _init_openai(self):
        if not OPENAI_AVAILABLE or not self.api_key:
            self._available = False
            return
        self._client = OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=60.0)
        self._available = True
        logger.info("VLM: OpenAI connected (model=%s)", self.model)

    def _init_anthropic(self):
        if not ANTHROPIC_AVAILABLE or not self.api_key:
            self._available = False
            return
        self._client = anthropic.Anthropic(api_key=self.api_key, timeout=60.0)
        self._available = True
        logger.info("VLM: Anthropic connected (model=%s)", self.model)

    def judge(self, image_path: str, query_context: Optional[str] = None) -> Dict:
        self._ensure_client()

        if not self._available or not os.path.exists(image_path):
            return self._fallback(image_path)

        try:
            image_b64 = self._encode_image(image_path)
            mime = self._mime_type(image_path)
        except Exception as e:
            logger.error("Failed to encode image %s: %s", image_path, e)
            return self._fallback(image_path)

        prompt = VLM_JUDGE_PROMPT
        if query_context:
            prompt += f"\n\n用户当前查询：{query_context}\n请在判断时考虑与用户查询的相关性。"

        try:
            if self.provider == "anthropic":
                raw = self._call_anthropic(image_b64, mime, prompt)
            else:
                raw = self._call_openai_compat(image_b64, mime, prompt)
        except Exception as e:
            logger.error("VLM judgment failed: %s", e)
            return self._fallback(image_path)

        result = self._parse_json(raw)
        result["vlm_model"] = self.model
        result["vlm_provider"] = self.provider
        result["vlm_available"] = True
        logger.info("VLM judged image as category=%s", result.get("category", "unknown"))
        return result

    def _call_openai_compat(self, image_b64: str, mime: str, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
                {"type": "text", "text": prompt},
            ]}]
        )
        return response.choices[0].message.content.strip()

    def _call_anthropic(self, image_b64: str, mime: str, prompt: str) -> str:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {
                    "type": "base64",
                    "media_type": mime,
                    "data": image_b64,
                }},
                {"type": "text", "text": prompt},
            ]}]
        )
        return response.content[0].text.strip()

    def quick_check(self, image_path: str) -> Dict:
        result = self.judge(image_path)
        quality = result.get("quality_assessment", {})
        return {
            "pass": quality.get("is_clear", False) and not quality.get("needs_rescan", True),
            "quality": quality,
            "category": result.get("category", "unknown"),
            "needs_rescan": quality.get("needs_rescan", True),
            "issues": quality.get("issues", []),
        }

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _mime_type(self, image_path: str) -> str:
        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                     ".png": "image/png", ".webp": "image/webp",
                     ".gif": "image/gif", ".bmp": "image/bmp"}
        return mime_map.get(ext, "image/jpeg")

    def _parse_json(self, raw: str) -> Dict:
        cleaned = raw
        for marker in ("```json", "```"):
            if marker in cleaned:
                cleaned = cleaned.split(marker)[1].split("```")[0].strip()
                break
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("VLM returned non-JSON, using raw text as description")
            return {
                "category": "unknown",
                "content_description": raw[:500],
                "extracted_entities": {},
                "quality_assessment": {"is_clear": True, "needs_rescan": False, "issues": []},
                "fault_indicators": [],
                "relevance_summary": "",
                "parse_error": True,
            }

    def _fallback(self, image_path: str) -> Dict:
        exists = os.path.exists(image_path)
        return {
            "category": "unknown",
            "content_description": "",
            "extracted_entities": {},
            "quality_assessment": {"is_clear": exists, "needs_rescan": False, "issues": []},
            "fault_indicators": [],
            "relevance_summary": "",
            "vlm_available": False,
            "reason": "vlm_unavailable" if exists else "file_not_found",
        }


_vlm_judge: Optional[VlmJudge] = None


def get_vlm_judge(provider: str = "ollama",
                  base_url: str = "http://localhost:11434/v1",
                  model: str = "minicpm-v:8b",
                  api_key: Optional[str] = None) -> VlmJudge:
    global _vlm_judge
    if _vlm_judge is None:
        _vlm_judge = VlmJudge(provider=provider, base_url=base_url,
                              model=model, api_key=api_key)
    return _vlm_judge
