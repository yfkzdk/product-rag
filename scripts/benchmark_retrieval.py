#!/usr/bin/env python3
"""
Retrieval Benchmark Suite

Measures recall@5, MRR@5, and latency (P50/P95) for each retrieval strategy:
  - Vector (BGE embedding → cosine similarity)
  - HyDE (hypothetical doc embedding → cosine similarity)
  - KG (knowledge graph relationship traversal)
  - No-retrieval LLM-only baseline

Usage:
  python scripts/benchmark_retrieval.py           # full benchmark (demo mode)
  python scripts/benchmark_retrieval.py --live     # production mode (needs services)
  python scripts/benchmark_retrieval.py --output table  # markdown table only
"""
from __future__ import annotations

import json
import os
import sys
import time
import argparse
from typing import List, Dict, Tuple
from collections import defaultdict

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import get_settings, Settings
from src.retrieval.vector_retriever import get_vector_retriever
from src.retrieval.hyde_retriever import get_hyde_retriever
from src.retrieval.kg_retriever import get_kg_retriever


# ── Test queries with ground truth ──────────────────────
# Each query has: query text, relevant content keywords (for recall judgment),
# expected answer type, and expected entity mentions.
BENCHMARK_QUERIES = [
    {
        "query": "PROD-001 E001设备无法启动怎么办",
        "type": "troubleshoot",
        "relevant_keywords": ["电源", "保险丝", "E001", "电压", "启动"],
        "expected_entities": ["PROD-001", "E001"],
    },
    {
        "query": "PROD-002的技术规格参数是什么",
        "type": "spec",
        "relevant_keywords": ["规格", "电压", "功率", "尺寸", "PROD-002"],
        "expected_entities": ["PROD-002"],
    },
    {
        "query": "温度传感器读数偏差过大怎么排查",
        "type": "troubleshoot",
        "relevant_keywords": ["温度", "传感器", "偏差", "校准", "E002"],
        "expected_entities": ["E002"],
    },
    {
        "query": "PROD-003通信中断了如何恢复",
        "type": "troubleshoot",
        "relevant_keywords": ["通信", "网络", "网关", "E005", "中断"],
        "expected_entities": ["PROD-003", "E005"],
    },
    {
        "query": "PROD-001和PROD-002是否兼容",
        "type": "compatibility",
        "relevant_keywords": ["兼容", "PROD-001", "PROD-002"],
        "expected_entities": ["PROD-001", "PROD-002"],
    },
    {
        "query": "输出电压不稳定波动大是什么原因",
        "type": "troubleshoot",
        "relevant_keywords": ["电压", "不稳定", "波动", "电容", "E003"],
        "expected_entities": ["E003"],
    },
    {
        "query": "伺服驱动器过载报警怎么处理",
        "type": "troubleshoot",
        "relevant_keywords": ["伺服", "过载", "OL", "机械", "加速"],
        "expected_entities": ["E005"],
    },
    {
        "query": "压力传感器一直显示4mA零点值",
        "type": "troubleshoot",
        "relevant_keywords": ["压力", "4mA", "零点", "引压管", "堵塞"],
        "expected_entities": ["E006"],
    },
    {
        "query": "电源模块散热风扇不转导致过温",
        "type": "troubleshoot",
        "relevant_keywords": ["电源", "散热", "风扇", "过温", "E004"],
        "expected_entities": ["E004"],
    },
    {
        "query": "设备的防护等级和认证标准",
        "type": "spec",
        "relevant_keywords": ["防护", "IP65", "认证", "CE", "UL"],
        "expected_entities": [],
    },
]


# ── Metrics computation ─────────────────────────────────

def compute_recall_at_k(retrieved: List[Dict], relevant_keywords: List[str], k: int = 5) -> float:
    """Fraction of relevant keywords found in top-k retrieved content."""
    if not retrieved or not relevant_keywords:
        return 0.0
    top_k_docs = retrieved[:k]
    combined = " ".join(d.get("content", "") for d in top_k_docs).lower()
    hits = sum(1 for kw in relevant_keywords if kw.lower() in combined)
    return hits / len(relevant_keywords)


def compute_mrr_at_k(retrieved: List[Dict], relevant_keywords: List[str], k: int = 5) -> float:
    """Mean Reciprocal Rank: 1/rank of first relevant document."""
    if not retrieved or not relevant_keywords:
        return 0.0
    for i, doc in enumerate(retrieved[:k], start=1):
        content = doc.get("content", "").lower()
        if any(kw.lower() in content for kw in relevant_keywords):
            return 1.0 / i
    return 0.0


