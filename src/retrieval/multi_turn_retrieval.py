"""
多轮检索策略

基于对话历史的上下文感知检索
"""
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class MultiTurnRetrieval:
    """多轮检索策略"""

    def __init__(self):
        """初始化多轮检索"""
        logger.info("Multi-turn retrieval initialized")

    def retrieve_with_context(
        self,
        query: str,
        session_id: str,
        conversation_manager,
        memory_manager,
        retriever
    ) -> List[Dict]:
        """
        基于上下文的检索

        Args:
            query: 当前查询
            session_id: 会话ID
            conversation_manager: 对话管理器
            memory_manager: 记忆管理器
            retriever: 检索器

        Returns:
            检索结果
        """
        # 获取对话历史
        conversation = conversation_manager.get_conversation(session_id)
        if not conversation:
            logger.warning(f"No conversation found: session_id={session_id}")
            return []

        # 获取最近上下文
        recent_context = memory_manager.get_recent_context(session_id, window_size=3)

        # 获取实体
        entities = memory_manager.extract_entities(session_id)

        # 扩展查询（结合上下文）
        expanded_query = self._expand_query_with_context(query, entities, recent_context)

        logger.info(f"Expanded query: {query} -> {expanded_query}")

        # 执行检索
        results = retriever.retrieve(expanded_query)

        # 重排序（基于上下文相关性）
        reranked_results = self._rerank_with_context(results, entities, recent_context)

        logger.info(f"Retrieved {len(reranked_results)} results with context")
        return reranked_results

    def _expand_query_with_context(
        self,
        query: str,
        entities: Dict,
        context: str
    ) -> str:
        """
        结合上下文扩展查询

        Args:
            query: 原始查询
            entities: 实体
            context: 上下文

        Returns:
            扩展后的查询
        """
        expanded = query

        # 补充产品型号
        if entities.get("products"):
            product = entities["products"][0]
            if product not in query:
                expanded = f"{product} {query}"

        # 补充故障代码
        if entities.get("faults"):
            fault = entities["faults"][0]
            if fault not in query:
                expanded = f"{fault} {expanded}"

        return expanded

    def _rerank_with_context(
        self,
        results: List[Dict],
        entities: Dict,
        context: str
    ) -> List[Dict]:
        """
        基于上下文重排序

        Args:
            results: 检索结果
            entities: 实体
            context: 上下文

        Returns:
            重排序后的结果
        """
        if not results:
            return results

        # 计算上下文相关性分数
        for result in results:
            context_score = 0.0

            # 检查实体匹配
            content = result.get("content", "")

            for product in entities.get("products", []):
                if product in content:
                    context_score += 0.3

            for fault in entities.get("faults", []):
                if fault in content:
                    context_score += 0.3

            # 更新分数
            original_score = result.get("score", 0.5)
            result["final_score"] = original_score * 0.7 + context_score * 0.3

        # 按最终分数排序
        reranked = sorted(results, key=lambda x: x.get("final_score", 0), reverse=True)

        return reranked

    def iterative_retrieval(
        self,
        query: str,
        session_id: str,
        memory_manager,
        retriever,
        max_iterations: int = 3
    ) -> List[Dict]:
        """
        迭代检索

        Args:
            query: 查询
            session_id: 会话ID
            memory_manager: 记忆管理器
            retriever: 检索器
            max_iterations: 最大迭代次数

        Returns:
            检索结果
        """
        all_results = []
        current_query = query

        for i in range(max_iterations):
            logger.info(f"Iteration {i+1}/{max_iterations}: query='{current_query}'")

            # 检索
            results = retriever.retrieve(current_query)

            if not results:
                break

            all_results.extend(results)

            # 检查是否找到足够结果
            if len(all_results) >= 10:
                break

            # 生成下一轮查询
            entities = memory_manager.extract_entities(session_id)
            current_query = self._refine_query(current_query, results, entities)

        # 去重
        unique_results = self._deduplicate(all_results)

        logger.info(f"Iterative retrieval: {len(unique_results)} unique results")
        return unique_results[:10]

    def _refine_query(self, query: str, results: List[Dict], entities: Dict) -> str:
        """
        改进查询

        Args:
            query: 原始查询
            results: 当前结果
            entities: 实体

        Returns:
            改进后的查询
        """
        # 简单策略：添加实体信息
        refined = query

        if entities.get("products"):
            product = entities["products"][0]
            if product not in query:
                refined = f"{product} {query}"

        return refined

    def _deduplicate(self, results: List[Dict]) -> List[Dict]:
        """
        去重

        Args:
            results: 结果列表

        Returns:
            去重后的结果
        """
        seen = set()
        unique = []

        for result in results:
            result_id = result.get("id")
            if result_id not in seen:
                seen.add(result_id)
                unique.append(result)

        return unique


# 全局实例
multi_turn_retrieval = MultiTurnRetrieval()
