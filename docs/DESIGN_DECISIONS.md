# Design Decisions

## Why Deterministic Routing instead of Agentic/ReAct?

**Context**: Industrial product queries are highly structured — specs, fault codes, compatibility. Users search for specific product models (e.g., "ATX-500") or fault codes (e.g., "E001").

**Decision**: Deterministic intent classifier → rule validation → 4-way parallel retrieval.

**Trade-off**: We lose flexibility for open-ended questions in exchange for:
- Predictable latency (no reasoning loops)
- Debuggable pipeline (each stage traced separately)
- 100% intent accuracy on structured queries
- Guardrails against hallucination (rule validation checks for required fields like product codes)

## Why BGE Subprocess instead of ONNX or API?

**Problem**: Loading PyTorch in uvicorn multi-worker mode causes segfault on Windows.

**Options evaluated**:
1. ONNX export — no official BGE ONNX weights; export is fragile
2. Remote embedding API — adds network dependency & latency
3. Subprocess isolation — runs PyTorch in separate process, stdin/stdout JSON protocol

**Decision**: Subprocess isolation. Zero external dependencies, same model fidelity, uvicorn-safe.

**Cost**: +17s cold-start (mitigated by lifespan pre-warming), ~20MB extra memory for worker process.

## Why HyDE with Mock Fallback?

**Problem**: Small indexed corpus (3 sample PDFs) means vector search often finds nothing relevant.

**Decision**: HyDE with rich, domain-specific mock documents as fallback.

**Why not just use LLM generation directly?** HyDE first tries LLM → hypothetical document → vector search. If that fails (no LLM or Milvus), it falls back to rule-based mock docs. This means the system *always* returns something useful, even in degraded mode. The mock docs are realistic Chinese technical content, not generic "I don't know" responses.

## Why OpenAI SDK for DeepSeek?

Anthropic SDK uses `/v1/messages` format; DeepSeek uses OpenAI-compatible `/v1/chat/completions`. A local proxy (127.0.0.1:15721) was returning 502 for Anthropic-format requests. Switching to OpenAI SDK eliminated the proxy compatibility issue and made the LLM provider pluggable (config change only).

## Why pgvector PostgreSQL instead of Pinecone/Qdrant?

For a self-contained demo, PostgreSQL + pgvector gives us relational data + vector search in one dependency. Production should use Milvus for scale (10M+ vectors), but pgvector is sufficient for demo-scale (<100K vectors).

## Why No GPU?

BGE model is small (133MB, 384-dim). CPU inference is ~17s cold-start but <50ms per encode thereafter. For a demo with <10 QPS, CPU is adequate. GPU would reduce cold-start but adds Docker GPU passthrough complexity on Windows.

## Pipeline Trace Design

Every search request gets a `PipelineTracer` context manager. Each stage is wrapped:
```python
with tracer.stage("意图分类"):
    result = classifier.classify(query)
```

This produces per-request timing data used by:
- `/api/v1/metrics` endpoint (Prometheus)
- Demo page pipeline visualization
- Alert rules (e.g., latency > 1s triggers P0 alert)

## Lazy Singleton Pattern

Every heavy component uses the same pattern:
```python
_instance = None
def get_thing():
    global _instance
    if _instance is None:
        _instance = Thing()
    return _instance
```

This avoids import-time side effects (connection attempts, model loading) and allows the server to start even when dependent services are down.
