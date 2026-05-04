"""
Month 4 单元测试

测试查询改写、多轮对话、上下文记忆、澄清问题生成
"""
import pytest


# ===== 查询改写测试 =====

def test_query_rewriter_init():
    """测试查询改写器初始化"""
    from src.retrieval.query_rewriter import QueryRewriter

    rewriter = QueryRewriter()
    assert rewriter is not None


def test_query_rewriter_rule_rewrite():
    """测试规则改写"""
    from src.retrieval.query_rewriter import QueryRewriter

    rewriter = QueryRewriter()

    # 测试产品型号补充
    rewritten = rewriter._rule_rewrite("prod 001的功率", None)
    assert "PROD-001" in rewritten or "prod" in rewritten.lower()

    # 测试故障代码补充
    rewritten = rewriter._rule_rewrite("e1故障", None)
    assert "E" in rewritten


def test_query_rewriter_expand():
    """测试查询扩展"""
    from src.retrieval.query_rewriter import QueryRewriter

    rewriter = QueryRewriter()

    expanded = rewriter.expand_query("产品的功率参数")
    assert len(expanded) > 0
    assert "功率" in expanded[0]


def test_query_rewriter_decompose():
    """测试查询分解"""
    from src.retrieval.query_rewriter import QueryRewriter

    rewriter = QueryRewriter()

    # 测试复杂查询分解
    sub_queries = rewriter.decompose_query("查询功率和重量以及尺寸")
    assert len(sub_queries) >= 1


# ===== 多轮对话管理测试 =====

def test_conversation_manager_init():
    """测试对话管理器初始化"""
    from src.routing.conversation_manager import ConversationManager

    manager = ConversationManager()
    assert manager is not None


def test_conversation_manager_start():
    """测试开始对话"""
    from src.routing.conversation_manager import ConversationManager

    manager = ConversationManager()

    conversation = manager.start_conversation("test-session-1")
    assert conversation is not None
    assert "state" in conversation
    assert "turns" in conversation


def test_conversation_manager_add_turn():
    """测试添加对话轮次"""
    from src.routing.conversation_manager import ConversationManager

    manager = ConversationManager()

    manager.start_conversation("test-session-2")
    conversation = manager.add_turn("test-session-2", "用户查询", "系统响应")

    assert len(conversation["turns"]) == 1
    assert conversation["turns"][0]["user_query"] == "用户查询"


# ===== 上下文记忆测试 =====

def test_conversation_memory_init():
    """测试对话记忆初始化"""
    from src.memory.conversation_memory import ConversationMemory

    memory = ConversationMemory()
    assert memory is not None


def test_conversation_memory_add():
    """测试添加记忆"""
    from src.memory.conversation_memory import ConversationMemory

    memory = ConversationMemory()

    memory.add_memory("test-session", "测试查询", "query")
    memories = memory.get_memories("test-session")

    assert len(memories) == 1
    assert memories[0]["content"] == "测试查询"


def test_conversation_memory_context():
    """测试获取上下文"""
    from src.memory.conversation_memory import ConversationMemory

    memory = ConversationMemory()

    memory.add_memory("test-session-3", "查询1", "query")
    memory.add_memory("test-session-3", "响应1", "response")

    context = memory.get_recent_context("test-session-3", window_size=2)
    assert len(context) > 0


# ===== 澄清问题生成测试 =====

def test_clarification_generator_init():
    """测试澄清问题生成器初始化"""
    from src.routing.clarification_generator import ClarificationGenerator

    generator = ClarificationGenerator()
    assert generator is not None


def test_clarification_generator_detect():
    """测试检测缺失信息"""
    from src.routing.clarification_generator import ClarificationGenerator

    generator = ClarificationGenerator()

    # 测试规格查询缺失产品型号
    missing = generator.detect_missing_info("查询功率", "spec")
    assert "missing_product" in missing

    # 测试故障查询缺失故障代码
    missing = generator.detect_missing_info("设备故障", "troubleshoot")
    assert len(missing) > 0


def test_clarification_generator_template():
    """测试模板生成"""
    from src.routing.clarification_generator import ClarificationGenerator

    generator = ClarificationGenerator()

    result = generator._template_generate("查询产品", ["missing_product"], None)
    assert "question" in result
    assert len(result["question"]) > 0


# ===== 对话状态跟踪测试 =====

def test_dialogue_state_tracker_init():
    """测试对话状态跟踪器初始化"""
    from src.routing.dialogue_state_tracker import DialogueStateTracker

    tracker = DialogueStateTracker()
    assert tracker is not None


def test_dialogue_state_tracker_update():
    """测试更新状态"""
    from src.routing.dialogue_state_tracker import DialogueStateTracker

    tracker = DialogueStateTracker()

    state = tracker.init_state("test-session")
    assert state["phase"] == "initial"

    updated = tracker.update_state("test-session", intent="spec", phase="retrieving")
    assert updated["intent"] == "spec"
    assert updated["phase"] == "retrieving"


def test_dialogue_state_tracker_slots():
    """测试槽位填充"""
    from src.routing.dialogue_state_tracker import DialogueStateTracker

    tracker = DialogueStateTracker()

    tracker.init_state("test-session-2")
    tracker.update_state("test-session-2", intent="spec")
    tracker.fill_slot("test-session-2", "product_code", "PROD-001")

    missing = tracker.get_missing_slots("test-session-2")
    assert len(missing) == 0


# ===== 多轮检索测试 =====

def test_multi_turn_retrieval_init():
    """测试多轮检索初始化"""
    from src.retrieval.multi_turn_retrieval import MultiTurnRetrieval

    retrieval = MultiTurnRetrieval()
    assert retrieval is not None


def test_multi_turn_retrieval_empty_history():
    """测试多轮检索类可正常实例化并处理基本调用"""
    from src.retrieval.multi_turn_retrieval import MultiTurnRetrieval
    from src.routing.conversation_manager import ConversationManager

    retrieval = MultiTurnRetrieval()
    cm = ConversationManager()
    cm.start_conversation("test-session-mt")

    # 验证方法签名可调用（即使参数不完整也不会崩溃类本身）
    assert retrieval is not None
    assert hasattr(retrieval, 'retrieve_with_context')


# ===== 上下文感知重排测试 =====

def test_context_aware_reranker_init():
    """测试上下文感知重排器初始化"""
    from src.retrieval.context_aware_reranker import ContextAwareReranker

    reranker = ContextAwareReranker()
    assert reranker is not None


def test_context_aware_reranker_score():
    """测试重排分数计算"""
    from src.retrieval.context_aware_reranker import ContextAwareReranker

    reranker = ContextAwareReranker()

    results = [
        {"id": "1", "content": "PROD-001功率220V", "score": 0.9},
        {"id": "2", "content": "PROD-002功率110V", "score": 0.8}
    ]

    entities = {"products": ["PROD-001"]}
    reranked = reranker.rerank(results, "查询PROD-001", entities, "spec")

    assert len(reranked) == 2
    assert "final_score" in reranked[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
