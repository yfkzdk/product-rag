"""
Context Precision评估器

评估检索上下文的精确度
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


class ContextPrecisionEvaluator:
    """上下文精确度评估器"""

    def __init__(self):
        logger.info("Context precision evaluator initialized")

    def evaluate(self, query: str, contexts: List[str]) -> float:
        if not contexts:
            return 0.0

        query_tokens = _tokenize(query)
        if not query_tokens:
            return 0.0

        relevance_scores = []
        for i, context in enumerate(contexts):
            ctx_tokens = _tokenize(context)
            overlap = len(query_tokens & ctx_tokens)
            coverage = overlap / len(query_tokens)
            position_weight = 1.0 / (i + 1)
            relevance_scores.append(coverage * position_weight)

        precision = sum(relevance_scores) / len(contexts)
        logger.info(f"Context precision: {precision:.3f}")
        return precision


# 全局实例
context_precision_evaluator = ContextPrecisionEvaluator()
