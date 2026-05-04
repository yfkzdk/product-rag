"""
对话状态跟踪器

跟踪多轮对话的状态和意图变化
"""
from typing import Dict, Optional, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DialogueStateTracker:
    """对话状态跟踪器"""

    def __init__(self):
        """初始化对话状态跟踪器"""
        self.states = {}  # session_id -> state
        logger.info("Dialogue state tracker initialized")

    def init_state(self, session_id: str) -> Dict:
        """
        初始化对话状态

        Args:
            session_id: 会话ID

        Returns:
            初始状态
        """
        self.states[session_id] = {
            "phase": "initial",
            "intent": None,
            "entities": {},
            "slots": {},
            "turn_count": 0,
            "last_action": None,
            "confidence": 0.0
        }

        logger.info(f"Initialized state: session_id={session_id}")
        return self.states[session_id]

    def update_state(
        self,
        session_id: str,
        intent: Optional[str] = None,
        entities: Optional[Dict] = None,
        phase: Optional[str] = None,
        confidence: Optional[float] = None
    ) -> Dict:
        """
        更新对话状态

        Args:
            session_id: 会话ID
            intent: 意图
            entities: 实体
            phase: 阶段
            confidence: 置信度

        Returns:
            更新后的状态
        """
        if session_id not in self.states:
            self.init_state(session_id)

        state = self.states[session_id]

        # 更新意图
        if intent:
            state["intent"] = intent

        # 更新实体
        if entities:
            state["entities"].update(entities)

        # 更新阶段
        if phase:
            state["phase"] = phase

        # 更新置信度
        if confidence is not None:
            state["confidence"] = confidence

        # 更新轮次
        state["turn_count"] += 1

        logger.info(f"Updated state: session_id={session_id}, phase={state['phase']}, intent={state['intent']}")
        return state

    def fill_slot(self, session_id: str, slot_name: str, slot_value: str) -> Dict:
        """
        填充槽位

        Args:
            session_id: 会话ID
            slot_name: 槽位名称
            slot_value: 槽位值

        Returns:
            更新后的状态
        """
        if session_id not in self.states:
            self.init_state(session_id)

        state = self.states[session_id]
        state["slots"][slot_name] = slot_value

        logger.info(f"Filled slot: session_id={session_id}, {slot_name}={slot_value}")
        return state

    def get_missing_slots(self, session_id: str) -> List[str]:
        """
        获取缺失的槽位

        Args:
            session_id: 会话ID

        Returns:
            缺失槽位列表
        """
        if session_id not in self.states:
            return []

        state = self.states[session_id]
        intent = state.get("intent")

        if not intent:
            return []

        # 定义每种意图需要的槽位
        required_slots = {
            "spec": ["product_code"],
            "troubleshoot": ["symptom"],
            "compatibility": ["product_a", "product_b"]
        }

        required = required_slots.get(intent, [])
        filled = state.get("slots", {})

        missing = [slot for slot in required if slot not in filled]

        logger.info(f"Missing slots: session_id={session_id}, intent={intent}, missing={missing}")
        return missing

    def is_complete(self, session_id: str) -> bool:
        """
        检查对话是否完成

        Args:
            session_id: 会话ID

        Returns:
            是否完成
        """
        missing = self.get_missing_slots(session_id)
        return len(missing) == 0

    def get_state(self, session_id: str) -> Optional[Dict]:
        """
        获取对话状态

        Args:
            session_id: 会话ID

        Returns:
            对话状态
        """
        return self.states.get(session_id)

    def reset_state(self, session_id: str) -> Dict:
        """
        重置对话状态

        Args:
            session_id: 会话ID

        Returns:
            重置后的状态
        """
        return self.init_state(session_id)

    def detect_intent_change(self, session_id: str, new_intent: str) -> bool:
        """
        检测意图变化

        Args:
            session_id: 会话ID
            new_intent: 新意图

        Returns:
            是否意图变化
        """
        if session_id not in self.states:
            return False

        old_intent = self.states[session_id].get("intent")
        if old_intent and old_intent != new_intent:
            logger.info(f"Intent changed: session_id={session_id}, {old_intent} -> {new_intent}")
            return True

        return False


# 全局实例
dialogue_state_tracker = DialogueStateTracker()