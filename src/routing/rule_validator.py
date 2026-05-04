from typing import Dict, List, Tuple
from pydantic import BaseModel, Field, field_validator
import logging

logger = logging.getLogger(__name__)


class ProductSpecSchema(BaseModel):
    """产品规格校验Schema"""
    product_code: str = Field(..., pattern=r'^[A-Z]{2,5}-\d{3,5}$')
    name: str = Field(..., min_length=1, max_length=500)
    specifications: Dict = Field(default_factory=dict)

    @field_validator('product_code')
    @classmethod
    def validate_product_code(cls, v):
        """验证产品型号格式"""
        if not v or len(v) < 5:
            raise ValueError('产品型号格式错误')
        return v


class TroubleshootSchema(BaseModel):
    """故障排查校验Schema"""
    symptom: str = Field(..., min_length=1)
    possible_causes: List[str] = Field(..., min_length=1)
    recommended_solutions: List[Dict] = Field(..., min_length=1)


class CompatibilitySchema(BaseModel):
    """兼容性校验Schema"""
    product_a: str = Field(..., min_length=1)
    product_b: str = Field(..., min_length=1)
    compatibility_type: str = Field(..., pattern=r'^(compatible|upgrade|replace)$')


class RuleValidator:
    """规则校验引擎"""

    SCHEMAS = {
        "spec": ProductSpecSchema,
        "troubleshoot": TroubleshootSchema,
        "compatibility": CompatibilitySchema
    }

    def validate(self, intent: str, data: Dict) -> Tuple[bool, List[str]]:
        """校验数据"""
        schema_class = self.SCHEMAS.get(intent)

        if not schema_class:
            logger.warning(f"未知意图类型: {intent}")
            return True, []

        try:
            schema_class(**data)
            logger.info(f"规则校验通过: intent={intent}")
            return True, []
        except Exception as e:
            errors = [str(e)]
            logger.warning(f"规则校验失败: {errors}")
            return False, errors