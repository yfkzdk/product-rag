#!/usr/bin/env python
"""RAG 检索质量 Benchmark 脚本

用法:
    python scripts/benchmark.py              # 完整 benchmark
    python scripts/benchmark.py --quick       # 快速测试 (3 queries)
    python scripts/benchmark.py --url http://127.0.0.1:8000  # 指定服务器

输出:
    - 每个 query 的 intent / latency / 评估分数
    - 汇总统计 (avg/median/p95)
    - JSON 报告写入 benchmark_results.json
"""
import urllib.request
import urllib.error
import json
import time
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ============================================================
# 测试查询集 — 工业产品知识图谱典型场景
# ============================================================
BENCHMARK_QUERIES = [
    {
        "id": "spec_01",
        "query": "ATX-500 power supply voltage and current specifications",
        "intent": "spec",
        "ground_truth": "ATX-500 has rated voltage 220V/50Hz, rated power 150W",
    },
    {
        "id": "spec_02",
        "query": "What are the dimensions and weight of the ATX-500?",
        "intent": "spec",
        "ground_truth": "Dimensions 120mm x 80mm x 45mm, weight 0.8kg",
    },
    {
        "id": "troubleshoot_01",
        "query": "E001 error device won't start how to fix",
        "intent": "troubleshoot",
        "ground_truth": "Check power input voltage 220V±10%, check fuses F1/F2, replace power module if needed",
    },
    {
        "id": "troubleshoot_02",
        "query": "温度读数偏差太大 E002 故障",
        "intent": "troubleshoot",
        "ground_truth": "PT100 sensor terminal oxidation, clean with alcohol, re-tighten screws, run auto-calibration",
    },
    {
        "id": "troubleshoot_03",
        "query": "E005 servo overload alarm troubleshooting",
        "intent": "troubleshoot",
        "ground_truth": "Check mechanical load, increase acceleration time Pr1.20 to 500ms, verify motor power rating",
    },
    {
        "id": "compat_01",
        "query": "Is PROD-002 compatible with ATX-500?",
        "intent": "compatibility",
        "ground_truth": "PROD-002 power module provides 24VDC, needs firmware v2.1.0+, physical M12 connectors per IEC 61076-2-101",
    },
    {
        "id": "compat_02",
        "query": "What communication protocols does ATX-500 support for system integration?",
        "intent": "spec",
        "ground_truth": "RS485 Modbus RTU, Ethernet Modbus TCP, ARM Cortex-M4 processor",
    },
    {
        "id": "general_01",
        "query": "Tell me about industrial automation systems",
        "intent": "general",
        "ground_truth": "General industrial automation overview with typical scenarios",
    },
]

QUICK_QUERIES = BENCHMARK_QUERIES[:3]


