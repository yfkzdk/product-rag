from pymilvus import MilvusClient
from src.config import get_settings
from typing import List, Dict, Optional
import socket
import logging

logger = logging.getLogger(__name__)

_MILVUS_TIMEOUT = 3.0


class MilvusVectorStore:
    """Milvus向量存储客户端"""

    def __init__(self):
        """初始化Milvus客户端（延迟连接，实际连接在首次操作时建立）"""
        self._client = None
        self._collection_name = None
        self._initialized = False
        self._connection_failed = False

    def _ensure_connection(self):
        """确保连接已建立"""
        if self._initialized:
            return
        if self._connection_failed:
            return

        settings = get_settings()
        self._collection_name = settings.MILVUS_COLLECTION

        saved_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(_MILVUS_TIMEOUT)
        try:
            self._client = MilvusClient(
                uri=f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}",
                timeout=_MILVUS_TIMEOUT
            )
            self._ensure_collection()
            self._initialized = True
            logger.info(f"Milvus connected: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
        except Exception as e:
            self._connection_failed = True
            logger.warning(f"Milvus unavailable (offline mode): {e}")
        finally:
            socket.setdefaulttimeout(saved_timeout)

    def _ensure_collection(self):
        """确保集合存在"""
        settings = get_settings()
        try:
            if not self._client.has_collection(self._collection_name):
                self._client.create_collection(
                    collection_name=self._collection_name,
                    dimension=settings.EMBEDDING_DIMENSION,
                    metric_type=settings.MILVUS_METRIC_TYPE,
                    auto_id=True
                )
                logger.info(f"Created Milvus collection: {self._collection_name}")
            else:
                logger.info(f"Milvus collection already exists: {self._collection_name}")
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")
            raise

    def insert_vectors(
        self,
        vectors: List[List[float]],
        metadata: List[Dict]
    ) -> List[int]:
        """插入向量"""
        self._ensure_connection()

        try:
            data = []
            for i, (vector, meta) in enumerate(zip(vectors, metadata)):
                data.append({
                    "vector": vector,
                    "product_id": meta.get("product_id"),
                    "chunk_id": meta.get("chunk_id"),
                    "chunk_type": meta.get("chunk_type"),
                    "content": meta.get("content", "")
                })

            result = self._client.insert(
                collection_name=self._collection_name,
                data=data
            )

            logger.info(f"Inserted {len(result['ids'])} vectors")
            return result['ids']

        except Exception as e:
            logger.error(f"Failed to insert vectors: {e}")
            raise

    def search_vectors(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[str] = None
    ) -> List[Dict]:
        """搜索向量"""
        self._ensure_connection()

        if self._client is None:
            return []

        try:
            settings = get_settings()
            search_params = {
                "metric_type": settings.MILVUS_METRIC_TYPE,
                "params": {"nprobe": 10}
            }

            results = self._client.search(
                collection_name=self._collection_name,
                data=[query_vector],
                search_params=search_params,
                limit=top_k,
                filter=filters,
                output_fields=["product_id", "chunk_id", "chunk_type", "content"]
            )

            # MilvusClient returns list of lists of dicts
            formatted_results = []
            for hits in results:
                for hit in hits:
                    formatted_results.append({
                        "id": hit.get("id"),
                        "distance": hit.get("distance", 0.0),
                        "score": 1 - hit.get("distance", 0.0),
                        "product_id": hit.get("entity", {}).get("product_id"),
                        "chunk_id": hit.get("entity", {}).get("chunk_id"),
                        "chunk_type": hit.get("entity", {}).get("chunk_type"),
                        "content": hit.get("entity", {}).get("content", "")
                    })

            logger.info(f"Found {len(formatted_results)} results")
            return formatted_results

        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            raise

    def delete_by_product_id(self, product_id: int):
        """删除指定产品的向量"""
        self._ensure_connection()

        try:
            self._client.delete(
                collection_name=self._collection_name,
                filter=f"product_id == {product_id}"
            )
            logger.info(f"Deleted vectors for product_id={product_id}")

        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            raise

    def get_stats(self) -> Dict:
        """获取统计信息"""
        if not self._initialized:
            return {"row_count": 0, "collection_name": "not_connected"}

        try:
            stats = self._client.get_collection_stats(self._collection_name)
            return {
                "row_count": stats.get("row_count", 0),
                "collection_name": self._collection_name
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}


# Lazy singleton accessor
_milvus_client: Optional[MilvusVectorStore] = None


def get_milvus_client() -> MilvusVectorStore:
    """获取Milvus客户端（延迟初始化）"""
    global _milvus_client
    if _milvus_client is None:
        _milvus_client = MilvusVectorStore()
    return _milvus_client