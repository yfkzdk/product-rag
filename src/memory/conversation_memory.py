"""
上下文记忆模块

基于LangChain的对话记忆管理
"""
from typing import List, Dict, Optional
from collections import deque
import logging

logger = logging.getLogger(__name__)


class MemoryBlock:
    """记忆块"""

    def __init__(self, content: str, memory_type: str = "query", metadata: Optional[Dict] = None):
        """
        初始化记忆块

        Args:
            content: 记忆内容
            memory_type: 记忆类型 (query, response, context, entity)
            metadata: 元数据
        """
        self.content = content
        self.memory_type = memory_type
        self.metadata = metadata or {}
        self.timestamp = self._get_timestamp()

    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "content": self.content,
            "memory_type": self.memory_type,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class ConversationMemory:
    """对话记忆管理器"""

    def __init__(self, max_memory_blocks: int = 20):
        """
        初始化对话记忆

        Args:
            max_memory_blocks: 最大记忆块数量
        """
        self.max_memory_blocks = max_memory_blocks
        self.memories = {}  # session_id -> deque of MemoryBlock
        logger.info(f"Conversation memory initialized: max_blocks={max_memory_blocks}")

    def add_memory(
        self,
        session_id: str,
        content: str,
        memory_type: str = "query",
        metadata: Optional[Dict] = None
    ) -> None:
        """
        添加记忆

        Args:
            session_id: 会话ID
            content: 记忆内容
            memory_type: 记忆类型
            metadata: 元数据
        """
        if session_id not in self.memories:
            self.memories[session_id] = deque(maxlen=self.max_memory_blocks)

        memory_block = MemoryBlock(content, memory_type, metadata)
        self.memories[session_id].append(memory_block)

        logger.info(f"Added memory: session_id={session_id}, type={memory_type}, content={content[:50]}...")

    def get_memories(
        self,
        session_id: str,
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        获取记忆

        Args:
            session_id: 会话ID
            memory_type: 记忆类型过滤
            limit: 返回数量限制

        Returns:
            记忆列表
        """
        if session_id not in self.memories:
            return []

        memories = list(self.memories[session_id])

        # 过滤类型
        if memory_type:
            memories = [m for m in memories if m.memory_type == memory_type]

        # 限制数量
        memories = memories[-limit:]

        return [m.to_dict() for m in memories]

    def get_recent_context(self, session_id: str, window_size: int = 3) -> str:
        """
        获取最近上下文

        Args:
            session_id: 会话ID
            window_size: 上下文窗口大小

        Returns:
            上下文字符串
        """
        memories = self.get_memories(session_id, limit=window_size * 2)

        if not memories:
            return ""

        context_parts = []
        for memory in memories:
            if memory["memory_type"] == "query":
                context_parts.append(f"用户: {memory['content']}")
            elif memory["memory_type"] == "response":
                context_parts.append(f"系统: {memory['content']}")

        context = "\n".join(context_parts)
        logger.info(f"Retrieved context: session_id={session_id}, window={window_size}, length={len(context)}")
        return context

    def extract_entities(self, session_id: str) -> Dict:
        """
        提取记忆中的实体

        Args:
            session_id: 会话ID

        Returns:
            实体字典
        """
        memories = self.get_memories(session_id)
        entities = {
            "products": set(),
            "faults": set(),
            "parameters": set()
        }

        import re
        for memory in memories:
            content = memory["content"]

            # 提取产品型号
            product_pattern = r'[A-Z]{3,5}-\d{3,5}'
            products = re.findall(product_pattern, content)
            entities["products"].update(products)

            # 提取故障代码
            fault_pattern = r'E\d{3,5}'
            faults = re.findall(fault_pattern, content)
            entities["faults"].update(faults)

        # 转换为列表
        entities = {k: list(v) for k, v in entities.items()}

        logger.info(f"Extracted entities: session_id={session_id}, entities={entities}")
        return entities

    def summarize_memory(self, session_id: str) -> Dict:
        """
        总结记忆

        Args:
            session_id: 会话ID

        Returns:
            记忆总结
        """
        memories = self.get_memories(session_id)

        if not memories:
            return {"total_memories": 0}

        summary = {
            "total_memories": len(memories),
            "queries": len([m for m in memories if m["memory_type"] == "query"]),
            "responses": len([m for m in memories if m["memory_type"] == "response"]),
            "entities": self.extract_entities(session_id),
            "first_memory": memories[0]["timestamp"] if memories else None,
            "last_memory": memories[-1]["timestamp"] if memories else None
        }

        logger.info(f"Summarized memory: session_id={session_id}, total={summary['total_memories']}")
        return summary

    def clear_memory(self, session_id: str) -> None:
        """
        清除记忆

        Args:
            session_id: 会话ID
        """
        if session_id in self.memories:
            del self.memories[session_id]
            logger.info(f"Cleared memory: session_id={session_id}")


# 全局实例
conversation_memory = ConversationMemory()
