from typing import List, Dict, Optional
from src.config import get_settings
import re
import logging

logger = logging.getLogger(__name__)


class QueryRewriter:
    """查询改写器 — 基于规则，零延迟"""

    def __init__(self):
        pass

    def rewrite(self, query: str, context: Optional[Dict] = None) -> str:
        """规则改写查询（零延迟）"""
        return self._rule_rewrite(query, context)

    def _rule_rewrite(self, query: str, context: Optional[Dict] = None) -> str:
        """基于规则改写查询"""
        rewritten = query

        # 规则1: 补充产品型号格式
        if "prod" in query.lower() and "-" not in query:
            match = re.search(r'prod\s*(\d+)', query, re.IGNORECASE)
            if match:
                product_num = match.group(1)
                rewritten = re.sub(r'prod\s*\d+', f'PROD-{product_num.zfill(3)}', rewritten, flags=re.IGNORECASE)

        # 规则2: 扩展故障代码格式
        if "e" in query.lower() and "故障" in query:
            match = re.search(r'e(\d+)', query, re.IGNORECASE)
            if match:
                fault_num = match.group(1)
                rewritten = re.sub(r'e\d+', f'E{fault_num.zfill(3)}', rewritten, flags=re.IGNORECASE)

        # 规则3: 补充查询意图关键词
        if "功率" in query or "规格" in query or "参数" in query:
            if "产品" not in query:
                rewritten = f"产品{rewritten}"

        # 规则4: 上下文补充
        if context:
            if "product_code" in context and context["product_code"] not in rewritten:
                rewritten = f"{context['product_code']} {rewritten}"

        logger.info(f"规则改写查询: {query} -> {rewritten}")
        return rewritten

    def expand(self, query: str) -> List[str]:
        """扩展查询（生成多个变体）"""
        expanded = [query]

        synonyms = {
            "功率": ["额定功率", "电源功率", "功率参数"],
            "规格": ["规格参数", "技术规格", "产品规格"],
            "故障": ["故障代码", "错误", "异常"],
            "兼容": ["兼容性", "匹配", "配套"]
        }

        for key, syns in synonyms.items():
            if key in query:
                for syn in syns:
                    expanded.append(query.replace(key, syn))

        # 去重
        expanded = list(dict.fromkeys(expanded))
        return expanded[:5]


    def expand_query(self, query: str) -> List[str]:
        """扩展查询（公开接口，同expand）"""
        return self.expand(query)

    def decompose_query(self, query: str) -> List[str]:
        """分解复杂查询为子查询"""
        separators = ["和", "以及", "还有", "、", "并且"]
        sub_queries = [query]

        for sep in separators:
            if sep in query:
                parts = query.split(sep)
                if len(parts) >= 2:
                    sub_queries = [p.strip() for p in parts if p.strip()]
                    break

        logger.info(f"Decomposed query into {len(sub_queries)} sub-queries")
        return sub_queries if sub_queries else [query]


# Lazy singleton accessor
_rewriter: Optional[QueryRewriter] = None


def get_query_rewriter() -> QueryRewriter:
    """获取查询改写器（延迟初始化）"""
    global _rewriter
    if _rewriter is None:
        _rewriter = QueryRewriter()
    return _rewriter