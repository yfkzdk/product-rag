"""
多轮对话管理器

基于LangChain的对话流程管理
"""
from typing import List, Dict, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DialogueState(Enum):
    """对话状态"""
    INITIAL = "initial"
    CLARIFYING = "clarifying"
    RETRIEVING = "retrieving"
    ANSWERING = "answering"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversationManager:
    """多轮对话管理器"""

    def __init__(self, max_turns: int = 10):
        """
        初始化对话管理器

        Args:
            max_turns: 最大对话轮数
        """
        self.max_turns = max_turns
        self.conversations = {}  # session_id -> conversation history
        logger.info(f"Conversation manager initialized: max_turns={max_turns}")

    def start_conversation(self, session_id: str) -> Dict:
        """
        开始新对话

        Args:
            session_id: 会话ID

        Returns:
            对话状态
        """
        self.conversations[session_id] = {
            "state": DialogueState.INITIAL,
            "turns": [],
            "context": {},
            "current_query": None,
            "clarification_needed": False
        }

        logger.info(f"Started conversation: session_id={session_id}")
        return self.conversations[session_id]

    def add_turn(
        self,
        session_id: str,
        user_query: str,
        system_response: Optional[str] = None
    ) -> Dict:
        """
        添加对话轮次

        Args:
            session_id: 会话ID
            user_query: 用户查询
            system_response: 系统响应

        Returns:
            更新后的对话状态
        """
        if session_id not in self.conversations:
            self.start_conversation(session_id)

        conversation = self.conversations[session_id]

        # 检查对话轮数限制
        if len(conversation["turns"]) >= self.max_turns:
            logger.warning(f"Max turns reached: session_id={session_id}")
            conversation["state"] = DialogueState.COMPLETED
            return conversation

        # 添加对话轮次
        turn = {
            "turn_id": len(conversation["turns"]) + 1,
            "user_query": user_query,
            "system_response": system_response,
            "timestamp": self._get_timestamp()
        }
        conversation["turns"].append(turn)
        conversation["current_query"] = user_query

        logger.info(f"Added turn {turn['turn_id']}: session_id={session_id}")
        return conversation

    def update_state(self, session_id: str, new_state: DialogueState) -> Dict:
        """
        更新对话状态

        Args:
            session_id: 会话ID
            new_state: 新状态

        Returns:
            更新后的对话状态
        """
        if session_id not in self.conversations:
            logger.error(f"Conversation not found: session_id={session_id}")
            return {}

        conversation = self.conversations[session_id]
        old_state = conversation["state"]
        conversation["state"] = new_state

        logger.info(f"State changed: {old_state} -> {new_state} (session_id={session_id})")
        return conversation

    def update_context(self, session_id: str, context: Dict) -> Dict:
        """
        更新对话上下文

        Args:
            session_id: 会话ID
            context: 上下文信息

        Returns:
            更新后的对话状态
        """
        if session_id not in self.conversations:
            logger.error(f"Conversation not found: session_id={session_id}")
            return {}

        conversation = self.conversations[session_id]
        conversation["context"].update(context)

        logger.info(f"Context updated: session_id={session_id}, keys={list(context.keys())}")
        return conversation

    def get_conversation(self, session_id: str) -> Optional[Dict]:
        """
        获取对话历史

        Args:
            session_id: 会话ID

        Returns:
            对话历史
        """
        return self.conversations.get(session_id)

    def get_last_turn(self, session_id: str) -> Optional[Dict]:
        """
        获取最后一轮对话

        Args:
            session_id: 会话ID

        Returns:
            最后一轮对话
        """
        conversation = self.conversations.get(session_id)
        if conversation and conversation["turns"]:
            return conversation["turns"][-1]
        return None

    def needs_clarification(self, session_id: str, reason: str) -> None:
        """
        标记需要澄清

        Args:
            session_id: 会话ID
            reason: 澄清原因
        """
        if session_id in self.conversations:
            conversation = self.conversations[session_id]
            conversation["clarification_needed"] = True
            conversation["clarification_reason"] = reason
            conversation["state"] = DialogueState.CLARIFYING
            logger.info(f"Clarification needed: session_id={session_id}, reason={reason}")

    def end_conversation(self, session_id: str) -> Dict:
        """
        结束对话

        Args:
            session_id: 会话ID

        Returns:
            对话总结
        """
        if session_id not in self.conversations:
            return {}

        conversation = self.conversations[session_id]
        conversation["state"] = DialogueState.COMPLETED

        summary = {
            "session_id": session_id,
            "total_turns": len(conversation["turns"]),
            "final_state": conversation["state"].value,
            "context": conversation["context"]
        }

        logger.info(f"Ended conversation: session_id={session_id}, turns={summary['total_turns']}")
        return summary

    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()


# 全局实例
conversation_manager = ConversationManager()
