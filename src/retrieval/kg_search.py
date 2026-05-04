"""
知识图谱检索

基于RAGFlow的N-hop路径探索
"""
from typing import List, Dict, Set, Optional
import logging

logger = logging.getLogger(__name__)


class KGSearch:
    """知识图谱检索"""

    def __init__(self, neo4j_client=None):
        """
        初始化知识图谱检索

        Args:
            neo4j_client: Neo4j客户端
        """
        from src.storage.neo4j.client import neo4j_client as default_client
        self.neo4j = neo4j_client or default_client
        logger.info("KGSearch initialized")

    async def extract_entities(self, question: str) -> List[str]:
        """
        从问题中提取实体

        Args:
            question: 用户问题

        Returns:
            实体列表
        """
        import re

        entities = []

        # 提取产品型号
        product_pattern = r'[A-Z]{3,5}-\d{3,5}'
        product_matches = re.findall(product_pattern, question)
        entities.extend(product_matches)

        # 提取故障代码
        fault_pattern = r'E\d{3,5}'
        fault_matches = re.findall(fault_pattern, question)
        entities.extend(fault_matches)

        logger.info(f"Extracted entities: {entities}")
        return entities

    def get_entities_by_keywords(self, keywords: List[str]) -> List[Dict]:
        """
        通过关键词获取实体

        Args:
            keywords: 关键词列表

        Returns:
            实体列表
        """
        entities = []

        for keyword in keywords:
            # 查询Neo4j
            query = """
            MATCH (n)
            WHERE n.product_code CONTAINS $keyword
               OR n.name CONTAINS $keyword
               OR n.fault_code CONTAINS $keyword
            RETURN n
            LIMIT 10
            """

            try:
                results = self.neo4j.run_query(query, {"keyword": keyword})
                entities.extend(results)
            except Exception as e:
                logger.error(f"Failed to get entities: {e}")

        logger.info(f"Found {len(entities)} entities for keywords: {keywords}")
        return entities

    def explore_n_hop_paths(
        self,
        start_entities: List[str],
        n_hops: int = 2,
        max_paths: int = 20
    ) -> List[Dict]:
        """
        N-hop路径探索

        Args:
            start_entities: 起始实体列表
            n_hops: 跳数
            max_paths: 最大路径数

        Returns:
            路径列表
        """
        all_paths = []

        for entity in start_entities:
            # 查询N-hop路径
            paths = self.neo4j.find_n_hop_paths(
                start_node=entity,
                node_type="Product",
                n_hops=n_hops,
                limit=max_paths
            )

            all_paths.extend(paths)

        logger.info(f"Explored {len(all_paths)} paths ({n_hops} hops)")
        return all_paths

    def get_relations_by_text(self, question: str) -> List[Dict]:
        """
        通过文本获取关系

        Args:
            question: 用户问题

        Returns:
            关系列表
        """
        # 基于关键词匹配关系
        relations = []

        if "兼容" in question:
            query = """
            MATCH (a:Product)-[r:COMPATIBLE_WITH]->(b:Product)
            RETURN a.product_code as product_a, b.product_code as product_b, r.type as compatibility_type
            LIMIT 10
            """

            try:
                results = self.neo4j.run_query(query)
                relations.extend(results)
            except Exception as e:
                logger.error(f"Failed to get relations: {e}")

        if "故障" in question or "原因" in question:
            query = """
            MATCH (c:Cause)-[r:CAUSES]->(f:Fault)
            RETURN c.description as cause, f.fault_code as fault_code, f.symptom as symptom
            LIMIT 10
            """

            try:
                results = self.neo4j.run_query(query)
                relations.extend(results)
            except Exception as e:
                logger.error(f"Failed to get relations: {e}")

        logger.info(f"Found {len(relations)} relations")
        return relations

    def get_community_reports(self, entities: List[str]) -> List[Dict]:
        """
        获取社区报告

        Args:
            entities: 实体列表

        Returns:
            社区报告列表
        """
        # Mock实现（实际需要社区检测算法）
        reports = []

        for entity in entities[:3]:  # 限制数量
            reports.append({
                "entity": entity,
                "community_id": f"community-{hash(entity) % 10}",
                "summary": f"{entity}相关的产品社区",
                "member_count": 5
            })

        logger.info(f"Generated {len(reports)} community reports")
        return reports

    async def retrieval(self, question: str, kb_ids: List[str] = None) -> Dict:
        """
        知识图谱检索（完整流程）

        Args:
            question: 用户问题
            kb_ids: 知识库ID列表

        Returns:
            检索结果
        """
        logger.info(f"KG retrieval: question='{question[:50]}...'")

        # 1. 查询重写 - 提取实体和关键词
        entities_from_query = await self.extract_entities(question)

        # 2. 实体检索
        ents_from_query = self.get_entities_by_keywords(entities_from_query)

        # 3. N-hop路径探索（默认2跳）
        paths = self.explore_n_hop_paths(
            start_entities=entities_from_query,
            n_hops=2,
            max_paths=20
        )

        # 4. 关系检索
        relations = self.get_relations_by_text(question)

        # 5. 社区报告检索
        community_reports = self.get_community_reports(entities_from_query)

        result = {
            "entities": ents_from_query,
            "paths": paths,
            "relations": relations,
            "community_reports": community_reports
        }

        logger.info(f"KG retrieval complete: {len(ents_from_query)} entities, {len(paths)} paths, {len(relations)} relations")
        return result


# 全局实例
kg_search = KGSearch()
