"""
OCR 文字提取管道 — EasyOCR / PaddleOCR 双引擎，自动切换，优雅降级

优先级：EasyOCR > PaddleOCR（PaddlePaddle 3.x 在 Windows CPU 上有 oneDNN 兼容问题）
"""
import os
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 尝试加载 EasyOCR（首选）
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

# 尝试加载 PaddleOCR（备选）
try:
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False


class OcrPipeline:
    """OCR 文字提取管道 — 双引擎自动切换"""

    def __init__(self, lang: str = "ch"):
        self.lang = lang
        self._reader = None
        self._backend = None  # "easyocr" | "paddle" | None
        self._initialized = False

    def _ensure_ocr(self):
        if self._initialized:
            return

        self._try_easyocr() or self._try_paddleocr()
        self._initialized = True

    def _try_easyocr(self) -> bool:
        if not EASYOCR_AVAILABLE:
            return False
        try:
            langs = ['ch_sim', 'en'] if self.lang == 'ch' else ['en']
            self._reader = easyocr.Reader(langs, gpu=False, verbose=False)
            self._backend = "easyocr"
            logger.info("EasyOCR initialized (langs=%s)", langs)
            return True
        except Exception as e:
            logger.warning("EasyOCR init failed: %s", e)
            return False

    def _try_paddleocr(self) -> bool:
        if not PADDLE_AVAILABLE:
            return False
        try:
            self._reader = PaddleOCR(lang=self.lang)
            self._backend = "paddle"
            logger.info("PaddleOCR initialized (lang=%s)", self.lang)
            return True
        except Exception as e:
            logger.warning("PaddleOCR init failed: %s", e)
            return False

    def extract(self, image_path: str) -> Dict:
        """从图片提取文字

        Returns:
            {"text_lines": [...], "confidence": [...], "bboxes": [...],
             "full_text": "...", "available": bool, "backend": str}
        """
        self._ensure_ocr()

        if self._reader is None or not os.path.exists(image_path):
            return self._fallback(image_path)

        try:
            if self._backend == "easyocr":
                return self._extract_easyocr(image_path)
            elif self._backend == "paddle":
                return self._extract_paddleocr(image_path)
            else:
                return self._fallback(image_path)
        except Exception as e:
            logger.error("OCR failed for %s: %s", image_path, e)
            return self._fallback(image_path)

    def _extract_easyocr(self, image_path: str) -> Dict:
        raw = self._reader.readtext(image_path)

        if not raw:
            return {"text_lines": [], "confidence": [], "bboxes": [],
                    "full_text": "", "available": True, "block_count": 0,
                    "avg_confidence": 0.0, "backend": "easyocr"}

        lines, confidences, bboxes = [], [], []
        for bbox, text, conf in raw:
            lines.append(text)
            confidences.append(round(conf, 4))
            bboxes.append(bbox)

        full_text = "\n".join(lines)
        avg_conf = sum(confidences) / len(confidences) if confidences else 0

        logger.info("EasyOCR extracted %d lines from %s (avg confidence: %.2f)",
                    len(lines), os.path.basename(image_path), avg_conf)

        return {
            "text_lines": lines,
            "confidence": confidences,
            "bboxes": bboxes,
            "full_text": full_text,
            "available": True,
            "avg_confidence": round(avg_conf, 4),
            "block_count": len(lines),
            "backend": "easyocr",
        }

    def _extract_paddleocr(self, image_path: str) -> Dict:
        result = self._reader.ocr(image_path)

        if not result or not result[0]:
            return {"text_lines": [], "confidence": [], "bboxes": [],
                    "full_text": "", "available": True, "block_count": 0,
                    "avg_confidence": 0.0, "backend": "paddle"}

        lines, confidences, bboxes = [], [], []
        for group in result:
            for line in group:
                bbox, (text, confidence) = line
                lines.append(text)
                confidences.append(round(confidence, 4))
                bboxes.append(bbox)

        full_text = "\n".join(lines)
        avg_conf = sum(confidences) / len(confidences) if confidences else 0

        logger.info("PaddleOCR extracted %d lines from %s (avg confidence: %.2f)",
                    len(lines), os.path.basename(image_path), avg_conf)

        return {
            "text_lines": lines,
            "confidence": confidences,
            "bboxes": bboxes,
            "full_text": full_text,
            "available": True,
            "avg_confidence": round(avg_conf, 4),
            "block_count": len(lines),
            "backend": "paddle",
        }

    def _fallback(self, image_path: str) -> Dict:
        exists = os.path.exists(image_path)
        return {
            "text_lines": [],
            "confidence": [],
            "bboxes": [],
            "full_text": "",
            "available": False,
            "block_count": 0,
            "avg_confidence": 0.0,
            "backend": None,
            "reason": "ocr_unavailable" if exists else "file_not_found",
        }


_ocr_pipeline: Optional[OcrPipeline] = None


def get_ocr_pipeline(lang: str = "ch") -> OcrPipeline:
    global _ocr_pipeline
    if _ocr_pipeline is None:
        _ocr_pipeline = OcrPipeline(lang=lang)
    return _ocr_pipeline
