"""
故障传播链查询

基于知识图谱的故障影响分析
"""
from typing import List, Dict, Set
import logging

logger = logging.getLogger(__name__)


class FaultPropagation:
    """故障传播链查询"""

    def __init__(self, neo4j_client=None):
        """
        初始化故障传播查询

        Args:
            neo4j_client: Neo4j客户端
        """
        from src.storage.neo4j.client import neo4j_client as default_client
        self.neo4j = neo4j_client or default_client
        logger.info("FaultPropagation initialized")

    def find_root_causes(self, fault_code: str) -> List[Dict]:
        """
        查找故障根本原因

        Args:
            fault_code: 故障代码

        Returns:
            根本原因列表
        """
        query = """
        MATCH (c:Cause)-[:CAUSES]->(f:Fault {fault_code: $fault_code})
        RETURN c.description as cause, c.severity as severity
        ORDER BY c.severity DESC
        """

        try:
            results = self.neo4j.run_query(query, {"fault_code": fault_code})
            logger.info(f"Found {len(results)} root causes for {fault_code}")
            return results
        except Exception as e:
            logger.error(f"Failed to find root causes: {e}")
            return []

    def find_affected_components(self, fault_code: str) -> List[Dict]:
        """
        查找受影响的组件

        Args:
            fault_code: 故障代码

        Returns:
            受影响组件列表
        """
        query = """
        MATCH (f:Fault {fault_code: $fault_code})-[:AFFECTS]->(c:Component)
        RETURN c.name as component, c.criticality as criticality
        ORDER BY c.criticality DESC
        """

        try:
            results = self.neo4j.run_query(query, {"fault_code": fault_code})
            logger.info(f"Found {len(results)} affected components for {fault_code}")
            return results
        except Exception as e:
            logger.error(f"Failed to find affected components: {e}")
            return []

    def trace_propagation_chain(
        self,
        fault_code: str,
        max_depth: int = 5
    ) -> List[Dict]:
        """
        追踪故障传播链

        Args:
            fault_code: 故障代码
            max_depth: 最大深度

        Returns:
            传播链
        """
        query = f"""
        MATCH path = (f:Fault {{fault_code: $fault_code}})-[:PROPAGATES_TO*1..{max_depth}]->(target)
        RETURN path, nodes(path) as nodes, relationships(path) as rels
        LIMIT 20
        """

        try:
            results = self.neo4j.run_query(query, {"fault_code": fault_code})

            # 解析传播链
            chains = []
            for record in results:
                nodes = record.get("nodes", [])
                rels = record.get("rels", [])

                chain = {
                    "fault_code": fault_code,
                    "path_length": len(nodes),
                    "nodes": nodes,
                    "relationships": rels
                }
                chains.append(chain)

            logger.info(f"Traced {len(chains)} propagation chains for {fault_code}")
            return chains

        except Exception as e:
            logger.error(f"Failed to trace propagation chain: {e}")
            return []

    def find_cascading_faults(self, product_code: str) -> List[Dict]:
        """
        查找级联故障

        Args:
            product_code: 产品型号

        Returns:
            级联故障列表
        """
        query = """
        MATCH (p:Product {product_code: $product_code})-[:HAS_FAULT]->(f1:Fault)
        MATCH (f1)-[:PROPAGATES_TO]->(f2:Fault)
        RETURN f1.fault_code as primary_fault, f2.fault_code as secondary_fault,
               f1.symptom as primary_symptom, f2.symptom as secondary_symptom
        """

        try:
            results = self.neo4j.run_query(query, {"product_code": product_code})
            logger.info(f"Found {len(results)} cascading faults for {product_code}")
            return results
        except Exception as e:
            logger.error(f"Failed to find cascading faults: {e}")
            return []

    def analyze_fault_impact(self, fault_code: str) -> Dict:
        """
        分析故障影响范围

        Args:
            fault_code: 故障代码

        Returns:
            影响分析结果
        """
        # 查找根本原因
        root_causes = self.find_root_causes(fault_code)

        # 查找受影响组件
        affected_components = self.find_affected_components(fault_code)

        # 追踪传播链
        propagation_chains = self.trace_propagation_chain(fault_code)

        # 计算影响分数
        impact_score = len(root_causes) * 0.3 + len(affected_components) * 0.5 + len(propagation_chains) * 0.2

        result = {
            "fault_code": fault_code,
            "root_causes": root_causes,
            "affected_components": affected_components,
            "propagation_chains": propagation_chains,
            "impact_score": min(impact_score, 1.0),
            "severity": "HIGH" if impact_score > 0.7 else "MEDIUM" if impact_score > 0.4 else "LOW"
        }

        logger.info(f"Fault impact analysis: {fault_code} -> severity={result['severity']}, score={impact_score:.2f}")
        return result

    def find_similar_faults(self, fault_code: str, limit: int = 5) -> List[Dict]:
        """
        查找相似故障

        Args:
            fault_code: 故障代码
            limit: 结果限制

        Returns:
            相似故障列表
        """
        query = """
        MATCH (f1:Fault {fault_code: $fault_code})
        MATCH (f2:Fault)
        WHERE f1 <> f2
        AND (f1.symptom CONTAINS f2.symptom OR f2.symptom CONTAINS f1.symptom)
        RETURN f2.fault_code as fault_code, f2.symptom as symptom,
               f2.severity as severity
        LIMIT $limit
        """

        try:
            results = self.neo4j.run_query(query, {
                "fault_code": fault_code,
                "limit": limit
            })
            logger.info(f"Found {len(results)} similar faults for {fault_code}")
            return results
        except Exception as e:
            logger.error(f"Failed to find similar faults: {e}")
            return []


# 全局实例
fault_propagation = FaultPropagation()
