"""
多轮对话场景测试
"""
import pytest

from src.routing.conversation_manager import DialogueManager
from src.memory.conversation_memory import ConversationMemory

def test_multi_turn_scenario():
    """测试多轮对话场景"""
    manager = DialogueManager()
    memory = ConversationMemory()

    session_id = "multi-turn-test"

    # 开始对话
    manager.start_conversation(session_id)

    # 第一轮
    manager.add_turn(session_id, "查询PROD-001功率", "功率为220V")
    memory.add_memory(session_id, "查询PROD-001功率", "query")
    memory.add_memory(session_id, "功率为220V", "response")

    # 第二轮
    manager.add_turn(session_id, "查询重量", "重量为1.2kg")
    memory.add_memory(session_id, "查询重量", "query")

    # 获取上下文
    context = memory.get_recent_context(session_id, window_size=2)
    assert len(context) > 0

    # 结束对话
    summary = manager.end_conversation(session_id)
    assert summary["total_turns"] == 2

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
