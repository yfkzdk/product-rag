"""
社区检测和报告生成

基于图算法的产品社区发现
"""
from typing import List, Dict, Set
import logging

logger = logging.getLogger(__name__)


class CommunityDetector:
    """社区检测器"""

    def __init__(self, neo4j_client=None):
        """
        初始化社区检测器

        Args:
            neo4j_client: Neo4j客户端
        """
        from src.storage.neo4j.client import neo4j_client as default_client
        self.neo4j = neo4j_client or default_client
        logger.info("CommunityDetector initialized")

    def detect_product_communities(self, min_size: int = 3) -> List[Dict]:
        """
        检测产品社区

        Args:
            min_size: 最小社区大小

        Returns:
            社区列表
        """
        # 使用标签传播算法（LPA）
        query = """
        CALL gds.labelPropagation.stream('product-graph')
        YIELD nodeId, communityId
        WITH communityId, collect(gds.util.asNode(nodeId).product_code) as members
        WHERE size(members) >= $min_size
        RETURN communityId, members, size(members) as member_count
        ORDER BY member_count DESC
        """

        try:
            results = self.neo4j.run_query(query, {"min_size": min_size})
            logger.info(f"Detected {len(results)} product communities")
            return results
        except Exception as e:
            logger.warning(f"GDS not available, using fallback: {e}")
            return self._fallback_community_detection(min_size)

    def _fallback_community_detection(self, min_size: int = 3) -> List[Dict]:
        """降级社区检测（基于连通分量）"""
        query = """
        MATCH (p:Product)-[:COMPATIBLE_WITH]-(other:Product)
        WITH p, collect(other.product_code) as neighbors
        RETURN p.product_code as product, neighbors
        """

        try:
            results = self.neo4j.run_query(query)

            # 简单的连通分量检测
            visited = set()
            communities = []

            for record in results:
                product = record.get("product")
                if product in visited:
                    continue

                # BFS遍历
                community = self._bfs_traverse(product, results)
                if len(community) >= min_size:
                    communities.append({
                        "communityId": f"community-{len(communities)}",
                        "members": list(community),
                        "member_count": len(community)
                    })
                    visited.update(community)

            logger.info(f"Fallback detected {len(communities)} communities")
            return communities

        except Exception as e:
            logger.error(f"Fallback community detection failed: {e}")
            return []

    def _bfs_traverse(self, start: str, graph_data: List[Dict]) -> Set[str]:
        """BFS遍历"""
        from collections import deque

        visited = set()
        queue = deque([start])

        while queue:
            node = queue.popleft()
            if node in visited:
                continue

            visited.add(node)

            # 查找邻居
            for record in graph_data:
                if record.get("product") == node:
                    neighbors = record.get("neighbors", [])
                    for neighbor in neighbors:
                        if neighbor not in visited:
                            queue.append(neighbor)

        return visited

    def generate_community_report(self, community_id: str, members: List[str]) -> Dict:
        """
        生成社区报告

        Args:
            community_id: 社区ID
            members: 成员列表

        Returns:
            社区报告
        """
        # 查询社区统计信息
        query = """
        MATCH (p:Product)
        WHERE p.product_code IN $members
        RETURN collect(DISTINCT p.category) as categories,
               count(p) as product_count
        """

        try:
            results = self.neo4j.run_query(query, {"members": members})
            stats = results[0] if results else {}

            # 生成报告
            report = {
                "community_id": community_id,
                "member_count": len(members),
                "members": members[:10],  # 限制显示数量
                "categories": stats.get("categories", []),
                "summary": f"产品社区包含{len(members)}个产品，主要类别：{', '.join(stats.get('categories', [])[:3])}",
                "key_products": members[:5],
                "compatibility_density": self._calculate_density(members)
            }

            logger.info(f"Generated community report: {community_id}")
            return report

        except Exception as e:
            logger.error(f"Failed to generate community report: {e}")
            return {
                "community_id": community_id,
                "member_count": len(members),
                "members": members,
                "summary": f"产品社区包含{len(members)}个产品"
            }

    def _calculate_density(self, members: List[str]) -> float:
        """计算社区密度"""
        if len(members) < 2:
            return 0.0

        # 查询内部连接数
        query = """
        MATCH (a:Product)-[:COMPATIBLE_WITH]-(b:Product)
        WHERE a.product_code IN $members AND b.product_code IN $members
        RETURN count(DISTINCT [a.product_code, b.product_code]) as edge_count
        """

        try:
            results = self.neo4j.run_query(query, {"members": members})
            edge_count = results[0].get("edge_count", 0) if results else 0

            # 计算密度：实际边数 / 可能边数
            max_edges = len(members) * (len(members) - 1) / 2
            density = edge_count / max_edges if max_edges > 0 else 0.0

            return round(density, 2)

        except Exception as e:
            logger.error(f"Failed to calculate density: {e}")
            return 0.0

    def find_product_community(self, product_code: str) -> Dict:
        """
        查找产品所属社区

        Args:
            product_code: 产品型号

        Returns:
            社区信息
        """
        communities = self.detect_product_communities()

        for community in communities:
            if product_code in community.get("members", []):
                return self.generate_community_report(
                    community.get("communityId"),
                    community.get("members")
                )

        logger.info(f"Product {product_code} not found in any community")
        return {}

    def get_community_recommendations(self, product_code: str) -> List[str]:
        """
        获取社区推荐（相似产品）

        Args:
            product_code: 产品型号

        Returns:
            推荐产品列表
        """
        community = self.find_product_community(product_code)

        if not community:
            return []

        members = community.get("members", [])

        # 排除自己
        recommendations = [m for m in members if m != product_code]

        logger.info(f"Generated {len(recommendations)} recommendations for {product_code}")
        return recommendations[:5]


# 全局实例
community_detector = CommunityDetector()
