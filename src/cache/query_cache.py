import redis
import json
import logging
import hashlib
from collections import OrderedDict
from src.config import get_settings
from typing import Optional, Any

logger = logging.getLogger(__name__)

_LRU_MAX_ITEMS = 100


class QueryCache:
    """Redis查询缓存（Redis不可用时降级为内存LRU）"""

    def __init__(self):
        """初始化（延迟连接）"""
        self._client = None
        self._ttl = None
        self._initialized = False
        self._lru: OrderedDict = OrderedDict()

    @staticmethod
    def _record_hit():
        try:
            from src.observability.metrics import metrics_collector
            metrics_collector.record_cache_hit()
        except Exception:
            pass

    @staticmethod
    def _record_miss():
        try:
            from src.observability.metrics import metrics_collector
            metrics_collector.record_cache_miss()
        except Exception:
            pass

    def _ensure_connection(self):
        """确保连接已建立"""
        if self._initialized:
            return

        settings = get_settings()
        self._ttl = settings.CACHE_TTL

        # Demo 模式跳过 Redis 连接尝试（避免 4s 超时）
        if settings.DEMO_MODE:
            logger.info("Demo mode: using in-memory LRU cache")
            self._client = None
            self._initialized = True
            return

        try:
            self._client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            self._client.ping()
            self._initialized = True
            logger.info(f"Redis connected: {settings.REDIS_URL}")
        except Exception as e:
            logger.warning(f"Redis unavailable, using in-memory LRU cache (max {_LRU_MAX_ITEMS} items)")
            self._client = None
            self._initialized = True

    @property
    def is_available(self) -> bool:
        """检查缓存是否可用（Redis或内存LRU均为可用）"""
        if not self._initialized:
            self._ensure_connection()
        return True

    def _normalize_key(self, key: str) -> str:
        """Normalize long keys via md5 to avoid memory bloat."""
        if len(key) <= 80:
            return key
        return hashlib.md5(key.encode()).hexdigest() + ":" + key[-40:]

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self._initialized:
            self._ensure_connection()

        if self._client is not None:
            try:
                value = self._client.get(key)
                if value:
                    self._record_hit()
                    return json.loads(value)
                self._record_miss()
                return None
            except Exception as e:
                logger.error(f"Redis get error for key '{key}': {e}")

        # LRU fallback
        nk = self._normalize_key(key)
        if nk in self._lru:
            self._lru.move_to_end(nk)
            self._record_hit()
            return json.loads(self._lru[nk])
        self._record_miss()
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        if not self._initialized:
            self._ensure_connection()

        serialized = json.dumps(value, ensure_ascii=False)

        if self._client is not None:
            try:
                effective_ttl = ttl or self._ttl
                self._client.setex(key, effective_ttl, serialized)
                return True
            except Exception as e:
                logger.error(f"Redis set error for key '{key}': {e}")

        # LRU fallback
        nk = self._normalize_key(key)
        self._lru[nk] = serialized
        self._lru.move_to_end(nk)
        if len(self._lru) > _LRU_MAX_ITEMS:
            self._lru.popitem(last=False)
        return True

    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.is_available:
            return False

        try:
            self._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key '{key}': {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的所有缓存"""
        if not self.is_available:
            return 0

        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear error for pattern '{pattern}': {e}")
            return 0


# Lazy singleton accessor
_cache_client: Optional[QueryCache] = None


def get_cache() -> QueryCache:
    """获取缓存客户端（延迟初始化）"""
    global _cache_client
    if _cache_client is None:
        _cache_client = QueryCache()
    return _cache_client