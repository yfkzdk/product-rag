from neo4j import GraphDatabase
from src.config import get_settings
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class KnowledgeGraphStore:
    """Neo4j知识图谱存储"""

    def __init__(self):
        """初始化（延迟连接）"""
        self._driver = None
        self._initialized = False

    def _ensure_connection(self):
        """确保连接已建立"""
        if self._initialized:
            return

        settings = get_settings()
        if not all([settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD]):
            logger.warning("Neo4j credentials not configured, knowledge graph features disabled")
            return

        try:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            # Verify connectivity
            self._driver.verify_connectivity()
            self._initialized = True
            logger.info(f"Neo4j connected: {settings.NEO4J_URI}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self._driver = None

    @property
    def is_available(self) -> bool:
        """检查Neo4j是否可用"""
        if not self._initialized:
            self._ensure_connection()
        return self._driver is not None

    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """执行Cypher查询"""
        self._ensure_connection()
        if self._driver is None:
            return []

        try:
            with self._driver.session() as session:
                result = session.run(query, params or {})
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            return []

    def run_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """执行Cypher查询（别名，兼容不同调用方）"""
        return self.execute_query(query, params)

    def create_product_node(self, product_data: Dict) -> bool:
        """创建产品节点"""
        self._ensure_connection()
        if self._driver is None:
            logger.info("Neo4j not available, product node creation skipped (mock)")
            return True

        try:
            query = """
            MERGE (p:Product {product_code: $product_code})
            SET p.name = $name, p.specifications = $specifications, p.category = $category
            """
            params = {
                "product_code": product_data.get("product_code", ""),
                "name": product_data.get("name", ""),
                "specifications": product_data.get("specifications", {}),
                "category": product_data.get("category", "")
            }
            self.execute_query(query, params)
            return True
        except Exception as e:
            logger.error(f"Failed to create product node: {e}")
            return False

    def find_n_hop_paths(self, start_node: str = None, node_type: str = "Product",
                         n_hops: int = 2, limit: int = 20) -> List[Dict]:
        """N-hop路径查询"""
        self._ensure_connection()
        if self._driver is None:
            return []

        start = start_node
        if not start:
            return []

        try:
            query = f"""
            MATCH path = (n:{node_type} {{product_code: $start_node}})-[*1..{n_hops}]-(m)
            RETURN path, n.product_code as start, m.product_code as target, length(path) as hops
            LIMIT $limit
            """
            results = self.execute_query(query, {"start_node": start, "limit": limit})
            logger.info(f"Found {len(results)} {n_hops}-hop paths for {start}")
            return results
        except Exception as e:
            logger.error(f"Failed to find n-hop paths: {e}")
            return []

    def find_related_products(self, product_name: str, relation_type: Optional[str] = None) -> List[Dict]:
        """查找相关产品"""
        if relation_type:
            query = """
            MATCH (p1:Product {name: $name})-[r]->(p2:Product)
            WHERE type(r) = $relation_type
            RETURN p2.name AS name, type(r) AS relation, p2.category AS category
            """
            params = {"name": product_name, "relation_type": relation_type}
        else:
            query = """
            MATCH (p1:Product {name: $name})-[r]-(p2:Product)
            RETURN p2.name AS name, type(r) AS relation, p2.category AS category
            """
            params = {"name": product_name}

        return self.execute_query(query, params)

    def find_fault_solutions(self, product_name: str, fault_description: str) -> List[Dict]:
        """查找故障解决方案"""
        query = """
        MATCH (p:Product {name: $name})-[:HAS_FAULT]->(f:Fault)
        WHERE f.description CONTAINS $fault_desc
        MATCH (f)-[:HAS_SOLUTION]->(s:Solution)
        RETURN f.description AS fault, s.description AS solution, s.confidence AS confidence
        """
        params = {"name": product_name, "fault_desc": fault_description}
        return self.execute_query(query, params)

    def get_product_compatibility(self, product_name: str) -> List[Dict]:
        """获取产品兼容性信息"""
        query = """
        MATCH (p1:Product {name: $name})-[r:COMPATIBLE_WITH]->(p2:Product)
        RETURN p2.name AS product, r.confidence AS confidence, r.notes AS notes
        UNION
        MATCH (p1:Product {name: $name})-[r:INCOMPATIBLE_WITH]->(p2:Product)
        RETURN p2.name AS product, r.confidence AS confidence, r.notes AS notes
        """
        params = {"name": product_name}
        return self.execute_query(query, params)

    def close(self):
        """关闭连接"""
        if self._driver:
            self._driver.close()
            self._driver = None
            self._initialized = False


# Lazy singleton accessor
_kg_client: Optional[KnowledgeGraphStore] = None


def get_kg_client() -> KnowledgeGraphStore:
    """获取知识图谱客户端（延迟初始化）"""
    global _kg_client
    if _kg_client is None:
        _kg_client = KnowledgeGraphStore()
    return _kg_client


# Legacy alias for test compatibility
Neo4jClient = KnowledgeGraphStore

# Module-level singleton for compatibility with kg_search, fault_propagation, community_detector
neo4j_client = KnowledgeGraphStore()