def compute_entity_hit_rate(retrieved: List[Dict], expected_entities: List[str], k: int = 5) -> float:
    """Fraction of expected entities found in top-k results."""
    if not expected_entities:
        return 1.0  # no entities expected → perfect score
    if not retrieved:
        return 0.0  # no results but entities expected → miss
    top_k_content = " ".join(d.get("content", "") for d in retrieved[:k])
    hits = sum(1 for ent in expected_entities if ent in top_k_content)
    return hits / len(expected_entities)


# ── Strategy runners ────────────────────────────────────

def run_vector_retrieval(query: str, top_k: int = 5) -> Tuple[List[Dict], float]:
    """Vector retrieval via BGE embedding → Milvus/local cosine similarity."""
    retriever = get_vector_retriever()
    start = time.perf_counter()
    results = retriever.retrieve(query, top_k=top_k)
    latency = time.perf_counter() - start
    return results, latency


def run_hyde_retrieval(query: str, top_k: int = 5) -> Tuple[List[Dict], float]:
    """HyDE retrieval: hypothetical doc → embed → search (mock fallback in demo)."""
    retriever = get_hyde_retriever()
    start = time.perf_counter()
    results = retriever.retrieve(query, top_k=top_k)
    latency = time.perf_counter() - start
    return results, latency


def run_kg_retrieval(query: str, top_k: int = 5) -> Tuple[List[Dict], float]:
    """KG retrieval: embedding entity match → relationship traversal."""
    retriever = get_kg_retriever()
    start = time.perf_counter()
    results = retriever.retrieve(query, top_k=top_k)
    latency = time.perf_counter() - start
    return results, latency


def run_no_retrieval(query: str) -> Tuple[List[Dict], float]:
    """No-retrieval baseline: returns empty context (LLM-only generation)."""
    start = time.perf_counter()
    latency = time.perf_counter() - start
    return [], latency


STRATEGIES = {
    "Vector": run_vector_retrieval,
    "HyDE": run_hyde_retrieval,
    "KG": run_kg_retrieval,
    "No-Retrieval": run_no_retrieval,
}


def run_end_to_end(query: str) -> Tuple[float, Dict]:
    """全链路端到端：意图分类 → 多路检索 → RRF → 重排 → 生成
    Returns (latency_seconds, stage_breakdown_ms)"""
    from src.routing.intent_classifier import get_classifier
    from src.retrieval.base_retriever import get_base_retriever
    from src.generation.response_generator import get_generator

    start = time.perf_counter()
    stages = {}

    # 1. 意图分类
    t0 = time.perf_counter()
    classifier = get_classifier()
    intent_result = classifier.classify(query)
    intent = intent_result.get("intent", "general")
    stages["intent"] = round((time.perf_counter() - t0) * 1000, 1)

    # 2. 多路检索（Vector + HyDE + KG 并行 → RRF → Cross-Encoder）
    t0 = time.perf_counter()
    retriever = get_base_retriever()
    results = retriever.retrieve(query, intent=intent)
    stages["retrieval"] = round((time.perf_counter() - t0) * 1000, 1)
    stages["result_count"] = len(results)

    # 3. 上下文构建
    t0 = time.perf_counter()
    context_parts = [f"[{r.get('chunk_type', 'unknown')}] {r.get('content', '')}" for r in results]
    context = "\n\n".join(context_parts) if context_parts else "暂无相关信息"
    stages["context_build"] = round((time.perf_counter() - t0) * 1000, 1)

    # 4. LLM 生成响应
    t0 = time.perf_counter()
    generator = get_generator()
    response = generator.generate(query, context, intent)
    stages["generation"] = round((time.perf_counter() - t0) * 1000, 1)
    stages["answer_len"] = len(response.get("answer", ""))

    latency_sec = time.perf_counter() - start
    stages["total_ms"] = round(latency_sec * 1000, 1)

    return latency_sec, stages


# ── Benchmark runner ────────────────────────────────────

def compute_percentiles(values: List[float]) -> Dict[str, float]:
    """Compute P50 and P95 from a list of values."""
    if not values:
        return {"p50": 0.0, "p95": 0.0, "mean": 0.0}
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    p50_idx = int(n * 0.50)
    p95_idx = int(n * 0.95)
    return {
        "p50": sorted_vals[min(p50_idx, n - 1)] * 1000,
        "p95": sorted_vals[min(p95_idx, n - 1)] * 1000,
        "mean": sum(values) / n * 1000,
    }


