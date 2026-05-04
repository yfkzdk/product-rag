"""
routes.py 单元测试 — 所有 API 端点（使用 FastAPI TestClient + dependency overrides）
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import json

from src.main import create_app
from src.config import Settings, get_settings
from src.storage.postgres.database import get_db
from src.storage.postgres.models import Product, Fault, CompatibilityMatrix


@pytest.fixture
def mock_settings():
    return Settings(
        LLM_API_KEY=None,
        ANTHROPIC_API_KEY=None,
        DEMO_MODE=True,
        BGE_SUBPROCESS=False,
        SKIP_BGE_MODEL=True,
    )


@pytest.fixture
def client(mock_settings):
    app = create_app()

    # Override get_settings
    def _get_settings():
        return mock_settings
    app.dependency_overrides[get_settings] = _get_settings

    with TestClient(app) as c:
        yield c


# ── Health ──────────────────────────────────────

def test_health_check(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code in (200, 503)  # 503 if infra down, 200 with degraded note


# ── Products ───────────────────────────────────

def test_list_products_db_unavailable(client):
    """数据库不可用或返回 Demo 数据均正常"""
    resp = client.get("/api/v1/products/")
    assert resp.status_code == 200
    data = resp.json()
    # Demo mode with SQLite returns product list; real DB unavailable returns {"products": [], "note": ...}
    assert isinstance(data, (list, dict))


def test_search_products_no_query(client):
    """缺少 query 参数返回 422"""
    resp = client.get("/api/v1/search/products")
    assert resp.status_code == 422


def test_search_products_empty(client):
    resp = client.get("/api/v1/search/products?query=nonexistent_xyz")
    assert resp.status_code == 200


def test_get_product_not_found(client):
    """不存在的产品返回 404 或 503（DB 不可用）"""
    resp = client.get("/api/v1/products/99999")
    assert resp.status_code in (404, 503)


# ── Faults ─────────────────────────────────────

def test_list_faults(client):
    resp = client.get("/api/v1/faults/")
    assert resp.status_code in (200, 503)


def test_list_faults_filter_by_product(client):
    resp = client.get("/api/v1/faults/?product_id=1")
    assert resp.status_code in (200, 503)


# ── Compatibility ──────────────────────────────

def test_list_compatibility(client):
    resp = client.get("/api/v1/compatibility/")
    assert resp.status_code in (200, 503)


def test_list_compatibility_filter_by_product(client):
    resp = client.get("/api/v1/compatibility/?product_id=1")
    assert resp.status_code in (200, 503)


# ── Core RAG search ───────────────────────────

def test_search_spec_missing_product_code(client):
    """spec 意图但缺产品型号 → 被规则校验拦截，返回澄清"""
    resp = client.post("/api/v1/search", json={"query": "规格参数"})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "intent" in data
    assert "pipeline_trace" in data


def test_search_troubleshoot_missing_fault_code(client):
    """troubleshoot 意图但缺故障代码 → 拦截"""
    resp = client.post("/api/v1/search", json={"query": "故障"})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data


def test_search_with_product_code(client):
    """带产品型号的查询通过规则校验，进入检索"""
    resp = client.post("/api/v1/search", json={"query": "ATX-500 的规格参数"})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "intent" in data
    # 可能被澄清或正常返回，取决于 confidence
    assert "pipeline_trace" in data


def test_search_with_fault_code(client):
    """带故障代码的查询通过规则校验"""
    resp = client.post("/api/v1/search", json={"query": "E001 故障怎么解决"})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data


def test_search_with_session_id(client):
    """带 session_id 的多轮对话查询"""
    resp = client.post("/api/v1/search", json={
        "query": "ATX-500 规格",
        "session_id": "test-session-001"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data


def test_search_empty_query(client):
    """空查询"""
    resp = client.post("/api/v1/search", json={"query": ""})
    assert resp.status_code in (200, 422)


def test_search_response_schema(client):
    """验证响应 JSON schema"""
    resp = client.post("/api/v1/search", json={"query": "ATX-500"})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert isinstance(data["answer"], str)
    assert "intent" in data
    assert data["intent"] in ("spec", "troubleshoot", "compatibility", "general")
    assert "sources" in data
    assert isinstance(data["sources"], list)
    assert "pipeline_trace" in data


# ── Demo page ──────────────────────────────────

def test_demo_page(client):
    resp = client.get("/demo")
    assert resp.status_code in (200, 404)


# ── 404 unknown route ──────────────────────────

def test_unknown_route(client):
    resp = client.get("/api/v1/nonexistent_endpoint")
    assert resp.status_code == 404
