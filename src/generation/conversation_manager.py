from typing import Dict, List, Optional
from src.cache.query_cache import get_cache
import logging

logger = logging.getLogger(__name__)


class ConversationManager:
    """多轮对话管理器"""

    def __init__(self):
        """初始化"""
        pass

    def get_history(self, session_id: str) -> List[Dict]:
        """获取对话历史"""
        cache = get_cache()
        if not cache.is_available:
            return []

        history = cache.get(f"conversation:{session_id}")
        return history if isinstance(history, list) else []

    def add_message(self, session_id: str, role: str, content: str):
        """添加消息到对话历史"""
        cache = get_cache()
        if not cache.is_available:
            return

        history = self.get_history(session_id)
        history.append({"role": role, "content": content})

        # Keep last 20 messages
        if len(history) > 20:
            history = history[-20:]

        cache.set(f"conversation:{session_id}", history, ttl=7200)

    def build_context(self, session_id: str, current_query: str) -> str:
        """构建多轮对话上下文"""
        history = self.get_history(session_id)

        if not history:
            return current_query

        context_parts = []
        for msg in history[-6:]:  # Last 3 turns
            if msg["role"] == "user":
                context_parts.append(f"用户：{msg['content']}")
            else:
                context_parts.append(f"助手：{msg['content']}")

        context_parts.append(f"用户：{current_query}")
        return "\n".join(context_parts)

    def clear_history(self, session_id: str):
        """清除对话历史"""
        cache = get_cache()
        if cache.is_available:
            cache.delete(f"conversation:{session_id}")


# Lazy singleton accessor
_manager: Optional[ConversationManager] = None


def get_conversation_manager() -> ConversationManager:
    """获取对话管理器（延迟初始化）"""
    global _manager
    if _manager is None:
        _manager = ConversationManager()
    return _manager