def run_benchmark(queries: List[Dict], warmup: int = 2, runs: int = 3) -> Dict:
    """Run full benchmark across all strategies and queries.

    Args:
        queries: List of benchmark query dicts
        warmup: Number of warmup runs per query (excluded from stats)
        runs: Number of measured runs per query
    """
    results: Dict[str, Dict[str, List]] = defaultdict(lambda: defaultdict(list))

    # Reset singletons to ensure clean state
    import src.config
    src.config._settings_instance = None
    import src.retrieval.kg_retriever
    src.retrieval.kg_retriever._kg_retriever = None
    import src.retrieval.vector_retriever
    src.retrieval.vector_retriever._vector_retriever = None
    import src.retrieval.hyde_retriever
    src.retrieval.hyde_retriever._hyde_retriever = None

    for q in BENCHMARK_QUERIES:
        query = q["query"]
        relevant_kw = q["relevant_keywords"]
        entities = q["expected_entities"]
        qtype = q["type"]

        for strat_name, strat_fn in STRATEGIES.items():
            # Warmup
            for _ in range(warmup):
                strat_fn(query)

            # Measured runs
            for _ in range(runs):
                docs, latency = strat_fn(query)
                recall = compute_recall_at_k(docs, relevant_kw)
                mrr = compute_mrr_at_k(docs, relevant_kw)
                entity_hit = compute_entity_hit_rate(docs, entities)

                results[strat_name]["latency"].append(latency)
                results[strat_name]["recall"].append(recall)
                results[strat_name]["mrr"].append(mrr)
                results[strat_name]["entity_hit"].append(entity_hit)

    # Aggregate
    aggregated = {}
    for strat_name, metrics in results.items():
        lat_pct = compute_percentiles(metrics["latency"])
        aggregated[strat_name] = {
            "recall@5": round(sum(metrics["recall"]) / len(metrics["recall"]), 3),
            "mrr@5": round(sum(metrics["mrr"]) / len(metrics["mrr"]), 3),
            "entity_hit@5": round(sum(metrics["entity_hit"]) / len(metrics["entity_hit"]), 3),
            "latency_p50_ms": round(lat_pct["p50"], 1),
            "latency_p95_ms": round(lat_pct["p95"], 1),
            "latency_mean_ms": round(lat_pct["mean"], 1),
            "total_runs": len(metrics["latency"]),
        }

    # End-to-end pipeline benchmark
    e2e_latencies = []
    e2e_stages = defaultdict(list)
    for q in queries:
        for _ in range(runs):
            total_ms, stages = run_end_to_end(q["query"])
            e2e_latencies.append(total_ms)
            for k, v in stages.items():
                if isinstance(v, (int, float)):
                    e2e_stages[k].append(v)

    e2e_pct = compute_percentiles(e2e_latencies)
    aggregated["End-to-End Pipeline"] = {
        "recall@5": None,  # N/A for full pipeline
        "mrr@5": None,
        "entity_hit@5": None,
        "latency_p50_ms": round(e2e_pct["p50"], 1),
        "latency_p95_ms": round(e2e_pct["p95"], 1),
        "latency_mean_ms": round(e2e_pct["mean"], 1),
        "total_runs": len(e2e_latencies),
        "breakdown": {
            "intent_ms": round(sum(e2e_stages["intent"]) / len(e2e_stages["intent"]), 1),
            "retrieval_ms": round(sum(e2e_stages["retrieval"]) / len(e2e_stages["retrieval"]), 1),
            "context_ms": round(sum(e2e_stages["context_build"]) / len(e2e_stages["context_build"]), 1),
            "generation_ms": round(sum(e2e_stages["generation"]) / len(e2e_stages["generation"]), 1),
        },
    }

    return aggregated


# ── Output formatting ───────────────────────────────────

def print_markdown_table(results: Dict) -> str:
    """Format results as a markdown comparison table."""
    header = "| 策略 | Recall@5 | MRR@5 | EntityHit@5 | P50 (ms) | P95 (ms) | Mean (ms) |"
    sep = "|------|----------|-------|-------------|----------|----------|-----------|"
    lines = [header, sep]

    for name in ["Vector", "HyDE", "KG", "No-Retrieval", "End-to-End Pipeline"]:
        r = results.get(name, {})
        if not r:
            continue
        recall = f"{r['recall@5']:.3f}" if r.get("recall@5") is not None else "—"
        mrr = f"{r['mrr@5']:.3f}" if r.get("mrr@5") is not None else "—"
        entity = f"{r['entity_hit@5']:.3f}" if r.get("entity_hit@5") is not None else "—"
        lines.append(
            f"| {name} | {recall} | {mrr} | {entity} "
            f"| {r['latency_p50_ms']:.1f} | {r['latency_p95_ms']:.1f} | {r['latency_mean_ms']:.1f} |"
        )

    return "\n".join(lines)


