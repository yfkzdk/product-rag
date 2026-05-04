from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from src.config import get_settings
from src.api.routes import router
from src.api.health_check import router as health_router
from src.middleware.error_handler import error_handler_middleware
import os
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    settings = get_settings()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # Pre-warm: load local vector store metadata (no-op if missing)
    try:
        from src.storage.local_vector_store import get_local_vector_store
        store = get_local_vector_store()
        if store.is_available:
            logger.info(f"Local vector store ready: {store.count} vectors (pre-encoded BGE)")
        else:
            logger.info("Local vector store not available")
    except Exception:
        logger.debug("Local vector store pre-warm skipped")

    # Pre-warm BGE encoder subprocess worker (safe, PyTorch isolated)
    try:
        from src.embeddings.bge_embedder import get_encoder
        import asyncio
        settings = get_settings()
        if settings.BGE_SUBPROCESS:
            await asyncio.to_thread(lambda: get_encoder()._ensure_model())
            logger.info("BGE subprocess worker pre-warmed")
    except Exception as e:
        logger.warning(f"BGE encoder pre-warm skipped: {e}")

    yield
    logger.info("Shutting down application")


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="产品知识图谱RAG系统",
        lifespan=lifespan
    )

    # CORS配置（从settings读取）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=settings.CORS_ALLOWED_METHODS,
        allow_headers=settings.CORS_ALLOWED_HEADERS,
    )

    # 错误处理中间件
    app.middleware("http")(error_handler_middleware)

    # 注册路由
    app.include_router(router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1")

    # Demo 页面（面试展示用）
    @app.get("/demo")
    async def demo_page():
        demo_path = os.path.join(os.path.dirname(__file__), "api", "demo.html")
        return FileResponse(demo_path, media_type="text/html; charset=utf-8")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG
    )