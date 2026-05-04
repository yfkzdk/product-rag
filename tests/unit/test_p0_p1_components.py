"""
Pipeline Tracer + Local Vector Store + Metrics 行为测试

测试 P0/P1 新增组件的真实行为
"""
import pytest
import time


# ===== Pipeline Tracer 测试 =====

def test_pipeline_tracer_new_trace():
    """测试创建新追踪记录"""
    from src.observability.pipeline_tracer import get_pipeline_tracer, PipelineTrace

    tracer = get_pipeline_tracer()
    trace = tracer.new_trace("测试查询")
    assert trace is not None
    assert len(trace.trace_id) == 16
    assert trace.metadata["query"] == "测试查询"
    assert len(trace.stages) == 0


def test_pipeline_tracer_add_stage():
    """测试记录阶段"""
    from src.observability.pipeline_tracer import PipelineTrace

    trace = PipelineTrace("test123")
    trace.add_stage("意图分类", 5.2, "ok", "完成", "keyword")
    assert len(trace.stages) == 1
    assert trace.stages[0]["name"] == "意图分类"
    assert trace.stages[0]["duration_ms"] == 5.2
    assert trace.stages[0]["status"] == "ok"


def test_pipeline_tracer_to_dict():
    """测试序列化"""
    from src.observability.pipeline_tracer import PipelineTrace
    import time

    trace = PipelineTrace("test456")
    trace.add_stage("检索", 10.5, "ok", "返回 3 条结果")
    trace.add_stage("生成", 2.0, "ok", "规则引擎")
    trace.metadata["intent"] = "spec"

    time.sleep(0.001)  # 确保 total_ms > 0
    d = trace.to_dict()
    assert d["trace_id"] == "test456"
    assert len(d["stages"]) == 2
    assert d["metadata"]["intent"] == "spec"
    assert d["total_ms"] >= 0


def test_pipeline_tracer_context_manager():
    """测试上下文管理器自动计时"""
    from src.observability.pipeline_tracer import get_pipeline_tracer

    tracer = get_pipeline_tracer()
    trace = tracer.new_trace("ctx test")

    with tracer.trace_stage(trace, "测试阶段", {"key": "value"}) as span:
        time.sleep(0.01)

    assert len(trace.stages) == 1
    assert trace.stages[0]["name"] == "测试阶段"
    assert trace.stages[0]["duration_ms"] > 0
    assert trace.stages[0]["status"] == "ok"


def test_pipeline_tracer_error_propagation():
    """测试异常传播但不丢失追踪"""
    from src.observability.pipeline_tracer import get_pipeline_tracer

    tracer = get_pipeline_tracer()
    trace = tracer.new_trace("error test")

    try:
        with tracer.trace_stage(trace, "会失败的阶段"):
            raise ValueError("模拟错误")
    except ValueError:
        pass

    assert trace.stages[0]["status"] == "error"
    assert "模拟错误" in trace.stages[0]["detail"]


# ===== Local Vector Store 测试 =====

def test_local_vector_store_init():
    """测试本地向量存储初始化"""
    import os
    os.environ["DEMO_MODE"] = "true"

    # 确保有向量文件
    vectors_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "local_vectors.npz")
    from src.storage.local_vector_store import get_local_vector_store

    store = get_local_vector_store()
    assert store is not None
    # is_available 取决于是否有向量文件
    if os.path.exists(vectors_path):
        assert store.is_available
        assert store.count >= 5  # 至少有 ingestion 数据（22 条）或测试数据（5 条）


