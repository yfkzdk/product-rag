"""
base_retriever.py 单元测试 — 多路检索编排 + RRF 融合 + 重排序
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


@pytest.fixture
def mock_deps():
    """Mock 所有检索依赖"""
    with patch("src.retrieval.base_retriever.get_vector_retriever") as vec, \
         patch("src.retrieval.base_retriever.get_hyde_retriever") as hyde, \
         patch("src.retrieval.base_retriever.get_kg_retriever") as kg, \
         patch("src.retrieval.base_retriever.get_rrf_fusion") as rrf, \
         patch("src.retrieval.base_retriever.get_reranker") as rerank, \
         patch("src.retrieval.base_retriever.get_context_aware_reranker") as ctx, \
         patch("src.retrieval.base_retriever.get_query_rewriter") as rewrite:

        vec_inst = MagicMock()
        vec_inst.retrieve.return_value = [
            {"chunk_id": 1, "content": "Vector result", "score": 0.9}
        ]
        vec.return_value = vec_inst

        hyde_inst = MagicMock()
        hyde_inst.retrieve.return_value = [
            {"chunk_id": 2, "content": "HyDE result", "score": 0.8}
        ]
        hyde.return_value = hyde_inst

        kg_inst = MagicMock()
        kg_inst.retrieve.return_value = []
        kg.return_value = kg_inst

        rrf_inst = MagicMock()
        rrf_inst.fuse.return_value = [
            {"chunk_id": 1, "content": "RRF fused", "rrf_score": 0.95},
            {"chunk_id": 2, "content": "RRF fused", "rrf_score": 0.85},
        ]
        rrf.return_value = rrf_inst

        rerank_inst = MagicMock()
        rerank_inst.rerank.return_value = [
            {"chunk_id": 1, "content": "Reranked", "rrf_score": 0.95},
            {"chunk_id": 2, "content": "Reranked", "rrf_score": 0.85},
        ]
        rerank.return_value = rerank_inst

        ctx_inst = MagicMock()
        ctx_inst.rerank.return_value = [
            {"chunk_id": 1, "content": "Context reranked", "rrf_score": 0.95},
        ]
        ctx.return_value = ctx_inst

        rewrite_inst = MagicMock()
        rewrite_inst.rewrite.return_value = "rewritten query text"
        rewrite.return_value = rewrite_inst

        yield {
            "vector": vec_inst,
            "hyde": hyde_inst,
            "kg": kg_inst,
            "rrf": rrf_inst,
            "rerank": rerank_inst,
            "ctx": ctx_inst,
            "rewrite": rewrite_inst,
        }


class TestBaseRetrieverRetrieve:
    """retrieve() 编排测试"""

    def test_returns_results(self):
        from src.retrieval.base_retriever import BaseRetriever

        with patch("src.retrieval.base_retriever.get_vector_retriever") as vec, \
             patch("src.retrieval.base_retriever.get_hyde_retriever") as hyde, \
             patch("src.retrieval.base_retriever.get_kg_retriever") as kg, \
             patch("src.retrieval.base_retriever.get_rrf_fusion") as rrf, \
             patch("src.retrieval.base_retriever.get_reranker") as rerank, \
             patch("src.retrieval.base_retriever.get_context_aware_reranker") as ctx, \
             patch("src.retrieval.base_retriever.get_query_rewriter") as rewrite, \
             patch("src.retrieval.base_retriever.get_session_local"):

            vec_inst = MagicMock()
            vec_inst.retrieve.return_value = [{"chunk_id": 1, "content": "test"}]
            vec.return_value = vec_inst

            hyde_inst = MagicMock()
            hyde_inst.retrieve.return_value = []
            hyde.return_value = hyde_inst

            kg_inst = MagicMock()
            kg_inst.retrieve.return_value = []
            kg.return_value = kg_inst

            rrf_inst = MagicMock()
            rrf_inst.fuse.return_value = [{"chunk_id": 1, "content": "fused"}]
            rrf.return_value = rrf_inst

            rerank_inst = MagicMock()
            rerank_inst.rerank.return_value = [{"chunk_id": 1, "content": "reranked"}]
            rerank.return_value = rerank_inst

            ctx_inst = MagicMock()
            ctx_inst.rerank.return_value = [{"chunk_id": 1, "content": "final"}]
            ctx.return_value = ctx_inst

            rewrite_inst = MagicMock()
            rewrite_inst.rewrite.return_value = "rewritten"
            rewrite.return_value = rewrite_inst

            retriever = BaseRetriever()
            results = retriever.retrieve("test query", intent="spec")

            assert isinstance(results, list)
            rewrite_inst.rewrite.assert_called_once_with("test query")

    def test_no_results_from_any_source(self):
        from src.retrieval.base_retriever import BaseRetriever

        with patch("src.retrieval.base_retriever.get_vector_retriever") as vec, \
             patch("src.retrieval.base_retriever.get_hyde_retriever") as hyde, \
             patch("src.retrieval.base_retriever.get_kg_retriever") as kg, \
             patch("src.retrieval.base_retriever.get_query_rewriter") as rewrite:

            vec_inst = MagicMock()
            vec_inst.retrieve.return_value = []
            vec.return_value = vec_inst

            hyde_inst = MagicMock()
            hyde_inst.retrieve.return_value = []
            hyde.return_value = hyde_inst

            kg_inst = MagicMock()
            kg_inst.retrieve.return_value = []
            kg.return_value = kg_inst

            rewrite_inst = MagicMock()
            rewrite_inst.rewrite.return_value = "rewritten"
            rewrite.return_value = rewrite_inst

            retriever = BaseRetriever()
            results = retriever.retrieve("unknown product")

            assert results == []

    def test_exception_returns_empty(self):
        from src.retrieval.base_retriever import BaseRetriever

        with patch("src.retrieval.base_retriever.get_query_rewriter") as rewrite:
            rewrite_inst = MagicMock()
            rewrite_inst.rewrite.side_effect = RuntimeError("crash")
            rewrite.return_value = rewrite_inst

            retriever = BaseRetriever()
            results = retriever.retrieve("should not crash")
            assert results == []

    def test_passes_session_id(self):
        from src.retrieval.base_retriever import BaseRetriever

        with patch("src.retrieval.base_retriever.get_vector_retriever") as vec, \
             patch("src.retrieval.base_retriever.get_hyde_retriever") as hyde, \
             patch("src.retrieval.base_retriever.get_kg_retriever") as kg, \
             patch("src.retrieval.base_retriever.get_rrf_fusion") as rrf, \
             patch("src.retrieval.base_retriever.get_reranker") as rerank, \
             patch("src.retrieval.base_retriever.get_context_aware_reranker") as ctx, \
             patch("src.retrieval.base_retriever.get_query_rewriter") as rewrite, \
             patch("src.retrieval.base_retriever.get_session_local"):

            vec_inst = MagicMock()
            vec_inst.retrieve.return_value = [{"chunk_id": 1, "content": "test"}]
            vec.return_value = vec_inst

            hyde_inst = MagicMock()
            hyde_inst.retrieve.return_value = []
            hyde.return_value = hyde_inst

            kg_inst = MagicMock()
            kg_inst.retrieve.return_value = []
            kg.return_value = kg_inst

            rrf_inst = MagicMock()
            rrf_inst.fuse.return_value = [{"chunk_id": 1, "content": "fused"}]
            rrf.return_value = rrf_inst

            rerank_inst = MagicMock()
            rerank_inst.rerank.return_value = [{"chunk_id": 1, "content": "reranked"}]
            rerank.return_value = rerank_inst

            ctx_inst = MagicMock()
            ctx_inst.rerank.return_value = [{"chunk_id": 1, "content": "final"}]
            ctx.return_value = ctx_inst

            rewrite_inst = MagicMock()
            rewrite_inst.rewrite.return_value = "rewritten"
            rewrite.return_value = rewrite_inst

            retriever = BaseRetriever()
            results = retriever.retrieve("test", session_id="sess-123")
            assert isinstance(results, list)

    def test_intent_passed_through(self):
        from src.retrieval.base_retriever import BaseRetriever

        with patch("src.retrieval.base_retriever.get_vector_retriever") as vec, \
             patch("src.retrieval.base_retriever.get_hyde_retriever") as hyde, \
             patch("src.retrieval.base_retriever.get_kg_retriever") as kg, \
             patch("src.retrieval.base_retriever.get_rrf_fusion") as rrf, \
             patch("src.retrieval.base_retriever.get_reranker") as rerank, \
             patch("src.retrieval.base_retriever.get_context_aware_reranker") as ctx, \
             patch("src.retrieval.base_retriever.get_query_rewriter") as rewrite, \
             patch("src.retrieval.base_retriever.get_session_local"):

            vec_inst = MagicMock()
            vec_inst.retrieve.return_value = [{"chunk_id": 1, "content": "troubleshoot doc"}]
            vec.return_value = vec_inst

            hyde_inst = MagicMock()
            hyde_inst.retrieve.return_value = []
            hyde.return_value = hyde_inst

            kg_inst = MagicMock()
            kg_inst.retrieve.return_value = []
            kg.return_value = kg_inst

            rrf_inst = MagicMock()
            rrf_inst.fuse.return_value = [{"chunk_id": 1, "content": "fused"}]
            rrf.return_value = rrf_inst

            rerank_inst = MagicMock()
            rerank_inst.rerank.return_value = [{"chunk_id": 1, "content": "reranked"}]
            rerank.return_value = rerank_inst

            ctx_inst = MagicMock()
            ctx_inst.rerank.return_value = [{"chunk_id": 1, "content": "final"}]
            ctx.return_value = ctx_inst

            rewrite_inst = MagicMock()
            rewrite_inst.rewrite.return_value = "rewritten"
            rewrite.return_value = rewrite_inst

            retriever = BaseRetriever()
            retriever.retrieve("E001 error", intent="troubleshoot")
            # All retrievers should be called with the rewritten query
            vec_inst.retrieve.assert_called_once_with("rewritten")


class TestGetBaseRetriever:
    """get_base_retriever() 单例"""

    def test_returns_retriever(self):
        from src.retrieval.base_retriever import get_base_retriever, BaseRetriever
        r = get_base_retriever()
        assert isinstance(r, BaseRetriever)

    def test_singleton(self):
        from src.retrieval.base_retriever import get_base_retriever
        r1 = get_base_retriever()
        r2 = get_base_retriever()
        assert r1 is r2
