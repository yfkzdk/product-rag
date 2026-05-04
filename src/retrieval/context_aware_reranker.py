from typing import List, Dict, Optional
from src.config import get_settings
import logging

logger = logging.getLogger(__name__)


class ContextAwareReranker:
    """上下文感知重排器"""

    def __init__(self):
        """初始化"""
        pass

    def rerank(
        self,
        query_or_results,
        documents_or_query=None,
        conversation_context=None,
        top_k=None
    ) -> List[Dict]:
        """上下文感知重排

        支持两种调用方式:
        1. rerank(results, query, entities, intent) — test兼容模式
        2. rerank(query, documents, conversation_context, top_k) — 标准模式
        """
        # 检测调用模式：如果第一个参数是list，则是test兼容模式
        if isinstance(query_or_results, list):
            return self._rerank_test_mode(
                results=query_or_results,
                query=documents_or_query,
                entities=conversation_context,
                intent=top_k
            )
        else:
            return self._rerank_standard(
                query=query_or_results,
                documents=documents_or_query,
                conversation_context=conversation_context,
                top_k=top_k
            )

    def _rerank_standard(
        self,
        query: str,
        documents: List[Dict],
        conversation_context: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> List[Dict]:
        """标准重排模式"""
        settings = get_settings()
        effective_top_k = top_k or settings.RERANK_TOP_K

        if not documents:
            return []

        try:
            enhanced_query = query
            if conversation_context:
                enhanced_query = f"{conversation_context}\n当前问题：{query}"

            scored_docs = []
            query_terms = set(enhanced_query.lower().split())

            for doc in documents:
                content = doc.get("content", "").lower()
                content_terms = set(content.split())
                overlap = len(query_terms & content_terms)
                total = len(query_terms) if query_terms else 1
                score = overlap / total if total > 0 else 0.0

                original_score = doc.get("rerank_score", doc.get("score", doc.get("rrf_score", 0.0)))
                combined_score = 0.7 * original_score + 0.3 * score

                result = dict(doc)
                result["context_aware_score"] = combined_score
                scored_docs.append((result, combined_score))

            scored_docs.sort(key=lambda x: x[1], reverse=True)
            results = [doc for doc, _ in scored_docs[:effective_top_k]]
            logger.info(f"上下文感知重排完成: input={len(documents)}, output={len(results)}")
            return results

        except Exception as e:
            logger.error(f"上下文感知重排失败: {e}")
            return documents[:effective_top_k]

    def _rerank_test_mode(
        self,
        results: List[Dict],
        query: str,
        entities: Optional[Dict] = None,
        intent: Optional[str] = None
    ) -> List[Dict]:
        """Test兼容重排模式"""
        if not results:
            return results

        for result in results:
            context_score = 0.0
            content = result.get("content", "")

            if entities:
                for product in entities.get("products", []):
                    if product in content:
                        context_score += 0.3

                for fault in entities.get("faults", []):
                    if fault in content:
                        context_score += 0.3

            query_terms = set(query.lower().split()) if query else set()
            content_terms = set(content.lower().split())
            query_overlap = len(query_terms & content_terms) / max(len(query_terms), 1)
            context_score += query_overlap * 0.4

            original_score = result.get("score", 0.5)
            result["final_score"] = original_score * 0.7 + context_score * 0.3

        reranked = sorted(results, key=lambda x: x.get("final_score", 0), reverse=True)
        return reranked


# Lazy singleton accessor
_context_reranker: Optional[ContextAwareReranker] = None


def get_context_aware_reranker() -> ContextAwareReranker:
    """获取上下文感知重排器（延迟初始化）"""
    global _context_reranker
    if _context_reranker is None:
        _context_reranker = ContextAwareReranker()
    return _context_reranker