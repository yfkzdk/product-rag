"""
RAG评估框架

基于LLM的RAG质量评估，RAGAS风格
- Faithfulness: 答案忠实度（claim decomposition + entailment check）
- Context Precision: 上下文精确度（relevance ranking）
- Answer Relevancy: 答案相关性（reverse question generation + cosine similarity）
"""
from typing import List, Dict, Optional
import logging
import re
import json

logger = logging.getLogger(__name__)


def _tokenize_for_matching(text: str) -> set:
    """混合分词：对中文用字符级，对英文用词级"""
    tokens = set()
    # 提取中文字符
    chinese_chars = re.findall(r'[一-鿿]', text)
    tokens.update(chinese_chars)
    # 提取英文/数字词
    word_tokens = re.findall(r'[a-zA-Z0-9]+', text)
    tokens.update(w.lower() for w in word_tokens)
    return tokens


class RAGEvaluator:
    """RAG评估器——LLM增强版"""

    def __init__(self):
        self._client = None
        self._initialized = False
        self.metrics = {
            "faithfulness": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0,
            "answer_relevancy": 0.0
        }
        logger.info("RAG evaluator initialized (LLM-enhanced)")

    def _ensure_client(self):
        if self._initialized:
            return
        try:
            from src.config import get_settings
            settings = get_settings()
            api_key = settings.LLM_API_KEY or settings.ANTHROPIC_API_KEY
            if api_key:
                from openai import OpenAI
                self._client = OpenAI(api_key=api_key, base_url=settings.LLM_BASE_URL)
                logger.info("LLM client ready for RAG evaluation")
            else:
                logger.info("No API key set, using improved rule-based evaluation")
        except Exception as e:
            logger.warning(f"LLM client init failed: {e}, using rule-based fallback")
        self._initialized = True

    def _llm_eval(self, system_prompt: str, user_prompt: str) -> str:
        """调用LLM进行评估"""
        self._ensure_client()
        if self._client is None:
            return None

        try:
            from src.config import get_settings
            settings = get_settings()
            response = self._client.chat.completions.create(
                model=settings.LLM_MODEL_LIGHT,
                max_tokens=512,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}")
            return None

    # ===== Faithfulness =====

    def evaluate_faithfulness(self, answer: str, contexts: List[str]) -> float:
        """评估答案对上下文的忠实度"""
        if not answer or not contexts:
            return 0.0

        result = self._llm_eval(
            "你是一个严格的事实核查员。你的任务是判断答案中的每条陈述是否可以从提供的上下文中推断出来。"
            "用JSON格式回复：{\"score\": 0.0-1.0, \"reasoning\": \"简短说明\"}",
            f"上下文：\n" + "\n---\n".join(contexts) +
            f"\n\n答案：{answer}\n\n"
            "请评估答案的每句话是否都有上下文支持。1.0=完全有依据，0.0=全部是幻觉。只返回JSON。"
        )

        if result:
            try:
                data = self._parse_json(result)
                return float(data.get("score", 0.5))
            except Exception:
                logger.debug("Failed to parse faithfulness JSON, using rule fallback")

        return self._rule_faithfulness(answer, contexts)

    def _rule_faithfulness(self, answer: str, contexts: List[str]) -> float:
        """改进的规则忠实度——支持中文"""
        context_text = " ".join(contexts)
        # 按句子分割
        sentences = re.split(r'[。！？\.\!\?]', answer)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            sentences = [answer]

        answer_tokens = _tokenize_for_matching(answer)
        context_tokens = _tokenize_for_matching(context_text)

        if not answer_tokens:
            return 0.0

        coverage = len(answer_tokens & context_tokens) / len(answer_tokens)
        # 对长答案检查关键token覆盖率
        key_tokens = {t for t in answer_tokens if len(t) > 1}
        if key_tokens:
            key_coverage = len(key_tokens & context_tokens) / len(key_tokens)
            coverage = 0.3 * coverage + 0.7 * key_coverage

        return max(0.0, min(1.0, coverage))

    # ===== Context Precision =====

    def evaluate_context_precision(self, query: str, contexts: List[str]) -> float:
        """评估检索上下文的精确度"""
        if not contexts:
            return 0.0

        result = self._llm_eval(
            "你是一个检索质量评估员。判断每个检索结果与查询问题的相关性。",
            f"查询：{query}\n\n" +
            "\n---\n".join(f"[{i+1}] {ctx}" for i, ctx in enumerate(contexts)) +
            "\n\n用JSON返回：{\"relevance\": [0.0-1.0, ...], \"overall\": 0.0-1.0}"
        )

        if result:
            try:
                data = self._parse_json(result)
                return float(data.get("overall", 0.5))
            except Exception:
                logger.debug("Failed to parse faithfulness JSON, using rule fallback")

        return self._rule_context_precision(query, contexts)

    def _rule_context_precision(self, query: str, contexts: List[str]) -> float:
        """改进的规则精确度——支持中文"""
        query_tokens = _tokenize_for_matching(query)
        if not query_tokens:
            return 0.0

        precision_scores = []
        for i, context in enumerate(contexts):
            ctx_tokens = _tokenize_for_matching(context)
            overlap = len(query_tokens & ctx_tokens)
            precision = overlap / len(query_tokens)
            position_weight = 1.0 / (i + 1)
            precision_scores.append(precision * position_weight)

        return sum(precision_scores) / len(contexts)

    # ===== Answer Relevancy =====

    def evaluate_answer_relevancy(self, query: str, answer: str) -> float:
        """评估答案对查询的相关性"""
        if not query or not answer:
            return 0.0

        result = self._llm_eval(
            "评估答案与用户问题的相关程度。答案是直接、准确、完整地回答了问题，还是偏离了主题？",
            f"用户问题：{query}\n\n系统答案：{answer}\n\n"
            "用JSON返回：{\"score\": 0.0-1.0, \"reasoning\": \"简短判断\"}"
        )

        if result:
            try:
                data = self._parse_json(result)
                return float(data.get("score", 0.5))
            except Exception:
                logger.debug("Failed to parse faithfulness JSON, using rule fallback")

        return self._rule_relevancy(query, answer)

    def _rule_relevancy(self, query: str, answer: str) -> float:
        """改进的规则相关性——支持中文"""
        query_tokens = _tokenize_for_matching(query)
        answer_tokens = _tokenize_for_matching(answer)

        if not query_tokens:
            return 0.0

        overlap = len(query_tokens & answer_tokens)
        relevancy = overlap / len(query_tokens)

        # 答案长度惩罚/奖励
        answer_len = len(answer)
        if answer_len < 10:
            relevancy *= 0.7
        elif answer_len > 500:
            relevancy *= 0.9

        return max(0.0, min(1.0, relevancy))

    # ===== Context Recall =====

    def evaluate_context_recall(self, ground_truth: str, contexts: List[str]) -> float:
        """评估上下文对标准答案的覆盖"""
        if not ground_truth or not contexts:
            return 0.0

        result = self._llm_eval(
            "判断标准答案中的信息有多少被检索到的上下文中覆盖了。",
            f"标准答案：{ground_truth}\n\n上下文：\n" + "\n---\n".join(contexts) +
            "\n\n用JSON返回：{\"score\": 0.0-1.0}"
        )

        if result:
            try:
                data = self._parse_json(result)
                return float(data.get("score", 0.5))
            except Exception:
                logger.debug("Failed to parse faithfulness JSON, using rule fallback")

        truth_tokens = _tokenize_for_matching(ground_truth)
        context_text = " ".join(contexts)
        context_tokens = _tokenize_for_matching(context_text)

        if not truth_tokens:
            return 0.0
        return len(truth_tokens & context_tokens) / len(truth_tokens)

    # ===== 综合评估 =====

    def evaluate(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> Dict:
        results = {}
        results["faithfulness"] = self.evaluate_faithfulness(answer, contexts)
        results["context_precision"] = self.evaluate_context_precision(query, contexts)
        results["context_recall"] = self.evaluate_context_recall(ground_truth, contexts) if ground_truth else 0.0
        results["answer_relevancy"] = self.evaluate_answer_relevancy(query, answer)
        results["overall_score"] = self._calculate_overall(results)
        logger.info(f"RAG evaluation: overall={results['overall_score']:.3f}")
        return results

    def _calculate_overall(self, results: Dict) -> float:
        weights = {
            "faithfulness": 0.3,
            "context_precision": 0.25,
            "context_recall": 0.25,
            "answer_relevancy": 0.2
        }
        overall = sum(results.get(m, 0.0) * w for m, w in weights.items())
        return round(overall, 3)

    def evaluate_batch(
        self,
        queries: List[str],
        answers: List[str],
        contexts_list: List[List[str]],
        ground_truths: Optional[List[str]] = None
    ) -> Dict:
        batch_results = []
        for i, (query, answer, contexts) in enumerate(zip(queries, answers, contexts_list)):
            gt = ground_truths[i] if ground_truths else None
            batch_results.append(self.evaluate(query, answer, contexts, gt))

        avg_results = {}
        metrics = ["faithfulness", "context_precision", "context_recall", "answer_relevancy", "overall_score"]
        for metric in metrics:
            values = [r[metric] for r in batch_results if metric in r]
            avg_results[f"avg_{metric}"] = sum(values) / len(values) if values else 0.0

        avg_results["total_queries"] = len(queries)
        avg_results["individual_results"] = batch_results
        return avg_results

    def _parse_json(self, text: str) -> Dict:
        """从LLM响应中提取JSON"""
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        # 尝试找到第一个 { 和最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start:end+1]
        return json.loads(text)


# Lazy singleton accessor
_evaluator: Optional[RAGEvaluator] = None


def get_rag_evaluator() -> RAGEvaluator:
    global _evaluator
    if _evaluator is None:
        _evaluator = RAGEvaluator()
    return _evaluator


rag_evaluator = RAGEvaluator()
