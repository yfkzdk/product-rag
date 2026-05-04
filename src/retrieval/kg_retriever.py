from typing import List, Dict, Optional
from src.storage.neo4j.client import get_kg_client
from src.config import get_settings
import logging

logger = logging.getLogger(__name__)


class KGRetriever:
    """知识图谱检索器"""

    def __init__(self):
        """初始化"""
        pass

    def retrieve(self, query: str, product_name: Optional[str] = None) -> List[Dict]:
        """知识图谱检索"""
        settings = get_settings()
        if settings.DEMO_MODE or not settings.NEO4J_URI:
            return []

        kg = get_kg_client()

        if not kg.is_available:
            return []

        try:
            results = []

            # 1. 查找相关产品
            if product_name:
                related = kg.find_related_products(product_name)
                for item in related:
                    item["source"] = "knowledge_graph"
                    item["retrieval_type"] = "related_products"
                    results.append(item)

            # 2. 查找故障解决方案
            fault_results = kg.find_fault_solutions(
                product_name or "",
                query
            )
            for item in fault_results:
                item["source"] = "knowledge_graph"
                item["retrieval_type"] = "fault_solution"
                results.append(item)

            # 3. 查找兼容性信息
            if product_name:
                compat = kg.get_product_compatibility(product_name)
                for item in compat:
                    item["source"] = "knowledge_graph"
                    item["retrieval_type"] = "compatibility"
                    results.append(item)

            logger.info(f"知识图谱检索完成: results={len(results)}")
            return results

        except Exception as e:
            logger.error(f"知识图谱检索失败: {e}")
            return []


# Lazy singleton accessor
_kg_retriever: Optional[KGRetriever] = None


def get_kg_retriever() -> KGRetriever:
    """获取知识图谱检索器（延迟初始化）"""
    global _kg_retriever
    if _kg_retriever is None:
        _kg_retriever = KGRetriever()
    return _kg_retriever