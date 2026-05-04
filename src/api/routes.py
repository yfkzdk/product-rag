from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from src.storage.postgres.database import get_db
from src.storage.postgres.models import Product, Fault, CompatibilityMatrix, ManualChunk
from src.retrieval.base_retriever import get_base_retriever
from src.generation.response_generator import get_generator
from src.generation.conversation_manager import get_conversation_manager
from src.routing.intent_classifier import get_classifier
from src.routing.rule_validator import RuleValidator
from src.routing.clarification_generator import get_clarification_generator
from src.cache.query_cache import get_cache
from src.config import get_settings
from src.exceptions import ProductNotFoundError, ProductKGError
from src.observability.pipeline_tracer import get_pipeline_tracer
from pydantic import BaseModel

router = APIRouter()


# Request/Response models
class SearchRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class SearchResponse(BaseModel):
    answer: str
    intent: str
    sources: list
    confidence: Optional[float] = None
    pipeline_trace: Optional[Dict[str, Any]] = None


# Products endpoints
@router.get("/products/")
async def list_products(db: Session = Depends(get_db)):
    """列出所有产品"""
    try:
        products = db.query(Product).all()
    except Exception:
        return {"products": [], "note": "Database unavailable — start PostgreSQL to see product data"}
    return [
        {
            "id": p.id,
            "product_code": p.product_code,
            "name": p.name,
            "category": p.category,
            "description": p.description
        }
        for p in products
    ]


@router.get("/products/{product_id}")
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """获取产品详情"""
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {
        "id": product.id,
        "product_code": product.product_code,
        "name": product.name,
        "category": product.category,
        "description": product.description,
        "specifications": product.specifications
    }


