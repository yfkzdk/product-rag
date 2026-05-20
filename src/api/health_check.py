from fastapi import APIRouter
from src.storage.postgres.database import get_engine
from src.cache.query_cache import get_cache
from src.config import get_settings
from typing import Dict, Callable, Optional
import logging
import time

logger = logging.getLogger(__name__)

router = APIRouter()

# 跟踪启动时间和总查询数
_start_time = time.time()
_query_count = 0
_total_latency_ms = 0.0
_last_faithfulness = 0.0


def _record_query_stats(latency_ms: float, faithfulness: float = 0.0):
    """记录查询统计（由 pipeline_tracer 调用）"""
    global _query_count, _total_latency_ms, _last_faithfulness
    _query_count += 1
    _total_latency_ms += latency_ms
    _last_faithfulness = faithfulness


class HealthChecker:
    """健康检查器（用于单元测试和手动检查）"""

    def __init__(self):
        self._checks: Dict[str, Callable[[], bool]] = {}

    def register_check(self, name: str, check_fn: Callable[[], bool]) -> None:
        self._checks[name] = check_fn

    def run_check(self, name: str) -> Dict:
        if name not in self._checks:
            return {"status": "unknown", "error": f"check '{name}' not found"}
        try:
            result = self._checks[name]()
            return {"status": "healthy" if result else "unhealthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def run_all_checks(self) -> Dict:
        results = {}
        for name in self._checks:
            results[name] = self.run_check(name)
        all_healthy = all(r["status"] == "healthy" for r in results.values()) if results else True
        return {"overall_status": "healthy" if all_healthy else "unhealthy", "checks": results}


@router.get("/health")
async def health_check():
    """健康检查"""
    settings = get_settings()
    status = {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "services": {}
    }

    # PostgreSQL
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        status["services"]["postgres"] = "healthy"
    except Exception as e:
        status["services"]["postgres"] = f"unhealthy: {str(e)}"
        status["status"] = "degraded"

    # Milvus
    try:
        from src.storage.milvus.client import get_milvus_client

        milvus = get_milvus_client()
        stats = milvus.get_stats()
        status["services"]["milvus"] = "healthy"
        status["services"]["milvus_stats"] = stats
    except Exception as e:
        status["services"]["milvus"] = f"unhealthy: {str(e)}"
        status["status"] = "degraded"

    # Redis
    try:
        cache = get_cache()
        if cache.is_available:
            status["services"]["redis"] = "healthy"
        else:
            status["services"]["redis"] = "not_configured"
    except Exception as e:
        status["services"]["redis"] = f"unhealthy: {str(e)}"
        status["status"] = "degraded"

    # Neo4j
    try:
        from src.storage.neo4j.client import get_kg_client

        kg = get_kg_client()
        if kg.is_available:
            status["services"]["neo4j"] = "healthy"
        else:
            status["services"]["neo4j"] = "not_configured"
    except Exception as e:
        status["services"]["neo4j"] = f"unhealthy: {str(e)}"

    return status


@router.get("/metrics")
async def metrics():
    """RAG 系统指标（Prometheus 兼容 + 自定义）"""
    uptime = time.time() - _start_time

    # 检查告警
    alerts = []
    try:
        from src.observability.alerting import alerting_system
        avg_latency = (_total_latency_ms / _query_count / 1000) if _query_count > 0 else 0
        result = alerting_system.check_alerts({
            "faithfulness": _last_faithfulness if _last_faithfulness > 0 else 0.9,
            "latency": avg_latency,
        })
        alerts = result
    except Exception:
        logger.debug("Alert check skipped (alerting system unavailable)")

    # 缓存统计
    cache_stats = {}
    try:
        from src.observability.metrics import metrics_collector
        cache_stats = {
            "hits": metrics_collector._cache_hits,
            "misses": metrics_collector._cache_misses,
            "hit_rate": round(metrics_collector.cache_hit_rate, 3),
        }
    except Exception:
        cache_stats = {"error": "metrics unavailable"}

    return {
        "uptime_seconds": round(uptime, 1),
        "total_queries": _query_count,
        "avg_latency_ms": round(_total_latency_ms / _query_count, 1) if _query_count > 0 else 0,
        "last_faithfulness": round(_last_faithfulness, 2),
        "cache": cache_stats,
        "alerts": alerts,
        "pipelines": {
            "intent_classification": "keyword_fallback",
            "retrieval": "hyde_mock + vector(degraded) + kg(degraded)",
            "reranker": "passthrough (model not cached)",
            "generation": "rule_based",
            "embeddings": "hash_fallback",
        },
    }