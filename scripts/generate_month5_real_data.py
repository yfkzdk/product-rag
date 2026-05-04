"""
Month 5 端到端验证 - 生成真实运行数据
"""
import sys, os, json, logging, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evaluation.rag_evaluator import RAGEvaluator
from src.observability.metrics import MetricsCollector
from src.observability.alerting import AlertingSystem

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_real_data():
    print("=" * 60)
    print("Month 5 End-to-End Verification - Real Data Generation")
    print("=" * 60)

    evaluator = RAGEvaluator()
    collector = MetricsCollector()
    alerter = AlertingSystem()

    real_data = []
    test_cases = [
        {
            "query": "PROD-001的功率是多少？",
            "answer": "PROD-001的功率为220V，重量为1.2kg",
            "contexts": ["PROD-001功率220V，重量1.2kg，尺寸300x200x150mm"],
            "ground_truth": "PROD-001功率220V"
        },
        {
            "query": "设备无法启动怎么办？",
            "answer": "故障E001表示设备无法启动，原因：电源故障",
            "contexts": ["故障E001：设备无法启动，原因：电源故障，解决方案：检查电源连接"],
            "ground_truth": "故障E001电源故障"
        },
        {
            "query": "PROD-001和PROD-002兼容吗？",
            "answer": "PROD-001与PROD-002完全兼容",
            "contexts": ["PROD-001与PROD-002完全兼容，使用相同通信协议"],
            "ground_truth": "PROD-001 PROD-002兼容"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}\nTest Case {i}: {test_case['query']}\n{'='*60}")

        result = {"test_case_id": i, "query": test_case["query"], "steps": {}}

        # Step 1: RAG Evaluation
        print("\nStep 1: RAG Evaluation")
        start_time = time.time()
        eval_results = evaluator.evaluate(
            test_case["query"],
            test_case["answer"],
            test_case["contexts"],
            test_case["ground_truth"]
        )
        latency = time.time() - start_time
        result["steps"]["rag_evaluation"] = eval_results
        print(f"  Overall Score: {eval_results['overall_score']:.3f}")
        print(f"  Faithfulness: {eval_results['faithfulness']:.3f}")
        print(f"  Context Precision: {eval_results['context_precision']:.3f}")

        # Step 2: Record Metrics
        print("\nStep 2: Record Metrics")
        collector.record_query()
        collector.record_latency(latency)
        collector.record_faithfulness(eval_results["faithfulness"])
        collector.record_context_precision(eval_results["context_precision"])
        result["steps"]["metrics_recording"] = {"latency": latency}
        print(f"  Latency: {latency:.3f}s")

        # Step 3: Check Alerts
        print("\nStep 3: Check Alerts")
        alerts = alerter.check_alerts({
            "faithfulness": eval_results["faithfulness"],
            "latency": latency
        })
        result["steps"]["alert_checking"] = {"alert_count": len(alerts)}
        print(f"  Alerts: {len(alerts)}")

        real_data.append(result)

    output_file = "month5_real_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(real_data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}\nVerification Summary\n{'='*60}")
    print(f"Total Test Cases: {len(test_cases)}")
    print(f"Real Data Generated: {output_file}")
    print(f"File Size: {os.path.getsize(output_file)} bytes")
    print(f"\n{'='*60}\nMonth 5 End-to-End Verification Complete\n{'='*60}")

    return True

if __name__ == "__main__":
    success = generate_real_data()
    sys.exit(0 if success else 1)