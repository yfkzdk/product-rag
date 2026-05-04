"""
OpenTelemetry追踪

分布式追踪和性能监控
"""
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class TracingManager:
    """追踪管理器"""

    def __init__(self, service_name: str = "product-kg-rag"):
        """初始化追踪管理器"""
        self.service_name = service_name
        self.tracer = None

        # 尝试导入OpenTelemetry
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

            # 配置追踪
            provider = TracerProvider()
            processor = SimpleSpanProcessor(ConsoleSpanExporter())
            provider.add_span_processor(processor)
            trace.set_tracer_provider(provider)

            self.tracer = trace.get_tracer(__name__)
            logger.info(f"OpenTelemetry initialized: {service_name}")
        except Exception as e:
            logger.warning(f"OpenTelemetry not available: {e}")

    def start_span(self, name: str, attributes: Optional[dict] = None):
        """
        开始追踪span

        Args:
            name: span名称
            attributes: 属性

        Returns:
            span对象
        """
        if not self.tracer:
            return None

        try:
            span = self.tracer.start_span(name)
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            return span
        except Exception as e:
            logger.error(f"Failed to start span: {e}")
            return None

    def record_event(self, span, name: str, attributes: Optional[dict] = None):
        """
        记录事件

        Args:
            span: span对象
            name: 事件名称
            attributes: 属性
        """
        if not span:
            return

        try:
            from opentelemetry.trace import Event
            span.add_event(name, attributes or {})
        except Exception as e:
            logger.error(f"Failed to record event: {e}")


# 全局实例
tracing_manager = TracingManager()
