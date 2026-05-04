from typing import List, Dict, Optional
from src.retrieval.vector_retriever import get_vector_retriever
from src.retrieval.hyde_retriever import get_hyde_retriever
from src.retrieval.kg_retriever import get_kg_retriever
from src.retrieval.cross_encoder_reranker import get_reranker
from src.retrieval.context_aware_reranker import get_context_aware_reranker
from src.retrieval.rrf_fusion import get_rrf_fusion
from src.retrieval.query_rewriter import get_query_rewriter
from src.storage.postgres.database import get_session_local
from src.storage.postgres.models import ManualChunk
from src.config import get_settings
import logging

logger = logging.getLogger(__name__)


class BaseRetriever:
    """统一检索器 - 编排多种检索策略"""

    def __init__(self):
        """初始化"""
        pass

    def retrieve(self, query: str, intent: str = "general", session_id: Optional[str] = None) -> List[Dict]:
        """执行多路检索 + 融合 + 重排"""
        settings = get_settings()

        try:
            # 1. 查询改写
            rewriter = get_query_rewriter()
            rewritten_query = rewriter.rewrite(query)

            # 2. 多路检索
            retrieval_results = []

            # 2a. 向量检索
            vector_retriever = get_vector_retriever()
            vector_results = vector_retriever.retrieve(rewritten_query)
            if vector_results:
                retrieval_results.append(vector_results)

            # 2b. HyDE检索（所有意图均启用 — 离线模式下Mock文档是主要数据源）
            hyde_retriever = get_hyde_retriever()
            hyde_results = hyde_retriever.retrieve(rewritten_query)
            if hyde_results:
                retrieval_results.append(hyde_results)

            # 2c. 知识图谱检索
            kg_retriever = get_kg_retriever()
            kg_results = kg_retriever.retrieve(rewritten_query)
            if kg_results:
                retrieval_results.append(kg_results)

            if not retrieval_results:
                logger.info("No retrieval results from any source")
                return []

            # 3. RRF融合
            rrf = get_rrf_fusion()
            fused = rrf.fuse(retrieval_results)

            # 4. Cross-Encoder重排
            reranker = get_reranker()
            reranked = reranker.rerank(rewritten_query, fused)

            # 5. 上下文感知重排
            context_reranker = get_context_aware_reranker()
            conversation_context = None
            if session_id:
                try:
                    from src.generation.conversation_manager import get_conversation_manager
                    cm = get_conversation_manager()
                    history = cm.get_history(session_id)
                    if history:
                        conversation_context = " ".join(m["content"] for m in history[-4:])
                except Exception:
                    pass

            final = context_reranker.rerank(rewritten_query, reranked, conversation_context)

            # 6. 补充PostgreSQL中的chunk详情
            final = self._enrich_with_chunk_details(final)

            logger.info(f"检索完成: query={query[:30]}, results={len(final)}")
            return final

        except Exception as e:
            logger.error(f"检索失败: {e}")
            return []

    def _enrich_with_chunk_details(self, results: List[Dict]) -> List[Dict]:
        """用PostgreSQL中的chunk详情补充检索结果"""
        if not results:
            return results

        try:
            SessionLocal = get_session_local()
            session = SessionLocal()
            try:
                for result in results:
                    chunk_id = result.get("chunk_id")
                    if chunk_id:
                        chunk = session.query(ManualChunk).filter(ManualChunk.id == chunk_id).first()
                        if chunk:
                            result["chunk_type"] = chunk.chunk_type
                            result["section_title"] = chunk.section_title
                            result["chunk_metadata"] = chunk.chunk_metadata
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Failed to enrich chunk details: {e}")

        return results


# Lazy singleton accessor
_base_retriever: Optional[BaseRetriever] = None


def get_base_retriever() -> BaseRetriever:
    """获取统一检索器（延迟初始化）"""
    global _base_retriever
    if _base_retriever is None:
        _base_retriever = BaseRetriever()
    return _base_retriever