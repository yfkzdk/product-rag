from typing import List, Dict, Optional
from src.config import get_settings
import logging

logger = logging.getLogger(__name__)


class RRFFusion:
    """RRF (Reciprocal Rank Fusion) 融合检索器"""

    def __init__(self):
        """初始化"""
        pass

    def fuse(self, result_lists: List[List[Dict]], k: Optional[int] = None) -> List[Dict]:
        """融合多个检索结果列表"""
        settings = get_settings()
        effective_k = k or settings.RRF_K

        if not result_lists:
            return []

        # 计算RRF分数
        rrf_scores: Dict[str, float] = {}
        doc_map: Dict[str, Dict] = {}

        for results in result_lists:
            for rank, doc in enumerate(results, start=1):
                # Use chunk_id or content as unique key
                doc_key = doc.get("chunk_id") or doc.get("content", "")[:100]
                if not doc_key:
                    continue

                rrf_scores[doc_key] = rrf_scores.get(doc_key, 0.0) + 1.0 / (effective_k + rank)
                doc_map[doc_key] = doc

        # 按RRF分数排序
        sorted_keys = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        results = []
        for key in sorted_keys:
            doc = dict(doc_map[key])
            doc["rrf_score"] = rrf_scores[key]
            results.append(doc)

        logger.info(f"RRF融合完成: input_lists={len(result_lists)}, output={len(results)}")
        return results


# Lazy singleton accessor
_rrf_fusion: Optional[RRFFusion] = None


def get_rrf_fusion() -> RRFFusion:
    """获取RRF融合器（延迟初始化）"""
    global _rrf_fusion
    if _rrf_fusion is None:
        _rrf_fusion = RRFFusion()
    return _rrf_fusion