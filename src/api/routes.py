from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import os
import tempfile

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
import json

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
            cache_key = f"search:{request.query}:{request.session_id or 'default'}"
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


@router.post("/search/stream")
async def knowledge_search_stream(request: SearchRequest, db: Session = Depends(get_db)):
    """知识检索 + 流式生成 (SSE)"""
    settings = get_settings()
    tracer = get_pipeline_tracer()
    trace = tracer.new_trace(request.query)

    async def event_stream():
        try:
            # 1. 意图分类
            classifier = get_classifier()
            intent_result = classifier.classify(request.query)
            intent = intent_result.get("intent", "general")
            confidence = intent_result.get("confidence", 0.5)

            yield f"data: {json.dumps({'type': 'intent', 'intent': intent, 'confidence': confidence}, ensure_ascii=False)}\n\n"

            # 2. 规则校验
            import re
            if intent == "spec" and not re.search(r'[A-Z]{2,5}-\d{3,5}', request.query):
                yield f"data: {json.dumps({'type': 'error', 'message': '请提供产品型号（如 PROD-001）以查询规格信息。'}, ensure_ascii=False)}\n\n"
                return
            elif intent == "troubleshoot" and not re.search(r'E\d{3,5}', request.query) and "故障" not in request.query:
                yield f"data: {json.dumps({'type': 'error', 'message': '请描述您遇到的故障现象或提供故障代码（如 E001）。'}, ensure_ascii=False)}\n\n"
                return

            # 3. 多路检索
            retriever = get_base_retriever()
            results = retriever.retrieve(request.query, intent=intent, session_id=request.session_id)

            context_parts = []
            for r in results:
                content = r.get("content", "")
                if content:
                    source = r.get("chunk_type", "unknown")
                    context_parts.append(f"[{source}] {content}")
            context = "\n\n".join(context_parts) if context_parts else "暂无相关信息"

            # 4. 多轮对话上下文
            if request.session_id:
                cm = get_conversation_manager()
                context = cm.build_context(request.session_id, context)

            yield f"data: {json.dumps({'type': 'sources', 'count': len(results)}, ensure_ascii=False)}\n\n"

            # 5. 流式生成
            generator = get_generator()
            full_answer = []
            async for chunk in generator.generate_stream(request.query, context, intent):
                full_answer.append(chunk)
                yield f"data: {json.dumps({'type': 'token', 'content': chunk}, ensure_ascii=False)}\n\n"

            # 6. 保存对话历史
            if request.session_id:
                cm = get_conversation_manager()
                cm.add_message(request.session_id, "user", request.query)
                cm.add_message(request.session_id, "assistant", "".join(full_answer))

            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'流式生成失败：{str(e)}'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


def _build_visual_context(ocr_result: Dict, vlm_result: Dict) -> str:
    """将 OCR + VLM 分析结果构建为可注入检索上下文的文本"""
    parts = []

    if vlm_result.get("vlm_available"):
        # AI 视觉判断（最优先的语义理解）
        desc = vlm_result.get("content_description", "")
        if desc:
            parts.append(f"[VLM分析] 图片内容描述: {desc}")
        cat = vlm_result.get("category", "")
        if cat:
            parts.append(f"[VLM分析] 图片类别: {cat}")
        entities = vlm_result.get("extracted_entities", {})
        if entities:
            if entities.get("product_code"):
                parts.append(f"[VLM分析] 识别到产品型号: {entities['product_code']}")
            if entities.get("fault_code"):
                parts.append(f"[VLM分析] 识别到故障代码: {entities['fault_code']}")
            if entities.get("key_params"):
                    kp = entities["key_params"]
                    if isinstance(kp[0], dict):
                        kp = [f"{p.get('name') or p.get('parameter','')}: {p.get('value','')}" for p in kp]
                    parts.append(f"[VLM分析] 关键参数: {', '.join(kp)}")
        fault_indicators = vlm_result.get("fault_indicators", [])
        if fault_indicators:
            if isinstance(fault_indicators[0], dict):
                fault_indicators = [f"{k}: {v}" for fi in fault_indicators for k, v in fi.items()]
            parts.append(f"[VLM分析] 故障迹象: {', '.join(fault_indicators)}")
        quality = vlm_result.get("quality_assessment", {})
        if quality.get("needs_rescan"):
            parts.append("[VLM分析] 警告: 图片质量不佳，建议重新拍摄")
        relevance = vlm_result.get("relevance_summary", "")
        if relevance:
            parts.append(f"[VLM分析] 相关性: {relevance}")

    if ocr_result.get("available"):
        full_text = ocr_result.get("full_text", "")
        if full_text:
            parts.append(f"[OCR提取] 图片中的文字内容:\n{full_text}")
        avg_conf = ocr_result.get("avg_confidence", 0)
        if avg_conf:
            parts.append(f"[OCR提取] 识别置信度: {avg_conf:.0%}")

    return "\n".join(parts)


