"""
Prometheus指标

RAG系统性能指标收集
"""
from typing import Dict
import logging
import time

logger = logging.getLogger(__name__)


class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        """初始化指标收集器"""
        self.metrics = {}
        self.counters = {}
        self.histograms = {}

        # 内置计数器（不依赖Prometheus）
        self._cache_hits = 0
        self._cache_misses = 0
        self._query_total = 0

        # 尝试导入Prometheus客户端
        try:
            from prometheus_client import Counter, Histogram, Gauge

            self.query_counter = Counter(
                'rag_queries_total',
                'Total number of RAG queries'
            )

            self.latency_histogram = Histogram(
                'rag_query_latency_seconds',
                'Query latency in seconds'
            )

            self.faithfulness_gauge = Gauge(
                'rag_faithfulness_score',
                'Faithfulness score'
            )

            self.context_precision_gauge = Gauge(
                'rag_context_precision_score',
                'Context precision score'
            )

            self.cache_hit_counter = Counter(
                'rag_cache_hits_total',
                'Total cache hits'
            )

            self.cache_miss_counter = Counter(
                'rag_cache_misses_total',
                'Total cache misses'
            )

            self.metrics_available = True
            logger.info("Prometheus metrics initialized")
        except Exception as e:
            self.metrics_available = False
            logger.warning(f"Prometheus not available: {e}")

    def record_query(self):
        """记录查询次数"""
        self._query_total += 1
        if self.metrics_available:
            try:
                self.query_counter.inc()
            except Exception as e:
                logger.error(f"Failed to record query: {e}")

    def record_latency(self, latency: float):
        """
        记录延迟

        Args:
            latency: 延迟时间（秒）
        """
        if self.metrics_available:
            try:
                self.latency_histogram.observe(latency)
            except Exception as e:
                logger.error(f"Failed to record latency: {e}")

    def record_faithfulness(self, score: float):
        """
        记录忠实度分数

        Args:
            score: 忠实度分数
        """
        if self.metrics_available:
            try:
                self.faithfulness_gauge.set(score)
            except Exception as e:
                logger.error(f"Failed to record faithfulness: {e}")

    def record_context_precision(self, score: float):
        """
        记录上下文精确度分数

        Args:
            score: 上下文精确度分数
        """
        if self.metrics_available:
            try:
                self.context_precision_gauge.set(score)
            except Exception as e:
                logger.error(f"Failed to record context precision: {e}")

    def record_cache_hit(self):
        """记录缓存命中"""
        self._cache_hits += 1
        if self.metrics_available:
            try:
                self.cache_hit_counter.inc()
            except Exception as e:
                logger.error(f"Failed to record cache hit: {e}")

    def record_cache_miss(self):
        """记录缓存未命中"""
        self._cache_misses += 1
        if self.metrics_available:
            try:
                self.cache_miss_counter.inc()
            except Exception as e:
                logger.error(f"Failed to record cache miss: {e}")

    @property
    def cache_hit_rate(self) -> float:
        """缓存命中率"""
        total = self._cache_hits + self._cache_misses
        if total == 0:
            return 0.0
        return self._cache_hits / total

    def get_metrics(self) -> Dict:
        """
        获取指标

        Returns:
            指标字典
        """
        return {
            "total_queries": self._query_total,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": round(self.cache_hit_rate, 3),
            "metrics_available": self.metrics_available,
        }


# 全局实例
metrics_collector = MetricsCollector()
