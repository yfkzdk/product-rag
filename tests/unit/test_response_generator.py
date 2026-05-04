"""
response_generator.py 单元测试 — 规则生成 + LLM 降级路径
"""
import pytest
from src.generation.response_generator import ResponseGenerator, get_generator


@pytest.fixture(autouse=True)
def reset_generator_singleton():
    import src.generation.response_generator as mod
    mod._generator = None
    yield
    mod._generator = None


@pytest.fixture
def generator():
    """未初始化 LLM client 的生成器（走规则路径）"""
    g = ResponseGenerator()
    return g


class TestRuleBasedGenerate:
    """规则降级路径（无 LLM API key）"""

    def test_spec_with_blocks(self, generator):
        context = "[spec] 额定电压：DC 24V\n额定功率：500W\n效率：≥ 92%"
        result = generator._rule_based_generate("ATX-500 规格", context, "spec")
        assert "answer" in result
        assert "额定电压" in result["answer"]
        assert result["intent"] == "spec"
        assert "spec" in result["sources"]

    def test_spec_with_kv_pairs(self, generator):
        # Note: the regex in _rule_based_generate uses \S+ for value,
        # which breaks on values with spaces like "AC 220V"
        context = "[manual] 防护等级：IP65\n外形尺寸：215mm"
        result = generator._rule_based_generate("ATX-700 参数", context, "spec")
        assert "IP65" in result["answer"]

    def test_spec_with_blocks_no_kv_pairs(self, generator):
        context = "[spec] some unstructured text without colons"
        result = generator._rule_based_generate("查询", context, "spec")
        assert "answer" in result
        assert result["intent"] == "spec"

    def test_troubleshoot_with_solution_steps(self, generator):
        context = "[fault] 故障 E001 无输出。解决方案：检查输入电压，更换保险丝F1。"
        result = generator._rule_based_generate("E001 怎么修", context, "troubleshoot")
        assert "answer" in result
        assert "解决" in result["answer"] or "故障" in result["answer"]
        assert result["intent"] == "troubleshoot"

    def test_troubleshoot_no_solution(self, generator):
        context = "[fault] E999 未知故障，待补充。"
        result = generator._rule_based_generate("E999", context, "troubleshoot")
        # When no solution keywords found, falls back to generic message
        assert "answer" in result

    def test_general_with_blocks(self, generator):
        context = "[doc] 工业电源产品系列包括 ATX-500 和 ATX-700，适用于工业自动化场景。"
        result = generator._rule_based_generate("电源有哪些型号", context, "general")
        assert "answer" in result
        assert result["intent"] == "general"

    def test_general_empty_context(self, generator):
        result = generator._rule_based_generate("某某产品", "", "general")
        assert "answer" in result
        assert "没有找到" in result["answer"]

    def test_general_no_structured_blocks(self, generator):
        context = "plain text without any bracket tags"
        result = generator._rule_based_generate("查询", context, "general")
        assert "answer" in result
        assert result["intent"] == "general"

    def test_truncation_long_context(self, generator):
        long_text = "A" * 300
        context = f"[doc] {long_text}"
        result = generator._rule_based_generate("query", context, "general")
        snippet = result["answer"]
        assert len(snippet) < 500

    def test_multiple_source_blocks(self, generator):
        context = "[spec] 电压:220V\n[manual] 安装:DIN导轨\n[faq] 保修:3年"
        result = generator._rule_based_generate("产品信息", context, "spec")
        sources = result["sources"]
        assert len(sources) >= 1


class TestClientInit:
    """LLM client 初始化路径"""

    def test_no_api_key_uses_rule_fallback(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        from src.config import Settings, get_settings
        import src.config
        # Override the singleton so _ensure_client picks up empty keys
        src.config._settings_instance = Settings(
            _env_file=None, LLM_API_KEY=None, ANTHROPIC_API_KEY=None
        )
        g = ResponseGenerator()
        g._ensure_client()
        assert g._client is None
        assert g._initialized is True

    def test_generate_no_key_falls_back(self, monkeypatch):
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        g = ResponseGenerator()
        result = g.generate("测试查询", "[doc] 测试内容", "general")
        assert "answer" in result
        assert result["intent"] == "general"


class TestGetGenerator:
    """get_generator() 单例"""

    def test_returns_generator(self):
        g = get_generator()
        assert isinstance(g, ResponseGenerator)

    def test_singleton_same_instance(self):
        g1 = get_generator()
        g2 = get_generator()
        assert g1 is g2
