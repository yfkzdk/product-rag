from fastapi import Request, status
from fastapi.responses import JSONResponse
from src.exceptions import ProductKGError
import logging

logger = logging.getLogger(__name__)


async def error_handler_middleware(request: Request, call_next):
    """错误处理中间件"""
    try:
        return await call_next(request)

    except ProductKGError as e:
        logger.error(f"业务错误: {e.code} - {e.message}", extra=e.details)

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "details": e.details
                }
            }
        )

    except Exception as e:
        logger.exception(f"系统错误: {str(e)}")

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "系统内部错误",
                    "details": {}
                }
            }
        )