def call_search_api(base_url: str, query: str, top_k: int = 5, timeout: int = 60) -> Dict:
    """调用搜索 API"""
    req = urllib.request.Request(
        f"{base_url}/api/v1/search",
        data=json.dumps({"query": query, "top_k": top_k}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    resp = urllib.request.urlopen(req, timeout=timeout)
    elapsed = time.time() - t0
    data = json.loads(resp.read())
    data["_latency_s"] = elapsed
    return data


def run_benchmark(base_url: str, queries: List[Dict]) -> List[Dict]:
    """运行完整 benchmark"""
    results = []
    n = len(queries)

    print(f"\n{'='*70}")
    print(f"  RAG Benchmark — {n} queries against {base_url}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    for i, q in enumerate(queries):
        qid = q["id"]
        query_text = q["query"]
        expected_intent = q["intent"]
        ground_truth = q.get("ground_truth", "")

        print(f"[{i+1}/{n}] {qid}: {query_text[:80]}...")
        sys.stdout.flush()

        try:
            api_result = call_search_api(base_url, query_text)
        except Exception as e:
            print(f"  {'ERROR':12}: {e}")
            results.append({
                "id": qid,
                "query": query_text,
                "error": str(e),
                "latency_s": -1,
                "intent_ok": False,
            })
            continue

        intent = api_result.get("intent", "unknown")
        confidence = api_result.get("confidence", 0)
        answer = api_result.get("answer", "")
        sources = api_result.get("sources", [])
        trace = api_result.get("pipeline_trace", {})
        latency = api_result.get("_latency_s", -1)

        # 评估
        intent_ok = (intent == expected_intent)
        trace_stages = trace.get("stages", [])
        total_ms = trace.get("total_ms", 0)

        row = {
            "id": qid,
            "query": query_text,
            "expected_intent": expected_intent,
            "actual_intent": intent,
            "intent_ok": intent_ok,
            "confidence": confidence,
            "answer_length": len(answer),
            "num_sources": len(sources),
            "sources": sources,
            "latency_s": round(latency, 2),
            "total_ms": total_ms,
            "stages": {s["name"]: s["duration_ms"] for s in trace_stages},
            "answer_preview": answer[:120],
        }

        status = "OK" if intent_ok else f"MISMATCH (expected {expected_intent})"
        print(f"  Intent: {intent:15} {status}")
        print(f"  Latency: {latency:.1f}s  |  Sources: {sources}")
        print(f"  Answer: {answer[:100]}...")
        print()
        results.append(row)

    return results


def compute_stats(results: List[Dict]) -> Dict:
    """计算汇总统计"""
    valid = [r for r in results if r.get("latency_s", -1) > 0]
    if not valid:
        return {"error": "No valid results"}

    latencies = [r["latency_s"] for r in valid]
    latencies.sort()
    n = len(latencies)

    intent_accuracy = sum(1 for r in valid if r.get("intent_ok")) / len(valid)

    return {
        "total_queries": len(results),
        "successful": len(valid),
        "failed": len(results) - len(valid),
        "intent_accuracy": round(intent_accuracy, 3),
        "latency_avg_s": round(sum(latencies) / n, 1),
        "latency_median_s": round(latencies[n // 2], 1),
        "latency_p95_s": round(latencies[int(n * 0.95)] if n > 1 else latencies[0], 1),
        "latency_min_s": round(latencies[0], 1),
        "latency_max_s": round(latencies[-1], 1),
    }


def print_summary(stats: Dict, results: List[Dict]):
    """打印汇总报告"""
    print(f"{'='*70}")
    print(f"  BENCHMARK RESULTS")
    print(f"{'='*70}")
    print(f"  Queries:      {stats['total_queries']} total / {stats['successful']} success / {stats['failed']} failed")
    print(f"  Intent Acc:   {stats['intent_accuracy']:.0%}")
    print(f"  Latency Avg:  {stats['latency_avg_s']}s")
    print(f"  Latency Med:  {stats['latency_median_s']}s")
    print(f"  Latency P95:  {stats['latency_p95_s']}s")
    print(f"  Latency Min:  {stats['latency_min_s']}s")
    print(f"  Latency Max:  {stats['latency_max_s']}s")
    print()

    # Stage breakdown
    stage_totals = {}
    for r in results:
        for name, ms in r.get("stages", {}).items():
            if name not in stage_totals:
                stage_totals[name] = []
            stage_totals[name].append(ms)

    if stage_totals:
        print(f"  Pipeline Stage Breakdown (avg ms):")
        for name, times in sorted(stage_totals.items()):
            avg_ms = sum(times) / len(times)
            print(f"    {name:20}: {avg_ms/1000:.1f}s")
        print()

    print(f"{'='*70}")
    print(f"  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="RAG Benchmark Script")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--quick", action="store_true", help="Quick mode (3 queries)")
    parser.add_argument("--output", default="benchmark_results.json", help="Output JSON file")
    args = parser.parse_args()

    queries = QUICK_QUERIES if args.quick else BENCHMARK_QUERIES
    results = run_benchmark(args.url, queries)
    stats = compute_stats(results)
    print_summary(stats, results)

    # Write report
    report = {
        "benchmark": "RAG Industrial Knowledge Graph",
        "timestamp": datetime.now().isoformat(),
        "api_url": args.url,
        "summary": stats,
        "results": results,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved to: {args.output}")


if __name__ == "__main__":
    main()