@router.get("/search/products")
async def search_products(
    query: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    """搜索产品（数据库全文搜索）"""
    try:
        products = db.query(Product).filter(
            Product.name.ilike(f"%{query}%") | Product.product_code.ilike(f"%{query}%")
        ).all()
    except Exception:
        return {"products": [], "note": "Database unavailable"}

    if not products:
        return []

    return [
        {
            "id": p.id,
            "product_code": p.product_code,
            "name": p.name,
            "category": p.category,
            "description": p.description
        }
        for p in products
    ]


# Knowledge search endpoint (RAG pipeline)
@router.post("/search", response_model=SearchResponse)
async def knowledge_search(request: SearchRequest, db: Session = Depends(get_db)):
    """知识检索 + 生成"""
    settings = get_settings()
    tracer = get_pipeline_tracer()
    trace = tracer.new_trace(request.query)

    try:
        # 1. 检查缓存
        with tracer.trace_stage(trace, "缓存查询", {"query": request.query[:50]}):
            cache = get_cache()
            cache_key = f"search:{request.query}"
            cached = cache.get(cache_key)
        if cached:
            trace.metadata["cache_hit"] = True
            return SearchResponse(**cached)

        # 2. 意图分类
        with tracer.trace_stage(trace, "意图分类", {"query": request.query[:50]}) as span:
            classifier = get_classifier()
            intent_result = classifier.classify(request.query)
            intent = intent_result.get("intent", "general")
            confidence = intent_result.get("confidence", 0.5)
        trace.metadata["intent"] = intent
        trace.metadata["confidence"] = confidence

        # 3. 规则校验：仅在校验通过时拦截
        with tracer.trace_stage(trace, "规则校验", {"intent": intent}):
            import re
            if intent == "spec":
                if not re.search(r'[A-Z]{2,5}-\d{3,5}', request.query):
                    trace.add_stage("多路检索", 0, "skipped", "被规则校验拦截: 缺少产品型号")
                    trace.add_stage("RRF融合+重排", 0, "skipped", "被规则校验拦截")
                    trace.add_stage("响应生成", 0, "skipped", "被规则校验拦截")
                    trace.metadata["blocked"] = "missing_product_code"
                    return SearchResponse(
                        answer="请提供产品型号（如 PROD-001）以查询规格信息。",
                        intent=intent,
                        sources=[],
                        confidence=confidence,
                        pipeline_trace=trace.to_dict(),
                    )
            elif intent == "troubleshoot":
                if not re.search(r'E\d{3,5}', request.query) and "故障" not in request.query:
                    trace.add_stage("多路检索", 0, "skipped", "被规则校验拦截: 缺少故障代码")
                    trace.add_stage("RRF融合+重排", 0, "skipped", "被规则校验拦截")
                    trace.add_stage("响应生成", 0, "skipped", "被规则校验拦截")
                    trace.metadata["blocked"] = "missing_fault_code"
                    return SearchResponse(
                        answer="请描述您遇到的故障现象或提供故障代码（如 E001）。",
                        intent=intent,
                        sources=[],
                        confidence=confidence,
                        pipeline_trace=trace.to_dict(),
                    )

        # 4. 低置信度时生成澄清问题
        if confidence < 0.6:
            with tracer.trace_stage(trace, "澄清生成"):
                clarifier = get_clarification_generator()
                questions = clarifier.generate(request.query, intent, confidence)
            if questions:
                trace.add_stage("多路检索", 0, "skipped", "低置信度澄清")
                trace.add_stage("RRF融合+重排", 0, "skipped", "低置信度澄清")
                trace.add_stage("响应生成", 0, "skipped", "低置信度澄清")
                return SearchResponse(
                    answer="您的查询不够明确，请提供更多信息：\n" + "\n".join(f"- {q}" for q in questions),
                    intent=intent,
                    sources=[],
                    confidence=confidence,
                    pipeline_trace=trace.to_dict(),
                )

        # 5. 多路检索
        with tracer.trace_stage(trace, "多路检索", {"intent": intent}):
            retriever = get_base_retriever()
            results = retriever.retrieve(request.query, intent=intent, session_id=request.session_id)

        # 6. 构建上下文
        with tracer.trace_stage(trace, "RRF融合+重排"):
            context_parts = []
            for r in results:
                content = r.get("content", "")
                if content:
                    source = r.get("chunk_type", "unknown")
                    context_parts.append(f"[{source}] {content}")
            context = "\n\n".join(context_parts) if context_parts else "暂无相关信息"

        # 7. 多轮对话上下文
        if request.session_id:
            with tracer.trace_stage(trace, "对话上下文"):
                cm = get_conversation_manager()
                context = cm.build_context(request.session_id, context)

        # 8. 生成响应
        with tracer.trace_stage(trace, "响应生成", {"intent": intent, "context_len": len(context)}):
            generator = get_generator()
            response = generator.generate(request.query, context, intent)

        # 9. 保存对话历史
        if request.session_id:
            cm = get_conversation_manager()
            cm.add_message(request.session_id, "user", request.query)
            cm.add_message(request.session_id, "assistant", response["answer"])

        # 10. 缓存结果
        result = SearchResponse(
            answer=response["answer"],
            intent=intent,
            sources=response.get("sources", []),
            confidence=confidence,
            pipeline_trace=trace.to_dict(),
        )
        cache.set(cache_key, result.model_dump())

        # 记录指标 + 检查告警
        tracer.record_metrics(trace, intent, len(results), len(response["answer"]))

        return result

    except ProductNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProductKGError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败：{str(e)}")


# Faults endpoints
@router.get("/faults/")
async def list_faults(
    product_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """列出故障"""
    try:
        query = db.query(Fault)
        if product_id:
            query = query.filter(Fault.product_id == product_id)
        faults = query.all()
    except Exception:
        return {"faults": [], "note": "Database unavailable — start PostgreSQL to see fault data"}
    return [
        {
            "id": f.id,
            "fault_code": f.fault_code,
            "description": f.description,
            "severity": f.severity.value if hasattr(f.severity, 'value') else str(f.severity),
            "product_id": f.product_id
        }
        for f in faults
    ]


# Compatibility endpoints
@router.get("/compatibility/")
async def list_compatibility(
    product_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """列出兼容性信息"""
    try:
        query = db.query(CompatibilityMatrix)
        if product_id:
            query = query.filter(
                (CompatibilityMatrix.product_a_id == product_id) |
                (CompatibilityMatrix.product_b_id == product_id)
            )
        compat = query.all()
    except Exception:
        return {"compatibility": [], "note": "Database unavailable — start PostgreSQL to see compatibility data"}
    return [
        {
            "id": c.id,
            "product_a_id": c.product_a_id,
            "product_b_id": c.product_b_id,
            "compatibility_type": c.compatibility_type,
            "confidence": c.confidence,
            "notes": c.notes
        }
        for c in compat
    ]