"""
本地向量存储 — Demo 模式下替代 Milvus 的轻量级方案

设计意图：
- 零外部依赖（numpy + pickle，已在 requirements 中）
- 支持余弦相似度检索
- 持久化到磁盘（data/local_vectors.npz）
- 数据为空时返回空列表（优雅降级）
"""
from __future__ import annotations
import os
import pickle
import logging
from typing import List, Dict, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

# 向量数据文件路径
_VECTORS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "local_vectors.npz")
_META_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "local_vectors_meta.pkl")


class LocalVectorStore:
    """基于 numpy 的本地向量存储"""

    def __init__(self):
        self._vectors: Optional[np.ndarray] = None       # shape: (N, dim)
        self._metadata: List[Dict] = []                   # 每行向量对应的元数据
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        self._loaded = True

        if not os.path.exists(_VECTORS_PATH):
            logger.debug(f"Local vector store not found at {_VECTORS_PATH}, returning empty")
            return

        try:
            data = np.load(_VECTORS_PATH)
            self._vectors = data["vectors"]
            if os.path.exists(_META_PATH):
                with open(_META_PATH, "rb") as f:
                    self._metadata = pickle.load(f)
            logger.info(f"Loaded {len(self._vectors)} vectors (dim={self._vectors.shape[1]})")
        except Exception as e:
            logger.warning(f"Failed to load local vectors: {e}")
            self._vectors = None
            self._metadata = []

    @property
    def is_available(self) -> bool:
        self._ensure_loaded()
        return self._vectors is not None and len(self._vectors) > 0

    @property
    def count(self) -> int:
        self._ensure_loaded()
        return len(self._vectors) if self._vectors is not None else 0

    def save(self, vectors: np.ndarray, metadata: List[Dict]):
        """保存向量和元数据到磁盘"""
        os.makedirs(os.path.dirname(_VECTORS_PATH), exist_ok=True)
        np.savez_compressed(_VECTORS_PATH, vectors=vectors)
        with open(_META_PATH, "wb") as f:
            pickle.dump(metadata, f)
        self._vectors = vectors
        self._metadata = metadata
        self._loaded = True
        logger.info(f"Saved {len(vectors)} vectors to {_VECTORS_PATH}")

    def search(self, query_vector: List[float], top_k: int = 5) -> List[Dict]:
        """余弦相似度检索，返回 top_k 结果"""
        self._ensure_loaded()
        if self._vectors is None or len(self._vectors) == 0:
            return []

        query = np.array(query_vector, dtype=np.float32)
        # 归一化
        q_norm = np.linalg.norm(query)
        if q_norm > 0:
            query = query / q_norm

        # 批量计算余弦相似度（向量已预归一化存储）
        v_norms = np.linalg.norm(self._vectors, axis=1, keepdims=True)
        v_norms[v_norms == 0] = 1.0
        v_normalized = self._vectors / v_norms
        similarities = np.dot(v_normalized, query)

        # Top-K
        if top_k >= len(similarities):
            top_indices = list(range(len(similarities)))
        else:
            top_indices = np.argpartition(-similarities, top_k)[:top_k]
        top_indices = sorted(top_indices, key=lambda i: float(similarities[i]), reverse=True)

        results = []
        for idx in top_indices[:top_k]:
            meta = self._metadata[idx].copy() if idx < len(self._metadata) else {}
            meta["score"] = float(similarities[idx])
            meta["content"] = meta.get("content", "")
            results.append(meta)

        return results


# 全局单例
_local_store: Optional[LocalVectorStore] = None


def get_local_vector_store() -> LocalVectorStore:
    global _local_store
    if _local_store is None:
        _local_store = LocalVectorStore()
    return _local_store
