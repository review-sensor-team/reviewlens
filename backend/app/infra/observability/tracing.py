"""분산 트레이싱 (미래 확장용)"""
import logging
from functools import wraps
import time

logger = logging.getLogger(__name__)


def trace(operation_name: str):
    """함수 실행 트레이싱 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            logger.debug(f"[TRACE] START: {operation_name}")
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start
                logger.debug(f"[TRACE] END: {operation_name} ({duration:.3f}s)")
                return result
            except Exception as e:
                duration = time.time() - start
                logger.error(f"[TRACE] ERROR: {operation_name} ({duration:.3f}s) - {e}")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            logger.debug(f"[TRACE] START: {operation_name}")
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                logger.debug(f"[TRACE] END: {operation_name} ({duration:.3f}s)")
                return result
            except Exception as e:
                duration = time.time() - start
                logger.error(f"[TRACE] ERROR: {operation_name} ({duration:.3f}s) - {e}")
                raise
        
        if hasattr(func, '__await__'):
            return async_wrapper
        return sync_wrapper
    
    return decorator
