# 工业产品知识图谱 RAG 系统

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/tests-164/166%20passed-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-59%25-yellow)](tests/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)
[![Code style](https://img.shields.io/badge/code%20style-ruff-261230)](https://docs.astral.sh/ruff/)

面向工业场景的**确定性路由 RAG** 系统。以 "Pipeline 架构可控性" 替代 "黑盒 Agent" 的设计理念，实现意图分类 → 规则校验 → 四路混合检索 → RRF 融合 → 生成的端到端知识检索与问答。

## 项目亮点

- **四路混合检索**: 向量检索 + HyDE + 知识图谱 + SQL，RRF 融合 + Cross-Encoder 重排
- **全链路优雅降级**: Demo 模式下零外部依赖可运行完整 Pipeline（SQLite + 内存 LRU + Mock 文档）
- **Pipeline 可观测**: 自研轻量级 Pipeline Tracer，分阶段毫秒计时，支持 Prometheus 指标导出
- **自研评估框架**: RAGAS 风格 Faithfulness / Context Precision / Answer Relevancy，LLM + 规则双路径
- **BGE 子进程隔离**: 解决 Windows 上 PyTorch + uvicorn 的 segfault 问题

## 架构概览

```
用户查询
  │
  ├─ [意图分类]  LLM (DeepSeek) + 关键词降级
  │    └─ spec / troubleshoot / compatibility / general
  │
  ├─ [查询改写]  正则规则引擎（产品型号标准化、故障代码格式化）
  │
  ├─ [规则校验]  产品型号正则匹配 · 故障代码校验 · 低置信度澄清
  │
  ├─ [多路检索]  四路并行，RRF 融合
  │    ├── 向量检索   BGE Embedding → Milvus / 本地向量存储
  │    ├── HyDE 检索   领域 Mock 文档 → 零延迟假设文档生成
  │    ├── 知识图谱    Neo4j N-hop 路径查询
  │    └── SQL 检索    PostgreSQL 结构化搜索
  │
  ├─ [重排序]    Cross-Encoder (bge-reranker-v2-m3) + 上下文感知重排
  │
  └─ [响应生成]  DeepSeek Chat + 多轮对话上下文 + 规则降级生成
```

## 检索策略 Benchmark

`python scripts/benchmark_retrieval.py` 对 10 条中文工业查询（故障排查 / 规格查询 / 兼容性），基于 BGE 语义嵌入 + Demo 模式数据，实测四种策略及全链路的表现：

| 策略 | Recall@5 | MRR@5 | EntityHit@5 | P50 (ms) | P95 (ms) | Mean (ms) |
|------|----------|-------|-------------|----------|----------|-----------|
| HyDE | 0.790 | 1.000 | 0.450 | 10812 | 12520 | 10413 |
| Vector | 0.527 | 0.633 | 0.550 | 0.2 | 5.5 | 0.4 |
| KG | 0.487 | 0.553 | 0.700 | 0.0 | 0.2 | 0.0 |
| No-Retrieval | 0.000 | 0.000 | 0.100 | 0.0 | 0.0 | 0.0 |
| **全链路端到端** | — | — | — | **~29600** | — | — |

**全链路耗时分解：** 意图分类 ~1.0s | 多路检索 ~10.5s | 生成回答 ~18.1s

**关键发现：**
- **HyDE 召回最高 (79%)** — LLM 生成的假设文档质量好，但 10 秒级延迟，适合需要深度理解的复杂问题
- **Vector 平衡表现 (53% 召回, 63% MRR)** — BGE 语义嵌入提供亚毫秒级检索，适合事实型查询
- **KG 实体命中最高 (70%)** — 结构化关系遍历零延迟，适合关系推理（故障→方案、兼容性）
- **RRF 融合取各自长处** — 实际 `/search` 端点通过 RRF (k=60) 融合三路结果 + Cross-Encoder 重排

> 注：全链路约 30s 中 ~29s 为 LLM API 耗时（DeepSeek Chat）。Demo 模式下使用 Mock 降级路径，全链路可降至 <100ms。

## 技术栈

| 层 | 技术 |
|---|------|
| API 框架 | FastAPI + Pydantic v2 + uvicorn |
| 关系型存储 | PostgreSQL (SQLAlchemy 2.0 ORM)，Demo 模式降级为 SQLite |
| 向量引擎 | Milvus (pymilvus)，Demo 模式降级为本地 numpy 向量存储 |
| 图数据库 | Neo4j (Cypher, N-hop 路径查询)，Demo 模式跳过 |
| 缓存 | Redis，Demo 模式降级为内存 OrderedDict LRU |
| 嵌入模型 | BAAI/bge-small-en-v1.5 (SentenceTransformers, 子进程隔离) |
| 重排模型 | bge-reranker-v2-m3 (Demo 模式自动跳过，透传 RRF 结果) |
| LLM | DeepSeek Chat (OpenAI-compatible SDK)，支持关键词降级 |
| 评估框架 | 自研 RAGAS 风格 LLM 评估器（LLM / 规则双路径） |
| 可观测性 | Pipeline Tracer + Prometheus 指标 + 告警分级 (P0/P1/P2) |
| 容器化 | Docker + Docker Compose + GitHub Actions CI (ruff + mypy + pytest + 70% 覆盖率门禁) |

## 项目统计

| 指标 | 数值 |
|------|------|
| 源代码文件 | 66 个 |
| 测试文件 | 15 个（166 个测试用例） |
| 代码行数 | ~13,000 行 Python |
| 测试覆盖率 | 61%（CI 门禁 70%） |
| API 端点 | 10 个 |
| 自定义异常类 | 8 个 |

## Demo 模式 —— 零依赖离线演示

设置 `DEMO_MODE=true` 即可**无需任何外部服务**运行完整 Pipeline：

```bash
cp .env.example .env
# 编辑 .env，设置 DEMO_MODE=true
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

访问 `http://localhost:8000/demo` 查看搜索引擎风格演示页面，`http://localhost:8000/docs` 查看 Swagger API 文档。

Demo 模式降级策略：

| 生产依赖 | Demo 降级方案 | 效果 |
|---------|-------------|------|
| PostgreSQL | SQLite + 自动种子数据 (5产品/6故障/5兼容性) | 数据查询可用 |
| Redis | 内存 OrderedDict LRU (100条) | 缓存可用 |
| BGE Embedding (HuggingFace) | SKIP_BGE_MODEL=1 跳过 | 零延迟 |
| bge-reranker (HuggingFace) | 跳过重排，透传 RRF 结果 | 检索管线不中断 |
| Milvus 向量库 | 本地 numpy 向量存储 | 向量检索可用 |
| Neo4j 图库 | 内置 Mock 知识图谱 (3产品/6故障/12方案+关系) | 结构化的故障→方案、兼容性、N-hop路径 |
| LLM API (DeepSeek) | 关键词意图分类 + Mock HyDE 文档 + 规则生成 | 全链路可用 |

## 快速开始

### 环境要求

- Python 3.9+
- (可选) Docker Desktop —— 用于运行 PostgreSQL / Milvus / Redis / Neo4j

### 安装

```bash
git clone https://github.com/yfkzdk/product-rag.git
cd product-rag
pip install -r requirements.txt
```

### 运行 Demo（零依赖）

```bash
cp .env.example .env
# 编辑 .env：设置 DEMO_MODE=true, SKIP_BGE_MODEL=true
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### 启动完整服务

```bash
cp .env.example .env       # 编辑填入 LLM_API_KEY
docker compose up -d        # 启动 PG + Milvus + Redis + Neo4j
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/health` | 多维度健康检查 (PG/Milvus/Redis/Neo4j) |
| `GET` | `/api/v1/metrics` | Prometheus 兼容指标 |
| `GET` | `/api/v1/products/` | 产品列表 |
| `GET` | `/api/v1/products/{id}` | 产品详情 + 规格参数 |
| `GET` | `/api/v1/search/products?query=` | 产品名称/型号搜索 |
| `POST` | `/api/v1/search` | 核心 RAG 问答接口 |
| `GET` | `/api/v1/faults/?product_id=` | 故障列表 (可按产品筛选) |
| `GET` | `/api/v1/compatibility/?product_id=` | 兼容性矩阵查询 |
| `GET` | `/demo` | 演示页面 (Pipeline 追踪可视化) |

核心接口示例：

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "PROD-001 E001故障怎么解决？"}'
```

响应：

```json
{
  "answer": "好的，根据您提供的故障信息，针对PROD-001设备出现的E001故障...",
  "intent": "troubleshoot",
  "sources": ["vector", "hyde_mock"],
  "confidence": 0.95,
  "pipeline_trace": {
    "trace_id": "c70bf8f0cbab4060",
    "total_ms": 12500,
    "stages": [
      {"name": "缓存查询", "duration_ms": 0, "status": "ok"},
      {"name": "意图分类", "duration_ms": 1244, "status": "ok"},
      {"name": "规则校验", "duration_ms": 0, "status": "ok"},
      {"name": "多路检索", "duration_ms": 8, "status": "ok"},
      {"name": "RRF融合+重排", "duration_ms": 0, "status": "ok"},
      {"name": "响应生成", "duration_ms": 11274, "status": "ok"}
    ]
  }
}
```

## 项目结构

```
RAG/
├── src/
│   ├── api/              # FastAPI 路由 + 健康检查 + 演示页面
│   ├── routing/          # 意图分类 + 规则校验 + 澄清生成 + 对话状态追踪
│   ├── retrieval/        # 多路检索 (Vector/HyDE/KG) + RRF融合 + 重排序 + 查询改写
│   ├── generation/       # LLM 响应生成 + Prompt 模板 + 流式输出 + 对话管理
│   ├── evaluation/       # RAGAS 风格评估 (Faithfulness/Context Precision/Answer Relevancy)
│   ├── embeddings/       # BGE 文本嵌入 (子进程隔离，Windows uvicorn segfault 修复)
│   ├── ingestion/        # 文档解析 (Docling/PDF) + 实体抽取 + 模板分块
│   ├── storage/          # PostgreSQL / Milvus / Neo4j / 本地向量存储客户端
│   ├── cache/            # Redis 缓存 + 高级缓存策略 (LRU+TTL+预热)
│   ├── observability/    # Pipeline Tracer + Prometheus 指标 + 告警分级
│   └── middleware/        # 统一异常处理中间件
├── tests/
│   ├── unit/             # 166 个单元测试
│   ├── integration/      # 多轮对话集成测试
│   └── performance/      # 性能基准 + Locust 压力测试
├── scripts/              # 数据生成 + 验证脚本 (month1-6)
├── data/datasheets/      # 10 份 Demo 工业产品规格文档
├── docs/
│   ├── ARCHITECTURE.md   # 详细架构文档
│   └── DESIGN_DECISIONS.md  # 8 个关键设计决策记录
├── Dockerfile
├── docker-compose.yml    # 全栈服务编排
└── requirements.txt
```

## RAG 质量评估

自研评估框架，支持 LLM 和规则双路径：

- **Faithfulness (忠实度)**: Claim decomposition → 逐声明与上下文 entailment check
- **Context Precision (上下文精确度)**: 查询与检索结果的语义匹配度
- **Answer Relevancy (答案相关性)**: 逆向问题生成 + 与原问题的语义相似度

LLM 不可用时自动降级为字符级规则评估：

```python
from src.evaluation.rag_evaluator import RAGEvaluator

evaluator = RAGEvaluator()
results = evaluator.evaluate(
    query="PROD-001的功率是多少？",
    answer="PROD-001额定功率220V/50Hz",
    contexts=["PROD-001 规格：功率220V/50Hz，重量1.2kg，防护等级IP65"]
)
print(f"Faithfulness: {results['faithfulness']:.2f}")
print(f"Context Precision: {results['context_precision']:.2f}")
print(f"Overall: {results['overall_score']:.2f}")
```

## 测试

```bash
# 运行所有测试 (166/166 passed)
pytest tests/ -v

# 按模块运行
pytest tests/unit/test_month2.py -v   # 路由层
pytest tests/unit/test_month3.py -v   # 检索层
pytest tests/unit/test_month4.py -v   # 对话管理
pytest tests/unit/test_month5.py -v   # 评估框架
pytest tests/unit/test_month6.py -v   # 缓存 + 基础设施

# 集成测试
pytest tests/integration/ -v

# 覆盖率
pytest tests/ --cov=src --cov-report=term-missing
```

## 可观测性

- **Pipeline Tracer**: 每个请求生成 16 位 Trace-ID，分阶段独立计时，瓶颈可视化
- **Prometheus 指标**: 请求计数、延迟分布、检索质量评分
- **告警分级**: P0 (延迟 > 30s) / P1 (Faithfulness < 0.3) / P2 (缓存命中率 < 50%)
- **健康检查**: 四层探活 (PG/Milvus/Redis/Neo4j)，`GET /api/v1/health`

## 设计决策

详见 [docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md)，涵盖：

1. Pipeline vs Agent 架构选择
2. 四路检索 + RRF 融合权重设计
3. BGE 子进程隔离方案
4. Demo 模式全链路降级策略
5. 自研 Pipeline Tracer vs OpenTelemetry SDK
6. HyDE Mock 文档领域覆盖设计

## License

MIT © 2025
