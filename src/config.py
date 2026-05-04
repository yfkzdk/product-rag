from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List


class Settings(BaseSettings):
    """应用配置"""

    # 应用配置
    APP_NAME: str = "Product Knowledge Graph"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    DEMO_MODE: bool = False
    DEMO_DB_PATH: str = "./demo.db"

    # 服务器配置
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    # 数据库配置
    POSTGRES_URL: str = "postgresql://product_kg:product_kg@localhost:5432/product_kg"
    POSTGRES_POOL_SIZE: int = 10

    # Milvus配置
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "product_knowledge"
    MILVUS_INDEX_TYPE: str = "IVF_FLAT"
    MILVUS_METRIC_TYPE: str = "COSINE"
    MILVUS_NLIST: int = 1024

    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"

    # Neo4j配置
    NEO4J_URI: Optional[str] = "bolt://localhost:7687"
    NEO4J_USER: Optional[str] = "neo4j"
    NEO4J_PASSWORD: Optional[str] = "product_kg_password"

    # LLM配置 (支持 DeepSeek / Anthropic 等兼容提供商)
    ANTHROPIC_API_KEY: Optional[str] = None   # 兼容旧字段名
    LLM_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "deepseek"            # deepseek | anthropic
    LLM_BASE_URL: str = "https://api.deepseek.com"
    LLM_MODEL_CHAT: str = "deepseek-chat"      # 生成/对话模型
    LLM_MODEL_LIGHT: str = "deepseek-chat"     # 意图分类等轻量任务
    CLAUDE_MODEL_SONNET: str = "claude-sonnet-4-20250514"  # 兼容旧字段
    CLAUDE_MODEL_HAIKU: str = "claude-haiku-4-5-20251001"

    # HuggingFace配置
    HF_ENDPOINT: str = "https://hf-mirror.com"

    # Embedding配置
    BGE_SUBPROCESS: bool = False           # 子进程隔离 PyTorch（防止 uvicorn segfault）
    SKIP_BGE_MODEL: bool = False           # hash 降级模式（紧急兼容）
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSION: int = 384  # bge-small-en-v1.5 produces 384-dim vectors
    EMBEDDING_MAX_LENGTH: int = 512
    EMBEDDING_BATCH_SIZE: int = 32

    # Reranker配置
    RERANKER_MODEL_NAME: str = "BAAI/bge-reranker-v2-m3"
    RERANKER_MAX_LENGTH: int = 512
    RERANKER_BATCH_SIZE: int = 16

    # 检索配置
    RETRIEVAL_TOP_K: int = 20
    RERANK_TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.7
    RRF_K: int = 60

    # 缓存配置
    CACHE_TTL: int = 3600

    # CORS配置
    CORS_ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_ALLOWED_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_ALLOWED_HEADERS: List[str] = ["*"]

    # 监控配置
    PROMETHEUS_PORT: int = 9090
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Lazy singleton: only create on first access
_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """获取全局配置实例（延迟初始化）"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