def print_rich_table(results: Dict):
    """Print a formatted table to console."""
    print("\n" + "=" * 90)
    print("  RAG Retrieval Benchmark Results")
    print("=" * 90)
    print(f"{'Strategy':<20} {'Recall@5':>9} {'MRR@5':>8} {'EntityHit@5':>12} {'P50(ms)':>9} {'P95(ms)':>9} {'Mean(ms)':>9}")
    print("-" * 90)

    for name in ["Vector", "HyDE", "KG", "No-Retrieval", "End-to-End Pipeline"]:
        r = results.get(name, {})
        if not r:
            continue
        recall_str = f"{r['recall@5']:.3f}" if r.get("recall@5") is not None else "    —"
        mrr_str = f"{r['mrr@5']:.3f}" if r.get("mrr@5") is not None else "   —"
        entity_str = f"{r['entity_hit@5']:.3f}" if r.get("entity_hit@5") is not None else "       —"
        print(
            f"  {name:<18} {recall_str:>9} {mrr_str:>8} {entity_str:>12} "
            f"{r['latency_p50_ms']:>9.1f} {r['latency_p95_ms']:>9.1f} {r['latency_mean_ms']:>9.1f}"
        )
    print("-" * 90)

    # End-to-end breakdown
    e2e = results.get("End-to-End Pipeline", {})
    if e2e and e2e.get("breakdown"):
        bd = e2e["breakdown"]
        print(f"  End-to-End Breakdown: 意图分类={bd['intent_ms']:.0f}ms | 检索={bd['retrieval_ms']:.0f}ms | 上下文={bd['context_ms']:.0f}ms | 生成={bd['generation_ms']:.0f}ms")
        print("-" * 90)

    settings = get_settings()
    print(f"  Mode: {'DEMO' if settings.DEMO_MODE else 'PRODUCTION'} (BGE={not settings.SKIP_BGE_MODEL})")
    print(f"  Queries: {len(BENCHMARK_QUERIES)} | Runs per query: 3")
    print("=" * 90 + "\n")


def print_per_query_breakdown(results: Dict):
    """Show per-query-type breakdown."""
    print("Per Query-Type Breakdown (averaged across strategies):")
    print("-" * 60)
    types = defaultdict(list)
    for q in BENCHMARK_QUERIES:
        types[q["type"]].append(q["query"])

    for qtype, queries in types.items():
        print(f"  [{qtype}] {len(queries)} queries")
        for q in queries:
            print(f"    - {q[:80]}")
    print()


def main():
    parser = argparse.ArgumentParser(description="RAG Retrieval Benchmark Suite")
    parser.add_argument("--live", action="store_true", help="Run in production mode (needs services)")
    parser.add_argument("--output", choices=["table", "json", "both"], default="both",
                        help="Output format")
    parser.add_argument("--runs", type=int, default=3, help="Number of measured runs per query")
    parser.add_argument("--warmup", type=int, default=1, help="Number of warmup runs")
    args = parser.parse_args()

    # Configure settings
    if not args.live:
        os.environ["DEMO_MODE"] = "true"
        # Don't force SKIP_BGE_MODEL — use real BGE if available for consistent embedding space
        os.environ["BGE_SUBPROCESS"] = "false"
        os.environ["NEO4J_URI"] = ""

    # Force settings reload
    import src.config
    src.config._settings_instance = None

    settings = get_settings()
    print(f"Running benchmark in {'DEMO' if settings.DEMO_MODE else 'PRODUCTION'} mode...")

    results = run_benchmark(BENCHMARK_QUERIES, warmup=args.warmup, runs=args.runs)

    if args.output in ("table", "both"):
        print_rich_table(results)
        print_per_query_breakdown(results)

    if args.output in ("json", "both"):
        print("\n--- JSON ---")
        print(json.dumps(results, indent=2, ensure_ascii=False))

    # Generate markdown for README
    md_table = print_markdown_table(results)
    print("\n--- Markdown Table (for README) ---")
    print(md_table)

    return results


if __name__ == "__main__":
    main()
