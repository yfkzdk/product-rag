"""
Month 2 单元测试

测试检索层和路由层的核心功能
"""
import pytest
from src.routing.intent_classifier import IntentClassifier
from src.routing.rule_validator import RuleValidator
from src.retrieval.rrf_fusion import RRFFusion


# ===== 意图分类器测试 =====

def test_intent_classifier_spec():
    """测试规格查询意图分类"""
    classifier = IntentClassifier()

    # 测试规格查询
    result = classifier.classify("PROD-001的功率是多少？")
    assert result["intent"] == "spec"

    result = classifier.classify("产品规格参数")
    assert result["intent"] == "spec"


def test_intent_classifier_troubleshoot():
    """测试故障排查意图分类"""
    classifier = IntentClassifier()

    # 测试故障排查
    result = classifier.classify("设备无法启动怎么办？")
    assert result["intent"] == "troubleshoot"

    result = classifier.classify("故障代码E001")
    assert result["intent"] == "troubleshoot"


def test_intent_classifier_compatibility():
    """测试兼容性查询意图分类"""
    classifier = IntentClassifier()

    # 测试兼容性查询
    result = classifier.classify("PROD-001和PROD-002兼容吗？")
    assert result["intent"] == "compatibility"


def test_intent_classifier_general():
    """测试通用查询意图分类"""
    classifier = IntentClassifier()

    # 测试通用查询
    result = classifier.classify("你好")
    assert result["intent"] in ["spec", "troubleshoot", "compatibility", "general"]


# ===== 规则校验测试 =====

def test_rule_validator_spec():
    """测试规格查询规则校验"""
    validator = RuleValidator()

    # 测试通过
    is_valid, errors = validator.validate("spec", {
        "product_code": "PROD-001",
        "name": "智能控制器",
        "specifications": {"power": "220V"}
    })
    assert is_valid == True
    assert len(errors) == 0

    # 测试失败（缺少字段）
    is_valid, errors = validator.validate("spec", {
        "product_code": "PROD-001"
    })
    assert is_valid == False
    assert len(errors) > 0


def test_rule_validator_troubleshoot():
    """测试故障排查规则校验"""
    validator = RuleValidator()

    # 测试通过
    is_valid, errors = validator.validate("troubleshoot", {
        "symptom": "设备无法启动",
        "possible_causes": ["电源故障"],
        "recommended_solutions": [{"step": 1, "action": "检查电源"}]
    })
    assert is_valid == True
    assert len(errors) == 0


def test_rule_validator_compatibility():
    """测试兼容性规则校验"""
    validator = RuleValidator()

    # 测试通过
    is_valid, errors = validator.validate("compatibility", {
        "product_a": "PROD-001",
        "product_b": "PROD-002",
        "compatibility_type": "compatible"
    })
    assert is_valid == True
    assert len(errors) == 0


# ===== RRF融合测试 =====

def test_rrf_fusion():
    """测试RRF分数融合"""
    fusion = RRFFusion()

    # 模拟多路检索结果
    sql_results = [
        {"chunk_id": "1", "content": "产品A", "score": 0.9},
        {"chunk_id": "2", "content": "产品B", "score": 0.8}
    ]

    vector_results = [
        {"chunk_id": "2", "content": "产品B", "score": 0.95},
        {"chunk_id": "3", "content": "产品C", "score": 0.85}
    ]

    # 融合
    fused = fusion.fuse([sql_results, vector_results])

    # 验证
    assert len(fused) == 3
    assert all('rrf_score' in result for result in fused)

    # 验证排序（RRF分数降序）
    for i in range(len(fused) - 1):
        assert fused[i]['rrf_score'] >= fused[i + 1]['rrf_score']


def test_rrf_fusion_empty():
    """测试RRF融合（空结果）"""
    fusion = RRFFusion()

    # 测试空结果
    fused = fusion.fuse([[], []])
    assert len(fused) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])