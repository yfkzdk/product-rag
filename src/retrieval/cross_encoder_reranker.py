from typing import List, Dict, Optional
from src.config import get_settings
import socket
import logging

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Cross-Encoder重排器"""

    def __init__(self):
        """初始化（延迟加载模型）"""
        self._model = None
        self._initialized = False
        self._model_load_failed = False

    def _ensure_model(self):
        """确保模型已加载"""
        if self._initialized:
            return
        if self._model_load_failed:
            return

        settings = get_settings()

        # Skip model loading in demo mode or when BGE is disabled
        if settings.DEMO_MODE or settings.SKIP_BGE_MODEL or settings.BGE_SUBPROCESS:
            self._model_load_failed = True
            self._initialized = True
            logger.info("Reranker skipped (demo/BGE-skip/subprocess mode), using pass-through")
            return

        import os

        # Strategy 1: Try local cache first
        saved_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(3.0)
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(
                settings.RERANKER_MODEL_NAME,
                device="cpu",
                local_files_only=True
            )
            self._initialized = True
            logger.info(f"Reranker model loaded from cache: {settings.RERANKER_MODEL_NAME}")
            return
        except Exception:
            logger.debug("Reranker cache miss, trying download via HF endpoint")
        finally:
            socket.setdefaulttimeout(saved_timeout)

        # Strategy 2: Download via configured HF endpoint (default: hf-mirror.com)
        try:
            socket.setdefaulttimeout(30.0)
            os.environ["HF_ENDPOINT"] = settings.HF_ENDPOINT
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(
                settings.RERANKER_MODEL_NAME,
                device="cpu",
            )
            self._initialized = True
            logger.info(f"Reranker model downloaded via {settings.HF_ENDPOINT}: {settings.RERANKER_MODEL_NAME}")
            return
        except Exception:
            logger.debug("Download via HF endpoint failed, trying offline fallback")
        finally:
            socket.setdefaulttimeout(saved_timeout)

        # Strategy 3: Offline fallback
        try:
            socket.setdefaulttimeout(3.0)
            os.environ["HF_HUB_OFFLINE"] = "1"
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(
                settings.RERANKER_MODEL_NAME,
                device="cpu",
                local_files_only=True
            )
            self._initialized = True
            logger.info(f"Reranker model loaded (offline): {settings.RERANKER_MODEL_NAME}")
            return
        except Exception as e:
            self._model_load_failed = True
            self._initialized = True
            logger.warning(f"Reranker model unavailable, skipping rerank step: {e}")
        finally:
            socket.setdefaulttimeout(saved_timeout)

    def rerank(self, query: str, documents: List[Dict], top_k: Optional[int] = None) -> List[Dict]:
        """重排文档"""
        if not documents:
            return []

        self._ensure_model()
        settings = get_settings()
        effective_top_k = top_k or settings.RERANK_TOP_K

        if self._model is None:
            # Graceful degradation: return documents as-is (already sorted by RRF)
            logger.debug("Reranker unavailable, passing through documents unsorted")
            return documents[:effective_top_k]

        try:
            # 构建query-document对
            pairs = []
            for doc in documents:
                content = doc.get("content", "")
                if not content:
                    content = str(doc)
                pairs.append([query, content])

            # Cross-Encoder打分
            scores = self._model.predict(pairs)

            # 按分数排序
            scored_docs = list(zip(documents, scores))
            scored_docs.sort(key=lambda x: x[1], reverse=True)

            # 返回top_k结果
            results = []
            for doc, score in scored_docs[:effective_top_k]:
                result = dict(doc)
                result["rerank_score"] = float(score)
                results.append(result)

            logger.info(f"重排完成: input={len(documents)}, output={len(results)}")
            return results

        except Exception as e:
            logger.warning(f"重排失败, passing through: {e}")
            return documents[:effective_top_k]


# Lazy singleton accessor
_reranker: Optional[CrossEncoderReranker] = None


def get_reranker() -> CrossEncoderReranker:
    """获取重排器（延迟初始化）"""
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoderReranker()
    return _reranker