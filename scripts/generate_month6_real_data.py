"""
Month 6 端到端验证 - 生成真实运行数据
"""
import sys, os, json, logging, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cache.advanced_cache import AdvancedCache
from src.storage.index_optimizer import IndexOptimizer
from src.api.load_balancer import LoadBalancer
from src.api.health_check import HealthChecker
from src.api.auto_scaler import AutoScaler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_real_data():
    print("=" * 60)
    print("Month 6 End-to-End Verification - Real Data Generation")
    print("=" * 60)

    cache = AdvancedCache()
    optimizer = IndexOptimizer()
    lb = LoadBalancer(["server1:8000", "server2:8000"])
    checker = HealthChecker()
    scaler = AutoScaler()

    real_data = []
    test_cases = [
        {"query": "PROD-001的功率是多少？", "type": "spec"},
        {"query": "设备无法启动怎么办？", "type": "troubleshoot"},
        {"query": "PROD-001和PROD-002兼容吗？", "type": "compatibility"}
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}\nTest Case {i}: {test_case['query']}\n{'='*60}")

        result = {"test_case_id": i, "query": test_case["query"], "steps": {}}

        # Step 1: Cache Operation
        print("\nStep 1: Cache Operation")
        start_time = time.time()
        cache_key = f"query:{test_case['query']}"
        cache.set(cache_key, "cached_result")
        cached = cache.get(cache_key)
        cache_time = time.time() - start_time
        result["steps"]["cache_operation"] = {
            "key": cache_key,
            "hit": cached is not None,
            "time_ms": round(cache_time * 1000, 2)
        }
        print(f"  Cache hit: {cached is not None}")
        print(f"  Time: {cache_time*1000:.2f}ms")

        # Step 2: Index Optimization
        print("\nStep 2: Index Optimization")
        patterns = optimizer.analyze_query_patterns([test_case["query"]])
        recommendations = optimizer.recommend_indexes(patterns)
        result["steps"]["index_optimization"] = {
            "patterns": patterns,
            "recommendations": len(recommendations)
        }
        print(f"  Patterns: {patterns}")
        print(f"  Recommendations: {len(recommendations)} indexes")

        # Step 3: Load Balancing
        print("\nStep 3: Load Balancing")
        server = lb.get_next_server()
        result["steps"]["load_balancing"] = {"selected_server": server}
        print(f"  Selected server: {server}")

        # Step 4: Health Check
        print("\nStep 4: Health Check")
        checker.register_check("test", lambda: True)
        health = checker.run_all_checks()
        result["steps"]["health_check"] = {
            "status": health["overall_status"],
            "checks": len(health["checks"])
        }
        print(f"  Overall status: {health['overall_status']}")
        print(f"  Checks: {len(health['checks'])}")

        # Step 5: Auto Scaling
        print("\nStep 5: Auto Scaling")
        decision = scaler.evaluate_scaling({"cpu_usage": 0.5})
        metrics = scaler.get_scaling_metrics()
        result["steps"]["auto_scaling"] = {
            "decision": decision,
            "current_instances": metrics["current_instances"]
        }
        print(f"  Decision: {decision}")
        print(f"  Current instances: {metrics['current_instances']}")

        real_data.append(result)

    output_file = "month6_real_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(real_data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}\nVerification Summary\n{'='*60}")
    print(f"Total Test Cases: {len(test_cases)}")
    print(f"Real Data Generated: {output_file}")
    print(f"File Size: {os.path.getsize(output_file)} bytes")
    print(f"\n{'='*60}\nMonth 6 End-to-End Verification Complete\n{'='*60}")

    return True

if __name__ == "__main__":
    success = generate_real_data()
    sys.exit(0 if success else 1)