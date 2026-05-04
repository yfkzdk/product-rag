import asyncio
from typing import AsyncIterator, Dict, Optional
from src.generation.response_generator import get_generator
from src.config import get_settings
import logging

logger = logging.getLogger(__name__)


class StreamingHandler:
    """流式响应处理器"""

    def __init__(self):
        """初始化"""
        pass

    async def stream_response(self, query: str, context: str, intent: str = "general") -> AsyncIterator[str]:
        """流式生成响应"""
        generator = get_generator()
        async for chunk in generator.generate_stream(query, context, intent):
            yield chunk

    async def stream_with_cache(self, query: str, context: str, intent: str = "general") -> AsyncIterator[str]:
        """带缓存的流式生成"""
        full_response = []

        async for chunk in self.stream_response(query, context, intent):
            full_response.append(chunk)
            yield chunk

        # Cache the complete response
        try:
            from src.cache.query_cache import get_cache
            cache = get_cache()
            if cache.is_available:
                cache.set(f"response:{intent}:{query}", "".join(full_response))
        except Exception as e:
            logger.error(f"Failed to cache streaming response: {e}")


# Lazy singleton accessor
_handler: Optional[StreamingHandler] = None


def get_streaming_handler() -> StreamingHandler:
    """获取流式处理器（延迟初始化）"""
    global _handler
    if _handler is None:
        _handler = StreamingHandler()
    return _handler