from typing import Any, Optional


class ProductKGError(Exception):
    """基础异常类"""

    def __init__(self, message: str, code: str, details: Optional[dict] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class ProductNotFoundError(ProductKGError):
    """产品不存在"""

    def __init__(self, product_code: str):
        super().__init__(
            message=f"产品不存在: {product_code}",
            code="PRODUCT_NOT_FOUND",
            details={"product_code": product_code}
        )


class FaultNotFoundError(ProductKGError):
    """故障不存在"""

    def __init__(self, fault_code: str):
        super().__init__(
            message=f"故障不存在: {fault_code}",
            code="FAULT_NOT_FOUND",
            details={"fault_code": fault_code}
        )


class ValidationError(ProductKGError):
    """校验错误"""

    def __init__(self, message: str, field: str, value: Any = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"field": field, "value": str(value)}
        )


class RetrievalError(ProductKGError):
    """检索错误"""

    def __init__(self, message: str, engine: str):
        super().__init__(
            message=message,
            code="RETRIEVAL_ERROR",
            details={"engine": engine}
        )


class GenerationError(ProductKGError):
    """生成错误"""

    def __init__(self, message: str, model: str):
        super().__init__(
            message=message,
            code="GENERATION_ERROR",
            details={"model": model}
        )


class FallbackError(ProductKGError):
    """降级错误"""

    def __init__(self, message: str, reason: str):
        super().__init__(
            message=message,
            code="FALLBACK_ERROR",
            details={"reason": reason}
        )


class DatabaseError(ProductKGError):
    """数据库错误"""

    def __init__(self, message: str, operation: str):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            details={"operation": operation}
        )


class CacheError(ProductKGError):
    """缓存错误"""

    def __init__(self, message: str, operation: str):
        super().__init__(
            message=message,
            code="CACHE_ERROR",
            details={"operation": operation}
        )