"""
性能基准测试

基于Locust的负载测试
"""
from locust import HttpUser, task, between
import json


class ProductKGUser(HttpUser):
    """产品知识图谱用户"""

    wait_time = between(1, 3)

    @task(3)
    def query_spec(self):
        """规格查询（高频）"""
        self.client.post("/api/v1/query", json={
            "query": "产品PROD-001的规格参数"
        })

    @task(2)
    def query_troubleshoot(self):
        """故障排查（中频）"""
        self.client.post("/api/v1/query", json={
            "query": "产品PROD-001显示错误代码E001"
        })

    @task(1)
    def query_compatibility(self):
        """兼容性查询（低频）"""
        self.client.post("/api/v1/query", json={
            "query": "产品PROD-001和PROD-002是否兼容"
        })

    @task(1)
    def query_hyde(self):
        """HyDE检索增强查询"""
        self.client.post("/api/v1/query", json={
            "query": "如何解决设备启动问题",
            "use_hyde": True
        })

    @task(1)
    def query_kg(self):
        """知识图谱检索"""
        self.client.post("/api/v1/query", json={
            "query": "PROD-001的相关产品和故障",
            "use_kg": True
        })


class HyDEStressUser(HttpUser):
    """HyDE压力测试用户"""

    wait_time = between(0.5, 1.5)

    @task
    def hyde_query(self):
        """HyDE查询压力测试"""
        queries = [
            "PROD-001的功率是多少？",
            "设备无法启动怎么办？",
            "PROD-001和PROD-002兼容吗？",
            "故障代码E001的含义",
            "产品规格参数查询"
        ]

        import random
        query = random.choice(queries)

        self.client.post("/api/v1/query", json={
            "query": query,
            "use_hyde": True
        })


class KGSearchUser(HttpUser):
    """知识图谱检索用户"""

    wait_time = between(2, 5)

    @task
    def kg_n_hop_search(self):
        """N-hop路径探索"""
        self.client.post("/api/v1/kg/search", json={
            "product_code": "PROD-001",
            "n_hops": 2,
            "limit": 10
        })

    @task
    def fault_propagation(self):
        """故障传播链查询"""
        self.client.post("/api/v1/fault/propagation", json={
            "fault_code": "E001",
            "max_depth": 5
        })

    @task
    def community_detection(self):
        """社区检测"""
        self.client.get("/api/v1/community/detect?min_size=3")


# 运行命令：
# locust -f tests/performance/locustfile.py --host=http://localhost:8000
