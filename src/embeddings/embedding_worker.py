#!/usr/bin/env python
"""BGE 嵌入子进程 Worker —— 隔离 PyTorch，防止 uvicorn segfault。

启动时预加载模型，通过 stdin/stdout JSON 行协议与父进程通信。
"""
import sys
import json
import os
import logging

logging.basicConfig(level=logging.WARNING, format="[worker] %(levelname)s %(message)s")
logger = logging.getLogger("embedding_worker")

if len(sys.argv) > 1:
    os.environ["HF_ENDPOINT"] = sys.argv[1]

_worker_model = None
_load_error = None


def _load_model():
    global _worker_model, _load_error
    if _worker_model is not None:
        return True
    if _load_error is not None:
        return False
    try:
        from sentence_transformers import SentenceTransformer
        _worker_model = SentenceTransformer(
            "BAAI/bge-small-en-v1.5", device="cpu", local_files_only=True
        )
        logger.info("Model loaded successfully")
        return True
    except Exception as e:
        _load_error = str(e)
        logger.error(f"Model load failed: {e}")
        return False


def main():
    success = _load_model()
    # Signal ready/failed as first line
    print(json.dumps({"ok": success, "type": "ready", "error": _load_error}), flush=True)

    if not success:
        # Enter loop anyway — respond to ping, but fail encode requests
        pass

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            if req.get("cmd") == "ping":
                print(json.dumps({"ok": True, "type": "pong"}), flush=True)
                continue
            texts = req.get("texts", [])
            if not texts:
                print(json.dumps({"ok": False, "error": "no texts"}), flush=True)
                continue

            if not success:
                print(json.dumps({"ok": False, "error": _load_error or "model not loaded"}), flush=True)
                continue

            embeddings = _worker_model.encode(
                texts,
                batch_size=min(len(texts), 32),
                show_progress_bar=False,
                normalize_embeddings=True,
            )
            print(json.dumps({"ok": True, "embeddings": embeddings.tolist()}), flush=True)
        except Exception as e:
            print(json.dumps({"ok": False, "error": str(e)}), flush=True)


if __name__ == "__main__":
    main()
