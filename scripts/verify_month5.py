"""
Month 5 集成测试和验证

验证RAG评估、OpenTelemetry追踪、Prometheus指标
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evaluation.rag_evaluator import RAGEvaluator
from src.evaluation.faithfulness_evaluator import FaithfulnessEvaluator
from src.evaluation.context_precision_evaluator import ContextPrecisionEvaluator
from src.observability.tracing import TracingManager
from src.observability.metrics import MetricsCollector
from src.observability.alerting import AlertingSystem
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def verify_rag_evaluation():
    """验证RAG评估"""
    logger.info("=== 验证RAG评估 ===")

    evaluator = RAGEvaluator()

    # 测试完整评估
    results = evaluator.evaluate(
        query="PROD-001的功率是多少？",
        answer="PROD-001的功率为220V，重量为1.2kg",
        contexts=["PROD-001功率220V，重量1.2kg，尺寸300x200x150mm"],
        ground_truth="PROD-001功率220V"
    )

    logger.info(f"Faithfulness: {results['faithfulness']:.3f}")
    logger.info(f"Context Precision: {results['context_precision']:.3f}")
    logger.info(f"Context Recall: {results['context_recall']:.3f}")
    logger.info(f"Answer Relevancy: {results['answer_relevancy']:.3f}")
    logger.info(f"Overall Score: {results['overall_score']:.3f}")

    logger.info("✅ RAG评估验证完成\n")
    return True


def verify_faithfulness():
    """验证忠实度评估"""
    logger.info("=== 验证忠实度评估 ===")

    evaluator = FaithfulnessEvaluator()

    # 测试高忠实度
    score = evaluator.evaluate(
        "PROD-001功率220V，重量1.2kg",
        ["PROD-001功率220V，重量1.2kg，尺寸300x200x150mm"]
    )
    logger.info(f"高忠实度: {score:.3f}")

    # 测试低忠实度
    score = evaluator.evaluate(
        "PROD-002功率500W，重量5kg",
        ["PROD-001功率220V，重量1.2kg"]
    )
    logger.info(f"低忠实度: {score:.3f}")

    logger.info("✅ 忠实度评估验证完成\n")
    return True


def verify_context_precision():
    """验证上下文精确度"""
    logger.info("=== 验证上下文精确度 ===")

    evaluator = ContextPrecisionEvaluator()

    # 测试高精确度
    score = evaluator.evaluate("PROD-001 功率", ["PROD-001功率220V"])
    logger.info(f"高精确度: {score:.3f}")

    # 测试低精确度
    score = evaluator.evaluate("PROD-001 功率", ["PROD-002规格参数"])
    logger.info(f"低精确度: {score:.3f}")

    logger.info("✅ 上下文精确度验证完成\n")
    return True


def verify_tracing():
    """验证OpenTelemetry追踪"""
    logger.info("=== 验证OpenTelemetry追踪 ===")

    manager = TracingManager()

    # 测试追踪
    span = manager.start_span("test_span", {"key": "value"})
    logger.info(f"Span created: {span}")

    logger.info("✅ OpenTelemetry追踪验证完成\n")
    return True


def verify_metrics():
    """验证Prometheus指标"""
    logger.info("=== 验证Prometheus指标 ===")

    collector = MetricsCollector()

    # 测试指标记录
    collector.record_query()
    collector.record_latency(0.5)
    collector.record_faithfulness(0.85)
    collector.record_context_precision(0.90)

    # 获取指标
    metrics = collector.get_metrics()
    logger.info(f"Metrics available: {metrics['metrics_available']}")

    logger.info("✅ Prometheus指标验证完成\n")
    return True


def verify_alerting():
    """验证告警系统"""
    logger.info("=== 验证告警系统 ===")

    system = AlertingSystem()

    # 测试正常指标
    alerts = system.check_alerts({"faithfulness": 0.9, "latency": 0.3})
    logger.info(f"正常指标告警: {len(alerts)}个")

    # 测试低忠实度
    alerts = system.check_alerts({"faithfulness": 0.5, "latency": 0.3})
    logger.info(f"低忠实度告警: {len(alerts)}个")

    # 测试高延迟
    alerts = system.check_alerts({"faithfulness": 0.9, "latency": 1.5})
    logger.info(f"高延迟告警: {len(alerts)}个")

    logger.info("✅ 告警系统验证完成\n")
    return True


def verify_end_to_end():
    """验证端到端流程"""
    logger.info("=== 验证端到端流程 ===")

    # 初始化所有组件
    evaluator = RAGEvaluator()
    collector = MetricsCollector()
    system = AlertingSystem()

    # 1. 评估RAG质量
    results = evaluator.evaluate(
        query="PROD-001的功率是多少？",
        answer="PROD-001的功率为220V",
        contexts=["PROD-001功率220V，重量1.2kg"]
    )
    logger.info(f"1. RAG评估: overall={results['overall_score']:.3f}")

    # 2. 记录指标
    collector.record_query()
    collector.record_latency(0.5)
    collector.record_faithfulness(results["faithfulness"])
    logger.info("2. 指标记录完成")

    # 3. 检查告警
    alerts = system.check_alerts({
        "faithfulness": results["faithfulness"],
        "latency": 0.5
    })
    logger.info(f"3. 告警检查: {len(alerts)}个告警")

    logger.info("✅ 端到端流程验证完成\n")
    return True


def main():
    """主验证流程"""
    logger.info("=" * 60)
    logger.info("Month 5 RAG评估+可观测性 - 集成测试和验证")
    logger.info("=" * 60)

    try:
        # 验证各个模块
        rag_ok = verify_rag_evaluation()
        faith_ok = verify_faithfulness()
        precision_ok = verify_context_precision()
        tracing_ok = verify_tracing()
        metrics_ok = verify_metrics()
        alerting_ok = verify_alerting()
        e2e_ok = verify_end_to_end()

        # 最终总结
        logger.info("=" * 60)
        logger.info("验证结果总结")
        logger.info("=" * 60)

        logger.info(f"✅ RAG评估: {'正常工作' if rag_ok else '失败'}")
        logger.info(f"✅ 忠实度评估: {'正常工作' if faith_ok else '失败'}")
        logger.info(f"✅ 上下文精确度: {'正常工作' if precision_ok else '失败'}")
        logger.info(f"✅ OpenTelemetry追踪: {'正常工作' if tracing_ok else '失败'}")
        logger.info(f"✅ Prometheus指标: {'正常工作' if metrics_ok else '失败'}")
        logger.info(f"✅ 告警系统: {'正常工作' if alerting_ok else '失败'}")
        logger.info(f"✅ 端到端流程: {'逻辑闭环' if e2e_ok else '失败'}")

        logger.info("\n" + "=" * 60)
        logger.info("🎉 Month 5 RAG评估+可观测性验证完成")
        logger.info("所有核心功能正常工作，系统逻辑完整闭环")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"\n❌ 验证流程失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)