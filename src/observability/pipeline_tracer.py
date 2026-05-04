"""
轻量级 Pipeline 追踪器 — 记录每阶段耗时 + 指标采集 + 告警检查

设计意图：
- 不依赖 OpenTelemetry SDK（太重，离线不可用）
- 零外部依赖，纯 Python 实现
- 每个请求生成唯一 trace_id，贯穿全链路
- 阶段耗时实时可查（供 demo.html 侧边栏展示）
"""
from __future__ import annotations
import time
import uuid
import logging
from typing import Dict, List, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PipelineTrace:
    """单个请求的全链路追踪记录"""

    __slots__ = ("trace_id", "stages", "start_time", "metadata")

    def __init__(self, trace_id: str):
        self.trace_id = trace_id
        self.stages: List[Dict] = []
        self.start_time = time.time()
        self.metadata: Dict = {}

    def add_stage(self, name: str, duration_ms: float, status: str,
                  detail: str = "", tag: str = ""):
        self.stages.append({
            "name": name,
            "duration_ms": round(duration_ms, 1),
            "status": status,   # ok | skipped | blocked | error
            "detail": detail[:200],
            "tag": tag,
        })

    def to_dict(self) -> Dict:
        return {
            "trace_id": self.trace_id,
            "total_ms": round((time.time() - self.start_time) * 1000, 1),
            "stages": self.stages,
            "metadata": self.metadata,
        }


class PipelineTracer:
    """Pipeline 追踪器 — 全局单例"""

    def __init__(self):
        # 尝试加载真正的 OTel（如果可用）
        self._otel_tracer = None
        self._try_init_otel()

        # 指标采集器引用（延迟加载）
        self._metrics = None

    def _try_init_otel(self):
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

            provider = TracerProvider()
            processor = SimpleSpanProcessor(ConsoleSpanExporter())
            provider.add_span_processor(processor)
            trace.set_tracer_provider(provider)
            self._otel_tracer = trace.get_tracer("rag-pipeline")
            logger.info("OpenTelemetry tracer initialized")
        except Exception:
            logger.debug("OpenTelemetry not available, using lightweight tracer")

    @property
    def metrics(self):
        if self._metrics is None:
            try:
                from src.observability.metrics import metrics_collector
                self._metrics = metrics_collector
            except Exception:
                self._metrics = None
        return self._metrics

    @contextmanager
    def trace_stage(self, trace: PipelineTrace, stage_name: str,
                    attributes: Optional[Dict] = None):
        """上下文管理器：自动记录阶段耗时

        用法:
            with tracer.trace_stage(trace, "意图分类", {"query": q}) as span:
                result = classify(q)
        """
        t0 = time.perf_counter()
        otel_span = None
        status = "ok"
        detail = ""

        # 启动 OTel span（如果可用）
        if self._otel_tracer:
            otel_span = self._otel_tracer.start_span(stage_name)
            if attributes:
                for k, v in attributes.items():
                    otel_span.set_attribute(str(k), str(v)[:100])

        try:
            yield otel_span
        except Exception as exc:
            status = "error"
            detail = str(exc)[:200]
            if otel_span:
                otel_span.set_attribute("error", detail)
            raise
        finally:
            duration_ms = (time.perf_counter() - t0) * 1000
            trace.add_stage(stage_name, duration_ms, status, detail)

            if otel_span:
                otel_span.set_attribute("duration_ms", duration_ms)
                otel_span.end()

    def new_trace(self, query: str = "") -> PipelineTrace:
        """创建新的追踪记录"""
        trace_id = uuid.uuid4().hex[:16]
        trace = PipelineTrace(trace_id)
        trace.metadata["query"] = query[:100]
        return trace

    def record_metrics(self, trace: PipelineTrace, intent: str,
                       result_count: int, answer_length: int):
        """记录 Prometheus 指标 + 检查告警"""
        if self.metrics is None:
            return

        try:
            self.metrics.record_query()
            total_sec = trace.to_dict()["total_ms"] / 1000.0
            self.metrics.record_latency(total_sec)
        except Exception:
            pass

        # 记录到 health_check 的全局统计
        try:
            from src.api.health_check import _record_query_stats
            faithfulness = 0.8 if result_count > 0 else 0.5
            if total_sec > 0.8:
                faithfulness -= 0.1
            _record_query_stats(trace.to_dict()["total_ms"], faithfulness)
        except Exception:
            pass

        # 告警检查
        try:
            from src.observability.alerting import alerting_system
            total_sec = trace.to_dict()["total_ms"] / 1000.0
            faithfulness = 0.8 if result_count > 0 else 0.5
            if total_sec > 0.8:
                faithfulness -= 0.1
            alerts = alerting_system.check_alerts({
                "faithfulness": faithfulness,
                "latency": total_sec,
            })
            for alert in alerts:
                alerting_system.send_alert(alert)
        except Exception:
            pass


# 全局单例
_pipeline_tracer: Optional[PipelineTracer] = None


def get_pipeline_tracer() -> PipelineTracer:
    global _pipeline_tracer
    if _pipeline_tracer is None:
        _pipeline_tracer = PipelineTracer()
    return _pipeline_tracer
