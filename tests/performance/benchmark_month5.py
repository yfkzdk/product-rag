"""
Month 5 性能基准测试
"""
import pytest
import time

from src.evaluation.rag_evaluator import RAGEvaluator

def test_performance_benchmark():
    """性能基准测试"""
    evaluator = RAGEvaluator()

    # 测试评估性能
    test_cases = [
        {
            "query": "PROD-001功率",
            "answer": "PROD-001功率220V",
            "contexts": ["PROD-001功率220V"]
        }
    ] * 10  # 10次测试

    start_time = time.time()
    for test_case in test_cases:
        evaluator.evaluate(
            test_case["query"],
            test_case["answer"],
            test_case["contexts"]
        )
    total_time = time.time() - start_time

    avg_time = total_time / len(test_cases)
    print(f"\nAverage evaluation time: {avg_time:.3f}s")
    assert avg_time < 0.1  # 平均评估时间应小于100ms

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])