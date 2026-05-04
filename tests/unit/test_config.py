"""
config.py 单元测试 — Settings 加载、默认值、环境变量覆盖
"""
import os
import pytest
from src.config import Settings, get_settings


@pytest.fixture(autouse=True)
def reset_settings_singleton():
    """每个测试前后重置单例，避免测试间污染"""
    import src.config
    src.config._settings_instance = None
    yield
    src.config._settings_instance = None


class TestSettingsDefaults:
    """默认值校验（禁用 .env 加载以测试真正的默认值）"""

    @staticmethod
    def _settings(monkeypatch=None):
        """创建不加载 .env 的 Settings 实例，清除冲突环境变量"""
        if monkeypatch:
            for key in ("DEBUG", "DEMO_MODE", "BGE_SUBPROCESS", "SKIP_BGE_MODEL",
                        "ANTHROPIC_API_KEY", "LLM_API_KEY", "NEO4J_URI",
                        "NEO4J_USER", "NEO4J_PASSWORD"):
                monkeypatch.delenv(key, raising=False)
        return Settings(_env_file=None)

    def test_app_defaults(self, monkeypatch):
        s = self._settings(monkeypatch)
        assert s.APP_NAME == "Product Knowledge Graph"
        assert s.APP_VERSION == "1.0.0"
        assert s.DEBUG is False
        assert s.DEMO_MODE is False

    def test_server_defaults(self, monkeypatch):
        s = self._settings(monkeypatch)
        assert s.SERVER_HOST == "0.0.0.0"
        assert s.SERVER_PORT == 8000

    def test_postgres_defaults(self, monkeypatch):
        s = self._settings(monkeypatch)
        assert "product_kg" in s.POSTGRES_URL
        assert s.POSTGRES_POOL_SIZE == 10

    def test_milvus_defaults(self, monkeypatch):
        s = self._settings(monkeypatch)
        assert s.MILVUS_HOST == "localhost"
        assert s.MILVUS_PORT == 19530
        assert s.MILVUS_COLLECTION == "product_knowledge"

    def test_redis_defaults(self, monkeypatch):
        s = self._settings(monkeypatch)
        assert s.REDIS_URL == "redis://localhost:6379/0"

    def test_neo4j_defaults(self, monkeypatch):
        s = self._settings(monkeypatch)
        assert s.NEO4J_URI == "bolt://localhost:7687"
        assert s.NEO4J_USER == "neo4j"

    def test_llm_defaults(self, monkeypatch):
        s = self._settings(monkeypatch)
        assert s.LLM_PROVIDER == "deepseek"
        assert "deepseek" in s.LLM_BASE_URL

    def test_embedding_defaults(self, monkeypatch):
        s = self._settings(monkeypatch)
        assert s.EMBEDDING_MODEL_NAME == "BAAI/bge-small-en-v1.5"
        assert s.EMBEDDING_DIMENSION == 384
        assert s.BGE_SUBPROCESS is False
        assert s.SKIP_BGE_MODEL is False

    def test_retrieval_defaults(self, monkeypatch):
        s = self._settings(monkeypatch)
        assert s.RETRIEVAL_TOP_K == 20
        assert s.RERANK_TOP_K == 5
        assert s.SIMILARITY_THRESHOLD == 0.7

    def test_cache_defaults(self, monkeypatch):
        s = self._settings(monkeypatch)
        assert s.CACHE_TTL == 3600

    def test_cors_defaults(self, monkeypatch):
        s = self._settings(monkeypatch)
        assert s.CORS_ALLOWED_ORIGINS[0] == "http://localhost:3000"
        assert "GET" in s.CORS_ALLOWED_METHODS

    def test_monitoring_defaults(self, monkeypatch):
        s = self._settings(monkeypatch)
        assert s.PROMETHEUS_PORT == 9090
        assert s.LOG_LEVEL == "INFO"


class TestSettingsEnvOverride:
    """环境变量覆盖"""

    def test_env_override_string(self, monkeypatch):
        monkeypatch.setenv("APP_NAME", "TestApp")
        s = Settings()
        assert s.APP_NAME == "TestApp"

    def test_env_override_bool_true(self, monkeypatch):
        monkeypatch.setenv("DEBUG", "true")
        s = Settings()
        assert s.DEBUG is True

    def test_env_override_bool_false(self, monkeypatch):
        monkeypatch.setenv("DEBUG", "false")
        s = Settings()
        assert s.DEBUG is False

    def test_env_override_int(self, monkeypatch):
        monkeypatch.setenv("SERVER_PORT", "9999")
        s = Settings()
        assert s.SERVER_PORT == 9999

    def test_env_override_float(self, monkeypatch):
        monkeypatch.setenv("SIMILARITY_THRESHOLD", "0.85")
        s = Settings()
        assert s.SIMILARITY_THRESHOLD == 0.85

    def test_env_override_bge_subprocess(self, monkeypatch):
        monkeypatch.setenv("BGE_SUBPROCESS", "true")
        s = Settings()
        assert s.BGE_SUBPROCESS is True

    def test_env_override_llm_api_key(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "sk-test-key")
        s = Settings()
        assert s.LLM_API_KEY == "sk-test-key"

    def test_env_override_multiple(self, monkeypatch):
        monkeypatch.setenv("APP_NAME", "MultiTest")
        monkeypatch.setenv("SERVER_PORT", "8080")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        s = Settings()
        assert s.APP_NAME == "MultiTest"
        assert s.SERVER_PORT == 8080
        assert s.LOG_LEVEL == "DEBUG"


class TestSettingsOptional:
    """可选字段测试"""

    def test_optional_fields_none_by_default(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        s = Settings(_env_file=None)
        assert s.ANTHROPIC_API_KEY is None
        assert s.LLM_API_KEY is None

    def test_optional_fields_can_be_none(self, monkeypatch):
        monkeypatch.delenv("NEO4J_URI", raising=False)
        s = Settings(NEO4J_URI=None)
        assert s.NEO4J_URI is None

    def test_demo_db_path(self):
        s = Settings()
        assert s.DEMO_DB_PATH == "./demo.db"


class TestGetSettings:
    """get_settings() 单例测试"""

    def test_returns_settings_instance(self):
        s = get_settings()
        assert isinstance(s, Settings)

    def test_singleton_same_instance(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_force_reload(self, monkeypatch):
        """修改环境变量后不会自动更新 — 因为单例已创建"""
        s1 = get_settings()
        monkeypatch.setenv("APP_NAME", "ChangedAfterInit")
        s2 = get_settings()
        assert s1.APP_NAME == s2.APP_NAME  # 单例，不会重新读取 env
