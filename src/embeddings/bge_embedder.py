import hashlib
import json
import os
import socket
import subprocess
import atexit
from src.config import get_settings
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 3.0
_original_default_timeout = socket.getdefaulttimeout()


def _set_short_timeout():
    socket.setdefaulttimeout(_DEFAULT_TIMEOUT)


def _restore_timeout():
    socket.setdefaulttimeout(_original_default_timeout)


def _get_worker_script_path():
    return os.path.join(os.path.dirname(__file__), "embedding_worker.py")


class BGEEncoder:
    """BGE 文本嵌入模型 — 支持直接加载 / 子进程隔离 / hash 降级三种模式。

    模式选择：
    - BGE_SUBPROCESS=1: 子进程隔离 PyTorch，避免 uvicorn segfault（推荐服务器）
    - SKIP_BGE_MODEL=1: hash 降级（紧急兼容）
    - 均不设置: 直接加载模型（CLI / 脚本）
    """

    def __init__(self):
        self._model = None
        self._worker: Optional[subprocess.Popen] = None
        self._model_load_failed = False
        self._initialized = False
        self._use_subprocess = False

    def _ensure_model(self):
        if self._initialized:
            return
        if self._model_load_failed:
            return

        import os
        settings = get_settings()

        # Path A: hash-only fallback
        if settings.SKIP_BGE_MODEL:
            self._model_load_failed = True
            self._initialized = True
            logger.info("BGE: hash fallback (SKIP_BGE_MODEL=1)")
            return

        # Path B: subprocess-isolated worker (safe under uvicorn)
        if settings.BGE_SUBPROCESS:
            self._start_worker()
            return

        # Path C: direct model loading (CLI usage)
        settings = get_settings()

        for strategy in ["local_cache", "download", "offline"]:
            try:
                _set_short_timeout()
                from sentence_transformers import SentenceTransformer
                kwargs = {"device": "cpu"}
                if strategy == "local_cache":
                    kwargs["local_files_only"] = True
                elif strategy == "download":
                    os.environ["HF_ENDPOINT"] = settings.HF_ENDPOINT
                elif strategy == "offline":
                    os.environ["HF_HUB_OFFLINE"] = "1"
                    kwargs["local_files_only"] = True

                self._model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME, **kwargs)
                self._initialized = True
                logger.info(f"BGE model loaded ({strategy}): {settings.EMBEDDING_MODEL_NAME}")
                return
            except Exception:
                logger.debug(f"BGE load strategy '{strategy}' failed")
            finally:
                _restore_timeout()

        self._model_load_failed = True
        self._initialized = True
        logger.warning("BGE model unavailable, using hash fallback")

    def _start_worker(self):
        """启动子进程嵌入 Worker，隔离 PyTorch 防止 uvicorn segfault"""
        settings = get_settings()
        script = _get_worker_script_path()
        try:
            self._worker = subprocess.Popen(
                [os.sys.executable, script, settings.HF_ENDPOINT],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            # Read ready signal (model preloaded in worker)
            resp = self._worker.stdout.readline()
            data = json.loads(resp)
            if data.get("ok"):
                self._initialized = True
                self._use_subprocess = True
                logger.info("BGE subprocess worker started successfully")
                atexit.register(self._stop_worker)
            else:
                raise RuntimeError(f"Worker model load failed: {data.get('error')}")
        except Exception as e:
            logger.warning(f"BGE subprocess worker failed to start: {e}")
            self._stop_worker()
            self._model_load_failed = True
            self._initialized = True

    def _stop_worker(self):
        if self._worker:
            try:
                self._worker.stdin.close()
                self._worker.stdout.close()
                self._worker.terminate()
                self._worker.wait(timeout=3)
            except Exception:
                try:
                    self._worker.kill()
                except Exception:
                    pass
            self._worker = None
            self._use_subprocess = False

    def _encode_subprocess(self, texts: List[str]) -> Optional[List[List[float]]]:
        """通过子进程 Worker 编码，失败返回 None"""
        if self._worker is None or self._worker.poll() is not None:
            logger.warning("BGE worker died, falling back to hash")
            self._stop_worker()
            self._model_load_failed = True
            return None
        try:
            self._worker.stdin.write(json.dumps({"texts": texts}) + "\n")
            self._worker.stdin.flush()
            resp = self._worker.stdout.readline()
            data = json.loads(resp)
            if data.get("ok"):
                return data["embeddings"]
            else:
                logger.warning(f"BGE worker error: {data.get('error')}")
                return None
        except Exception as e:
            logger.warning(f"BGE worker communication failed: {e}")
            self._stop_worker()
            return None

    def _hash_vector(self, text: str) -> List[float]:
        dim = self.dimension
        vec = [0.0] * dim
        for seed in range(4):
            h = hashlib.sha256(f"{seed}:{text}".encode()).digest()
            for i in range(min(dim, len(h) * 8)):
                byte_idx = i // 8
                bit_idx = i % 8
                if (h[byte_idx % len(h)] >> bit_idx) & 1:
                    vec[i] += 0.25
        norm = sum(v * v for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def encode(self, texts: List[str], batch_size: Optional[int] = None) -> List[List[float]]:
        self._ensure_model()

        # Subprocess worker path
        if self._use_subprocess:
            result = self._encode_subprocess(texts)
            if result is not None:
                return result
            return [self._hash_vector(t) for t in texts]

        # Direct model path
        if self._model is None:
            logger.debug("Using hash-based fallback embeddings")
            return [self._hash_vector(t) for t in texts]

        settings = get_settings()
        effective_batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE

        try:
            embeddings = self._model.encode(
                texts,
                batch_size=effective_batch_size,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
            return embeddings.tolist()
        except Exception as e:
            logger.warning(f"Embedding failed, using hash fallback: {e}")
            return [self._hash_vector(t) for t in texts]

    def encode_single(self, text: str) -> List[float]:
        result = self.encode([text])
        return result[0]

    @property
    def dimension(self) -> int:
        settings = get_settings()
        return settings.EMBEDDING_DIMENSION


_encoder: Optional[BGEEncoder] = None


def get_encoder() -> BGEEncoder:
    global _encoder
    if _encoder is None:
        _encoder = BGEEncoder()
    return _encoder
