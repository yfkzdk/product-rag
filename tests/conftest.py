"""
Shared pytest fixtures for the RAG project.

Pattern: all fixtures are session- or function-scoped as appropriate,
with autouse fixtures for global state cleanup.
"""
import pytest
from unittest.mock import MagicMock, patch

from src.config import Settings


# ── Global state cleanup ──────────────────────────────

@pytest.fixture(autouse=True)
def reset_settings_singleton():
    """Reset the Settings singleton before and after each test."""
    import src.config
    src.config._settings_instance = None
    yield
    src.config._settings_instance = None


# ── Configuration ─────────────────────────────────────

@pytest.fixture
def mock_settings():
    """Central mock settings — demo mode, no API key, no external services."""
    return Settings(
        _env_file=None,
        LLM_API_KEY=None,
        ANTHROPIC_API_KEY=None,
        DEMO_MODE=True,
        BGE_SUBPROCESS=False,
        SKIP_BGE_MODEL=True,
        NEO4J_URI=None,
        NEO4J_USER=None,
        NEO4J_PASSWORD=None,
    )


# ── FastAPI test client ───────────────────────────────

@pytest.fixture
def client(mock_settings):
    """FastAPI TestClient with settings overridden."""
    from src.main import create_app
    from src.config import get_settings

    app = create_app()

    def _get_settings():
        return mock_settings
    app.dependency_overrides[get_settings] = _get_settings

    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c


# ── Retrieval pipeline mocks ──────────────────────────

@pytest.fixture
def mock_retrieval_deps():
    """Mock all retrieval dependencies — vector, HyDE, KG, RRF, rerankers."""
    with patch("src.retrieval.base_retriever.get_vector_retriever") as vec, \
         patch("src.retrieval.base_retriever.get_hyde_retriever") as hyde, \
         patch("src.retrieval.base_retriever.get_kg_retriever") as kg, \
         patch("src.retrieval.base_retriever.get_rrf_fusion") as rrf, \
         patch("src.retrieval.base_retriever.get_reranker") as rerank, \
         patch("src.retrieval.base_retriever.get_context_aware_reranker") as ctx, \
         patch("src.retrieval.base_retriever.get_query_rewriter") as rewrite:

        vec_inst = MagicMock()
        vec_inst.retrieve.return_value = [
            {"chunk_id": 1, "content": "Vector result", "score": 0.9, "chunk_type": "vector"}
        ]
        vec.return_value = vec_inst

        hyde_inst = MagicMock()
        hyde_inst.retrieve.return_value = [
            {"chunk_id": 2, "content": "HyDE result", "score": 0.8, "chunk_type": "hyde_mock"}
        ]
        hyde.return_value = hyde_inst

        kg_inst = MagicMock()
        kg_inst.retrieve.return_value = []
        kg.return_value = kg_inst

        rrf_inst = MagicMock()
        rrf_inst.fuse.return_value = [
            {"chunk_id": 1, "content": "RRF fused", "rrf_score": 0.95, "chunk_type": "vector"},
            {"chunk_id": 2, "content": "RRF fused", "rrf_score": 0.85, "chunk_type": "hyde_mock"},
        ]
        rrf.return_value = rrf_inst

        rerank_inst = MagicMock()
        rerank_inst.rerank.return_value = [
            {"chunk_id": 1, "content": "Reranked", "rrf_score": 0.95, "chunk_type": "vector"},
            {"chunk_id": 2, "content": "Reranked", "rrf_score": 0.85, "chunk_type": "hyde_mock"},
        ]
        rerank.return_value = rerank_inst

        ctx_inst = MagicMock()
        ctx_inst.rerank.return_value = [
            {"chunk_id": 1, "content": "Context reranked", "final_score": 0.92, "chunk_type": "vector"},
        ]
        ctx.return_value = ctx_inst

        rewrite_inst = MagicMock()
        rewrite_inst.rewrite.return_value = "rewritten query"
        rewrite.return_value = rewrite_inst

        yield {
            "vector": vec_inst,
            "hyde": hyde_inst,
            "kg": kg_inst,
            "rrf": rrf_inst,
            "rerank": rerank_inst,
            "context": ctx_inst,
            "rewrite": rewrite_inst,
        }


# ── Common test data ──────────────────────────────────

@pytest.fixture
def sample_query():
    return "PROD-001 E001设备无法启动"


@pytest.fixture
def sample_results():
    return [
        {"chunk_id": 1, "content": "E001故障：电源模块输入电压异常", "score": 0.95, "chunk_type": "vector"},
        {"chunk_id": 2, "content": "PROD-001技术规格说明书", "score": 0.82, "chunk_type": "hyde_mock"},
    ]
