from typing import List, Dict, Optional
from src.config import get_settings
import logging

logger = logging.getLogger(__name__)


class VectorRetriever:
    """向量检索器"""

    def __init__(self):
        """初始化"""
        pass

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Dict]:
        """向量检索（Demo 模式仅本地向量，零网络超时）"""
        from src.embeddings.bge_embedder import get_encoder

        settings = get_settings()
        effective_top_k = top_k or settings.RETRIEVAL_TOP_K
        results = []

        # Demo 模式：只查本地向量存储，跳过 Milvus 连接
        if settings.DEMO_MODE:
            try:
                from src.storage.local_vector_store import get_local_vector_store
                store = get_local_vector_store()
                if store.is_available:
                    encoder = get_encoder()
                    query_vector = encoder.encode_single(query)
                    results = store.search(query_vector, top_k=effective_top_k)
                    if results:
                        logger.info(f"Local vector retrieval: query={query[:30]}, results={len(results)}")
                        return results
            except Exception as e:
                logger.debug(f"Local vector retrieval unavailable: {e}")
            return results  # Demo 模式不降级到 Milvus

        # 1. 尝试 Milvus
        try:
            from src.storage.milvus.client import get_milvus_client

            encoder = get_encoder()
            milvus = get_milvus_client()

            query_vector = encoder.encode_single(query)
            results = milvus.search_vectors(
                query_vector=query_vector,
                top_k=effective_top_k
            )
            if results:
                logger.info(f"Milvus retrieval: query={query[:30]}, results={len(results)}")
                return results
        except Exception as e:
            logger.debug(f"Milvus retrieval unavailable: {e}")

        # 2. 降级到本地向量存储（非 Demo 模式 Milvus 失败时）
        if not settings.DEMO_MODE:
            try:
                from src.storage.local_vector_store import get_local_vector_store
                store = get_local_vector_store()
                if store.is_available:
                    encoder = get_encoder()
                    query_vector = encoder.encode_single(query)
                    results = store.search(query_vector, top_k=effective_top_k)
                    if results:
                        logger.info(f"Local vector retrieval (fallback): query={query[:30]}, results={len(results)}")
                        return results
            except Exception as e:
                logger.debug(f"Local vector retrieval unavailable: {e}")

        return results


# Lazy singleton accessor
_vector_retriever: Optional[VectorRetriever] = None


def get_vector_retriever() -> VectorRetriever:
    """获取向量检索器（延迟初始化）"""
    global _vector_retriever
    if _vector_retriever is None:
        _vector_retriever = VectorRetriever()
    return _vector_retriever