def test_local_vector_store_search():
    """测试本地向量检索"""
    import os
    from src.storage.local_vector_store import get_local_vector_store

    store = get_local_vector_store()
    if not store.is_available:
        pytest.skip("No local vectors available — run scripts/ingest_manual.py first")

    # 使用简单的 hash 向量搜索
    import hashlib

    def hash_vector(text, dim=384):
        vec = [0.0] * dim
        for seed in range(4):
            h = hashlib.sha256(f"{seed}:{text}".encode()).digest()
            for i in range(min(dim, len(h) * 8)):
                byte_idx = i // 8
                bit_idx = i % 8
                if (h[byte_idx % len(h)] >> bit_idx) & 1:
                    vec[i] += 0.25
        norm = sum(v * v for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    results = store.search(hash_vector("功率 电压 规格"), top_k=3)
    assert len(results) > 0
    assert len(results) <= 3
    for r in results:
        assert "content" in r
        assert "score" in r
        assert "chunk_type" in r


def test_local_vector_store_save_and_search():
    """测试保存和检索完整流程"""
    import numpy as np
    from src.storage.local_vector_store import LocalVectorStore

    store = LocalVectorStore()

    # 创建测试数据
    vectors = np.random.randn(5, 384).astype(np.float32)
    # 归一化
    vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    metadata = [
        {"chunk_id": i, "chunk_type": "spec", "section_title": f"章节{i}",
         "content": f"PROD-001 测试内容 {i}：功率 220V 重量 1.2kg"}
        for i in range(5)
    ]

    store.save(vectors, metadata)
    assert store.count == 5
    assert store.is_available

    # 使用完全匹配的向量搜索
    query = vectors[0].tolist()
    results = store.search(query, top_k=3)
    assert len(results) >= 1
    # 第一个结果应该和查询向量最相似
    assert results[0]["chunk_id"] == 0
    assert results[0]["score"] > 0.9  # 归一化向量自相似度应接近 1.0


def test_local_vector_store_empty():
    """测试空存储"""
    from src.storage.local_vector_store import LocalVectorStore
    # 全新实例，未加载任何数据
    store = LocalVectorStore()
    store._loaded = True
    store._vectors = None
    store._metadata = []

    assert not store.is_available
    assert store.count == 0
    assert store.search([0.1] * 384, top_k=5) == []


# ===== Metrics 测试 =====

def test_metrics_endpoint():
    """测试 /api/v1/metrics 端点"""
    from fastapi.testclient import TestClient
    from src.main import app

    client = TestClient(app)
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200

    data = response.json()
    assert "uptime_seconds" in data
    assert "total_queries" in data
    assert "avg_latency_ms" in data
    assert "pipelines" in data
    assert "alerts" in data


def test_search_response_has_trace():
    """测试搜索响应包含 pipeline_trace 字段"""
    from fastapi.testclient import TestClient
    from src.main import app

    client = TestClient(app)
    response = client.post("/api/v1/search", json={"query": "PROD-001功率"})
    assert response.status_code == 200

    data = response.json()
    assert "pipeline_trace" in data
    trace = data["pipeline_trace"]
    assert "trace_id" in trace
    assert "stages" in trace
    assert "total_ms" in trace
    assert len(trace["stages"]) >= 2  # 至少有意分类和多路检索


def test_search_trace_has_per_stage_timing():
    """测试追踪中每个阶段有耗时记录"""
    from fastapi.testclient import TestClient
    from src.main import app

    client = TestClient(app)
    response = client.post("/api/v1/search", json={"query": "PROD-001功率"})
    data = response.json()
    trace = data["pipeline_trace"]

    for stage in trace["stages"]:
        assert "name" in stage
        assert "duration_ms" in stage
        assert "status" in stage
        assert isinstance(stage["duration_ms"], (int, float))


def test_search_blocked_query_returns_trace():
    """测试拦截查询也返回追踪"""
    from fastapi.testclient import TestClient
    from src.main import app

    client = TestClient(app)
    response = client.post("/api/v1/search", json={"query": "这个产品的参数"})
    data = response.json()
    assert "pipeline_trace" in data
    trace = data["pipeline_trace"]
    # 应该有 blocked 标记
    assert trace["metadata"].get("blocked") == "missing_product_code"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
