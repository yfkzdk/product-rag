"""
Faithfulness评估器

评估答案对上下文的忠实度
"""
from typing import List
import re
import logging

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> set:
    tokens = set()
    tokens.update(re.findall(r'[一-鿿]', text))
    tokens.update(w.lower() for w in re.findall(r'[a-zA-Z0-9]+', text))
    return tokens


class FaithfulnessEvaluator:
    """忠实度评估器"""

    def __init__(self):
        logger.info("Faithfulness evaluator initialized")

    def evaluate(self, answer: str, contexts: List[str]) -> float:
        if not answer or not contexts:
            return 0.0

        context_text = " ".join(contexts)
        sentences = re.split(r'[。！？\.\!\?]', answer)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            sentences = [answer]

        supported_count = 0
        for sentence in sentences:
            sent_tokens = _tokenize(sentence)
            ctx_tokens = _tokenize(context_text)
            if not sent_tokens:
                continue
            overlap = len(sent_tokens & ctx_tokens)
            if overlap >= len(sent_tokens) * 0.5:
                supported_count += 1

        total = len(sentences)
        faithfulness = supported_count / total if total > 0 else 0.0
        logger.info(f"Faithfulness: {faithfulness:.3f}")
        return faithfulness


# 全局实例
faithfulness_evaluator = FaithfulnessEvaluator()
