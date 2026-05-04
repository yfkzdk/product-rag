from openai import OpenAI
from src.config import get_settings
from typing import List, Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)


class EntityExtractor:
    """实体提取器"""

    def __init__(self):
        self._client = None
        self._initialized = False

    def _ensure_client(self):
        if self._initialized:
            return

        settings = get_settings()
        api_key = settings.LLM_API_KEY or settings.ANTHROPIC_API_KEY
        if not api_key:
            logger.warning("LLM_API_KEY not set, entity extraction disabled")
            self._client = None
            self._initialized = True
            return

        try:
            self._client = OpenAI(api_key=api_key, base_url=settings.LLM_BASE_URL)
            self._initialized = True
            logger.info(f"LLM client initialized for entity extraction: {settings.LLM_PROVIDER}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client for entity extraction: {e}")
            self._client = None
            self._initialized = True

    def extract(self, text: str) -> Dict:
        self._ensure_client()

        if self._client is None:
            return {"entities": [], "relations": []}

        settings = get_settings()

        try:
            response = self._client.chat.completions.create(
                model=settings.LLM_MODEL_LIGHT,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": f"""从以下文本中提取实体和关系，返回JSON格式：
{{
  "entities": [{{"name": "实体名", "type": "Product|Fault|Solution|Component", "attributes": {{}}}}],
  "relations": [{{"source": "实体1", "target": "实体2", "type": "关系类型"}}]
}}

文本：{text}"""
                }]
            )

            text_response = response.choices[0].message.content.strip()
            if "```json" in text_response:
                text_response = text_response.split("```json")[1].split("```")[0].strip()
            elif "```" in text_response:
                text_response = text_response.split("```")[1].split("```")[0].strip()

            result = json.loads(text_response)
            logger.info(f"实体提取完成: entities={len(result.get('entities', []))}, relations={len(result.get('relations', []))}")
            return result

        except Exception as e:
            logger.error(f"实体提取失败: {e}")
            return {"entities": [], "relations": []}


    def _rule_extract_entities(self, text: str) -> List[Dict]:
        """基于规则提取实体（不依赖LLM）"""
        import re
        entities = []

        # 提取产品型号
        product_pattern = r'[A-Z]{2,5}-\d{3,5}'
        for match in re.finditer(product_pattern, text):
            entities.append({
                "type": "Product",
                "name": match.group(),
                "position": match.start()
            })

        # 提取故障代码
        fault_pattern = r'E\d{3,5}'
        for match in re.finditer(fault_pattern, text):
            entities.append({
                "type": "Fault",
                "name": match.group(),
                "position": match.start()
            })

        # 提取参数
        param_pattern = r'(\d+(?:\.\d+)?)\s*(V|A|W|kg|°C|Hz)'
        for match in re.finditer(param_pattern, text):
            entities.append({
                "type": "Parameter",
                "name": match.group(),
                "position": match.start()
            })

        return entities

    def extract_relations(self, text: str, entities: List[Dict]) -> List[Dict]:
        """从文本中提取实体间关系"""
        relations = []

        product_names = [e["name"] for e in entities if e["type"] == "Product"]

        # 检测兼容关系
        if "兼容" in text and len(product_names) >= 2:
            for i in range(len(product_names)):
                for j in range(i + 1, len(product_names)):
                    relations.append({
                        "source": product_names[i],
                        "target": product_names[j],
                        "type": "COMPATIBLE_WITH"
                    })

        # 检测故障关系
        fault_names = [e["name"] for e in entities if e["type"] == "Fault"]
        if fault_names and product_names:
            for fault in fault_names:
                for product in product_names:
                    relations.append({
                        "source": product,
                        "target": fault,
                        "type": "HAS_FAULT"
                    })

        return relations


# Lazy singleton accessor
_extractor: Optional[EntityExtractor] = None


def get_entity_extractor() -> EntityExtractor:
    """获取实体提取器（延迟初始化）"""
    global _extractor
    if _extractor is None:
        _extractor = EntityExtractor()
    return _extractor