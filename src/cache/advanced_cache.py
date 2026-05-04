"""
高级缓存优化策略

多级缓存和智能缓存预热
"""
from typing import Dict, Optional, List, Any
import time
import logging

logger = logging.getLogger(__name__)


class AdvancedCache:
    """高级缓存管理器"""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        初始化高级缓存

        Args:
            max_size: 最大缓存数量
            ttl: 缓存过期时间（秒）
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache = {}
        self.access_times = {}
        self.hit_count = 0
        self.miss_count = 0
        logger.info(f"Advanced cache initialized: max_size={max_size}, ttl={ttl}s")

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存

        Args:
            key: 缓存键

        Returns:
            缓存值
        """
        if key in self.cache:
            # 检查是否过期
            if time.time() - self.access_times[key] > self.ttl:
                del self.cache[key]
                del self.access_times[key]
                self.miss_count += 1
                logger.debug(f"Cache expired: {key}")
                return None

            self.hit_count += 1
            self.access_times[key] = time.time()
            logger.debug(f"Cache hit: {key}")
            return self.cache[key]

        self.miss_count += 1
        logger.debug(f"Cache miss: {key}")
        return None

    def set(self, key: str, value: any) -> None:
        """
        设置缓存

        Args:
            key: 缓存键
            value: 缓存值
        """
        # LRU淘汰
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.access_times, key=self.access_times.get)
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
            logger.debug(f"Cache evicted (LRU): {oldest_key}")

        self.cache[key] = value
        self.access_times[key] = time.time()
        logger.debug(f"Cache set: {key}")

    def warm_up(self, keys: List[str], loader) -> None:
        """
        缓存预热

        Args:
            keys: 需要预热的键列表
            loader: 数据加载函数
        """
        logger.info(f"Cache warm-up: {len(keys)} keys")
        for key in keys:
            if key not in self.cache:
                value = loader(key)
                if value:
                    self.set(key, value)

    def invalidate(self, key: str) -> None:
        """
        使缓存失效

        Args:
            key: 缓存键
        """
        if key in self.cache:
            del self.cache[key]
            del self.access_times[key]
            logger.debug(f"Cache invalidated: {key}")

    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self.access_times.clear()
        logger.info("Cache cleared")

    def get_stats(self) -> Dict:
        """
        获取缓存统计

        Returns:
            统计信息
        """
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total_requests if total_requests > 0 else 0.0

        return {
            "total_requests": total_requests,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": round(hit_rate, 3),
            "cache_size": len(self.cache),
            "max_size": self.max_size
        }


# 全局实例
advanced_cache = AdvancedCache()
