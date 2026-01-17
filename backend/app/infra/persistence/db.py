"""데이터베이스 연결 (미래 확장용)"""
import logging

logger = logging.getLogger(__name__)


class Database:
    """데이터베이스 연결 관리"""
    
    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string
        self._connection = None
    
    async def connect(self):
        """DB 연결"""
        logger.info("DB 연결 (현재는 파일 기반)")
        pass
    
    async def disconnect(self):
        """DB 연결 해제"""
        logger.info("DB 연결 해제")
        pass
