"""
降级和澄清处理器

处理规则校验失败的情况
"""
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class FallbackHandler:
    """降级和澄清处理器"""

    def handle_validation_failure(self, query: str, errors: List[str]) -> Dict:
        """
        处理规则校验失败

        Args:
            query: 用户查询
            errors: 错误列表

        Returns:
            处理结果
        """
        # 1. 尝试澄清（缺少必要信息）
        if any('缺少' in err or '不存在' in err for err in errors):
            clarification = self._generate_clarification(query, errors)
            return {
                "status": "clarify",
                "message": clarification,
                "missing_info": errors
            }

        # 2. 转人工（复杂业务规则失败）
        if any('版本' in err or '兼容' in err for err in errors):
            return {
                "status": "escalate",
                "message": "该问题需要人工审核，已转交技术支持团队",
                "reason": errors
            }

        # 3. 默认降级
        return {
            "status": "fallback",
            "message": "无法提供准确答案，建议联系技术支持",
            "errors": errors
        }

    def _generate_clarification(self, query: str, errors: List[str]) -> str:
        """生成澄清问题"""
        if '产品型号' in str(errors):
            return "请提供具体的产品型号（格式：XX-000）"
        elif '版本' in str(errors):
            return "请提供产品的版本号（格式：v1.0）"
        else:
            return "请补充更多详细信息以便准确回答"


# 全局实例
fallback_handler = FallbackHandler()