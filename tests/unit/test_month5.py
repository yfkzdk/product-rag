"""
Month 5 单元测试

测试RAG评估、OpenTelemetry追踪、Prometheus指标
"""
import pytest


# ===== RAG评估测试 =====

def test_rag_evaluator_init():
    """测试RAG评估器初始化"""
    from src.evaluation.rag_evaluator import RAGEvaluator

    evaluator = RAGEvaluator()
    assert evaluator is not None


def test_rag_evaluator_faithfulness():
    """测试忠实度评估"""
    from src.evaluation.rag_evaluator import RAGEvaluator

    evaluator = RAGEvaluator()

    # 测试高忠实度
    contexts = ["PROD-001功率220V，重量1.2kg"]
    answer = "PROD-001的功率为220V"
    score = evaluator.evaluate_faithfulness(answer, contexts)
    assert score > 0.0

    # 测试空上下文
    score = evaluator.evaluate_faithfulness("答案", [])
    assert score == 0.0


def test_rag_evaluator_context_precision():
    """测试上下文精确度评估"""
    from src.evaluation.rag_evaluator import RAGEvaluator

    evaluator = RAGEvaluator()

    # 测试高精确度
    contexts = ["PROD-001功率220V"]
    score = evaluator.evaluate_context_precision("PROD-001 功率", contexts)
    assert score > 0.0

    # 测试空上下文
    score = evaluator.evaluate_context_precision("查询", [])
    assert score == 0.0


def test_rag_evaluator_answer_relevancy():
    """测试答案相关性评估"""
    from src.evaluation.rag_evaluator import RAGEvaluator

    evaluator = RAGEvaluator()

    # 测试高相关性
    score = evaluator.evaluate_answer_relevancy("PROD-001功率", "PROD-001功率220V")
    assert score > 0.0

    # 测试空查询
    score = evaluator.evaluate_answer_relevancy("", "答案")
    assert score == 0.0


def test_rag_evaluator_known_input():
    """测试评估器对已知输入返回合理分数"""
    from src.evaluation.rag_evaluator import RAGEvaluator

    evaluator = RAGEvaluator()

    # 场景：答案完全来自上下文
    results = evaluator.evaluate(
        query="PROD-001的功率是多少？",
        answer="PROD-001的额定功率为220V/50Hz",
        contexts=["PROD-001规格参数：功率220V/50Hz，重量0.8kg"]
    )
    # 忠实度应该较高
    assert results["faithfulness"] > 0.0
    # 上下文精确度应该较高
    assert results["context_precision"] > 0.0
    # 整体分数在合理范围
    assert 0.0 <= results["overall_score"] <= 1.0


def test_rag_evaluator_chinese_text():
    """测试中文文本评估"""
    from src.evaluation.rag_evaluator import RAGEvaluator

    evaluator = RAGEvaluator()

    score = evaluator.evaluate_faithfulness("功率220V，重量0.8kg", ["PROD-001功率220V/50Hz，重量0.8kg"])
    assert score > 0.0

    # 空上下文忠实度为 0
    score = evaluator.evaluate_faithfulness("功率220V", [])
    assert score == 0.0


def test_rag_evaluator_irrelevant_answer():
    """测试不相关答案获得低分"""
    from src.evaluation.rag_evaluator import RAGEvaluator

    evaluator = RAGEvaluator()

    # 答案与查询完全不相关
    score = evaluator.evaluate_answer_relevancy("PROD-001功率", "今天天气很好适合出去玩")
    # 不相关答案得分应较低
    assert score < 0.5


# ===== Faithfulness评估测试 =====

def test_faithfulness_evaluator_init():
    """测试忠实度评估器初始化"""
    from src.evaluation.faithfulness_evaluator import FaithfulnessEvaluator

    evaluator = FaithfulnessEvaluator()
    assert evaluator is not None


def test_faithfulness_evaluator_evaluate():
    """测试忠实度评估"""
    from src.evaluation.faithfulness_evaluator import FaithfulnessEvaluator

    evaluator = FaithfulnessEvaluator()

    score = evaluator.evaluate("PROD-001功率220V", ["PROD-001功率220V"])
    assert score > 0.0


# ===== Context Precision评估测试 =====

def test_context_precision_evaluator_init():
    """测试上下文精确度评估器初始化"""
    from src.evaluation.context_precision_evaluator import ContextPrecisionEvaluator

    evaluator = ContextPrecisionEvaluator()
    assert evaluator is not None


def test_context_precision_evaluator_evaluate():
    """测试上下文精确度评估"""
    from src.evaluation.context_precision_evaluator import ContextPrecisionEvaluator

    evaluator = ContextPrecisionEvaluator()

    score = evaluator.evaluate("PROD-001 功率", ["PROD-001功率220V"])
    assert score > 0.0


# ===== OpenTelemetry追踪测试 =====

def test_tracing_manager_init():
    """测试追踪管理器初始化"""
    from src.observability.tracing import TracingManager

    manager = TracingManager()
    assert manager is not None


# ===== Prometheus指标测试 =====

def test_metrics_collector_init():
    """测试指标收集器初始化"""
    from src.observability.metrics import MetricsCollector

    collector = MetricsCollector()
    assert collector is not None


def test_metrics_collector_get_metrics():
    """测试获取指标"""
    from src.observability.metrics import MetricsCollector

    collector = MetricsCollector()
    metrics = collector.get_metrics()
    assert "metrics_available" in metrics


# ===== 告警系统测试 =====

def test_alerting_system_init():
    """测试告警系统初始化"""
    from src.observability.alerting import AlertingSystem

    system = AlertingSystem()
    assert system is not None


def test_alerting_system_check():
    """测试告警检查"""
    from src.observability.alerting import AlertingSystem

    system = AlertingSystem()

    # 测试正常指标
    alerts = system.check_alerts({"faithfulness": 0.9, "latency": 0.3})
    assert len(alerts) == 0

    # 测试低忠实度
    alerts = system.check_alerts({"faithfulness": 0.5, "latency": 0.3})
    assert len(alerts) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])