@router.post("/search/image", response_model=SearchResponse)
async def vision_search(
    image: UploadFile = File(...),
    query: str = Form(default=""),
    session_id: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
):
    """图片识别 + 知识检索 — AI视觉判断增强的RAG搜索

    上传一张产品/故障/文档图片，系统会：
    1. OCR提取图片中的文字
    2. VLM AI判断图片内容（类别/实体/质量/故障迹象）
    3. 将分析结果注入检索管道，生成增强回答
    """
    settings = get_settings()
    tracer = get_pipeline_tracer()
    trace = tracer.new_trace(query or f"[image: {image.filename}]")

    # 保存上传图片到临时文件
    suffix = os.path.splitext(image.filename or "upload.jpg")[1] or ".jpg"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await image.read()
            tmp.write(content)
            tmp_path = tmp.name
        trace.metadata["image_size"] = len(content)
        trace.metadata["image_filename"] = image.filename
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"图片保存失败：{str(e)}")

    try:
        # 1. OCR 文字提取
        with tracer.trace_stage(trace, "OCR文字提取", {"file": image.filename}):
            try:
                from src.vision.ocr_pipeline import get_ocr_pipeline
                ocr = get_ocr_pipeline(lang=settings.OCR_LANG)
                ocr_result = ocr.extract(tmp_path)
            except Exception as e:
                ocr_result = {"available": False, "full_text": "", "reason": str(e)}

        # 2. VLM AI 视觉判断
        vlm_result = {"vlm_available": False}
        with tracer.trace_stage(trace, "VLM视觉判断", {"file": image.filename}):
            if settings.VISION_ENABLED:
                try:
                    from src.vision.vlm_judge import get_vlm_judge
                    vlm = get_vlm_judge(
                        provider=settings.VLM_PROVIDER,
                        base_url=settings.VLM_BASE_URL,
                        model=settings.VLM_MODEL,
                        api_key=settings.LLM_API_KEY or settings.ANTHROPIC_API_KEY,
                    )
                    vlm_result = vlm.judge(tmp_path, query_context=query or None)
                except Exception as e:
                    vlm_result = {"vlm_available": False, "reason": str(e)}
            else:
                trace.add_stage("VLM视觉判断", 0, "skipped", "VISION_ENABLED=false")

        # 3. 构建视觉上下文
        with tracer.trace_stage(trace, "视觉上下文构建"):
            visual_context = _build_visual_context(ocr_result, vlm_result)

        # 4. 构建增强查询：OCR提取的关键实体 + 用户原始查询
        enhanced_query = query or ""
        if ocr_result.get("full_text"):
            enhanced_query = f"{query} {ocr_result['full_text'][:200]}" if query else ocr_result['full_text'][:200]
        if vlm_result.get("extracted_entities"):
            entities = vlm_result["extracted_entities"]
            for field in ("product_code", "fault_code"):
                val = entities.get(field)
                if val:
                    enhanced_query = f"{val} {enhanced_query}"

        trace.metadata["visual_query"] = enhanced_query[:100]

        # 5. 意图分类（基于增强查询）
        with tracer.trace_stage(trace, "意图分类", {"query": enhanced_query[:50]}):
            classifier = get_classifier()
            intent_result = classifier.classify(enhanced_query)
            intent = intent_result.get("intent", "general")
            confidence = intent_result.get("confidence", 0.5)
        trace.metadata["intent"] = intent

        # 6. 多路检索
        with tracer.trace_stage(trace, "多路检索", {"intent": intent}):
            retriever = get_base_retriever()
            results = retriever.retrieve(enhanced_query, intent=intent, session_id=session_id)

        # 7. 构建上下文（视觉分析 + 检索结果）
        with tracer.trace_stage(trace, "RRF融合+重排"):
            context_parts = [visual_context] if visual_context else []
            for r in results:
                content = r.get("content", "")
                if content:
                    source = r.get("chunk_type", "unknown")
                    context_parts.append(f"[{source}] {content}")
            context = "\n\n".join(context_parts) if context_parts else "暂无相关信息"

        # 8. 对话上下文
        if session_id:
            with tracer.trace_stage(trace, "对话上下文"):
                cm = get_conversation_manager()
                context = cm.build_context(session_id, context)

        # 9. VLM 质量检查 —— 图片太差时提醒用户
        quality = vlm_result.get("quality_assessment", {})
        quality_warning = ""
        if quality.get("needs_rescan"):
            issues = quality.get("issues", [])
            quality_warning = (
                "\n\n[系统提示] 上传的图片质量不佳"
                + (f"（{', '.join(issues)}）" if issues else "")
                + "，建议重新拍摄清晰的照片以获得更准确的结果。"
            )

        # 10. 生成响应
        with tracer.trace_stage(trace, "响应生成", {"intent": intent, "context_len": len(context)}):
            generator = get_generator()
            response = generator.generate(enhanced_query, context, intent)
            if quality_warning:
                response["answer"] = response["answer"] + quality_warning

        # 11. 保存对话历史
        if session_id:
            cm = get_conversation_manager()
            cm.add_message(session_id, "user", f"[图片: {image.filename}] {query}")
            cm.add_message(session_id, "assistant", response["answer"])

        result = SearchResponse(
            answer=response["answer"],
            intent=intent,
            sources=response.get("sources", []),
            confidence=confidence,
            pipeline_trace=trace.to_dict(),
        )

        tracer.record_metrics(trace, intent, len(results), len(response["answer"]))
        return result

    except ProductNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"视觉搜索失败：{str(e)}")
    finally:
        # 清理临时文件
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


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