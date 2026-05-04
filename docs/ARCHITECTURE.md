# Architecture: Industrial Product Knowledge Graph RAG

## Overview

A deterministic routing RAG pipeline for industrial product knowledge: intent classification → rule validation → 4-way hybrid retrieval → RRF fusion → LLM generation. Built with FastAPI + DeepSeek + BGE + Docker Compose infra.

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer (FastAPI)                      │
│  /api/v1/search  │  /api/v1/health  │  /api/v1/metrics  │  /demo │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                      Routing Layer                              │
│  IntentClassifier (LLM) → RuleValidator → ClarificationGen     │
│  intents: spec | troubleshoot | compatibility | general          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    Retrieval Layer (4-way Hybrid)               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Vector   │  │ BM25     │  │ HyDE     │  │ Compatibility│   │
│  │ (BGE 384d│  │ (Keyword │  │ (LLM hypo│  │ (Rule match) │   │
│  │ +Milvus) │  │ +TF-IDF) │  │ doc+Vec) │  │              │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘   │
│       └──────────────┴────────────┴───────────────┘            │
│                          │                                      │
│                   RRF Fusion + Reranker                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    Generation Layer                             │
│  ResponseGenerator (LLM) → Contextual Answer                    │
│  Stream support  │  Entity extraction  │  Source attribution    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                      Storage Layer                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Milvus   │  │ Neo4j    │  │ Postgres │  │ Local Vector │   │
│  │ (Vectors)│  │ (KG)     │  │ (+vec)   │  │ Store (demo) │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. BGE Subprocess Isolation (Windows segfault fix)
**Problem**: Loading `sentence-transformers` (PyTorch) in uvicorn main process causes segfault on Windows.
**Solution**: Subprocess worker (`embedding_worker.py`) loads BGE model in an isolated process. Communication via stdin/stdout JSON lines. Three modes: subprocess isolation (server), direct loading (CLI), hash fallback (emergency).
**Trade-off**: +~17s cold-start for model pre-loading; eliminated by lifespan pre-warming.

### 2. Deterministic Routing over Agentic
**Why**: Industrial queries are structured (specs/faults/compatibility). Deterministic routing gives predictable latency and debuggable paths. Agentic/reasoning loops add latency without proportional benefit for this domain.
**Result**: 100% intent classification accuracy on benchmark queries.

### 3. HyDE with Graceful Degradation
**Why**: HyDE (Hypothetical Document Embedding) improves recall for queries where keywords don't match indexed terms. When LLM is unavailable, falls back to rich rule-based mock documents — the system never returns empty results.
**Result**: Always returns structured Chinese technical content, even without LLM.

### 4. OpenAI SDK Unified Interface
**Why**: DeepSeek API is OpenAI-compatible. Using `openai` SDK instead of `anthropic` SDK enables provider switching without code changes. All 7 LLM-dependent modules share the same client pattern.
**Config**: `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL_CHAT`, `LLM_MODEL_LIGHT` in Settings.

### 5. Lazy Singleton Pattern
Every heavy component (Milvus client, Neo4j driver, BGE encoder, LLM clients) uses lazy initialization with `_ensure_*()` pattern. Fast import time, no connection attempts until first use, graceful degradation when services are unavailable.

## Data Flow (Search Request)

```
1. Query → IntentClassifier (LLM: deepseek-chat, 1.2s avg)
2. Intent → RuleValidator (regex patterns + constraint checks)
3. If confidence < 0.8 → ClarificationGenerator (optional)
4. 4-way parallel retrieval:
   a. VectorRetriever: BGE encode → Milvus/LocalStore cosine search
   b. BM25Retriever: keyword + TF-IDF (scikit-learn)
   c. HyDERetriever: LLM hypothetical doc → vector search
   d. CompatibilityRetriever: rule-based product matching
5. RRF (Reciprocal Rank Fusion) merge → rerank → top-K
6. ResponseGenerator (LLM: deepseek-chat, 5.4s avg) → answer + sources
7. PipelineTracer records per-stage latency → observability
```

## Infrastructure (Docker Compose)

| Service    | Image                  | Port  | Purpose                     |
|------------|------------------------|-------|-----------------------------|
| PostgreSQL | pgvector/pgvector:pg16 | 5432  | Relational + vector storage |
| Milvus     | milvusdb/milvus:v2.4   | 19530 | Vector similarity search    |
| Neo4j      | neo4j:5.25-community   | 7687  | Knowledge graph (Cypher)    |
| Redis      | redis:7-alpine         | 6379  | Query/response cache        |

Start: `bash scripts/setup_infra.sh` or `docker compose up -d`

## Tech Stack

| Layer         | Technology                                           |
|---------------|------------------------------------------------------|
| API           | FastAPI, uvicorn, UvicornWorker (single)             |
| LLM           | DeepSeek Chat (via OpenAI SDK)                       |
| Embeddings    | BAAI/bge-small-en-v1.5 (384-dim, subprocess)         |
| Reranker      | BAAI/bge-reranker-v2-m3 (skipped in subprocess mode) |
| Vector DB     | Milvus 2.4 (standalone, embedded etcd)               |
| Knowledge KG  | Neo4j 5.25 (Cypher, APOC)                            |
| Relational    | PostgreSQL 16 + pgvector                             |
| Cache         | Redis 7 (in-memory LRU fallback)                     |
| Eval          | Custom RAGAS-style: faithfulness, precision, relevancy |
| Observability | PipelineTracer (per-stage ms), Prometheus metrics    |
| Frontend      | Dark OLED Industrial (HTML/CSS/JS, no framework)     |

## Performance (Benchmark)

| Metric           | Value  |
|------------------|--------|
| Intent Accuracy  | 100%   |
| Avg Latency      | 13.8s  |
| Median Latency   | 10.5s  |
| P95 Latency      | 20.8s  |
| Retrieval (avg)  | 6.9s   |
| Generation (avg) | 5.4s   |

*Measured on 3-query quick benchmark, Windows 11, DeepSeek API, local BGE, no GPU.*

## Project Structure

```
RAG/
├── src/
│   ├── api/            # FastAPI routes, health, demo.html
│   ├── config.py       # Pydantic Settings (env-driven)
│   ├── routing/        # Intent classifier, clarification
│   ├── retrieval/      # 4-way hybrid: vector, BM25, HyDE, compat
│   ├── generation/     # LLM response generation (stream)
│   ├── embeddings/     # BGE encoder + subprocess worker
│   ├── ingestion/      # Entity extraction, pipeline
│   ├── storage/        # Milvus, Neo4j, Postgres, local vector
│   ├── evaluation/     # RAGAS-style evaluator
│   └── observability/  # Pipeline tracer
├── scripts/            # Benchmark, ingest, PDF generation, infra setup
├── data/               # Generated PDFs, local vector store
├── docker-compose.yml  # Infrastructure stack
└── .env                # Configuration (LLM keys, service URLs)
```
