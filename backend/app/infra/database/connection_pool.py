"""PostgreSQL Connection Pool

안정적인 DB 마이그레이션을 위한 컨넥션 풀 관리
- psycopg3의 ConnectionPool 사용
- 컨텍스트 관리자로 안전한 커넥션 사용
- 설정 기반 풀 크기 및 타임아웃 관리
"""
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager
import psycopg
from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)


class DatabaseConnectionPool:
    """PostgreSQL 컨넥션 풀 관리자
    
    싱글톤 패턴으로 애플리케이션 전체에서 하나의 풀만 유지
    """
    
    _instance: Optional['DatabaseConnectionPool'] = None
    _pool: Optional[ConnectionPool] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "reviewlens",
        user: str = "reviewlens",
        password: str = "reviewlens",
        min_size: int = 2,
        max_size: int = 10,
        timeout: float = 30.0,
        max_idle: float = 600.0,
        **kwargs
    ) -> None:
        """컨넥션 풀 초기화
        
        Args:
            host: DB 호스트
            port: DB 포트
            database: 데이터베이스명
            user: 사용자명
            password: 비밀번호
            min_size: 최소 컨넥션 수
            max_size: 최대 컨넥션 수
            timeout: 컨넥션 획득 타임아웃 (초)
            max_idle: 유휴 컨넥션 최대 유지 시간 (초)
            **kwargs: 추가 psycopg 연결 옵션
        """
        if self._pool is not None:
            logger.warning("컨넥션 풀이 이미 초기화되어 있습니다. 재초기화합니다.")
            self.close()
        
        conninfo = (
            f"host={host} port={port} dbname={database} "
            f"user={user} password={password}"
        )
        
        # 추가 옵션 처리
        for key, value in kwargs.items():
            conninfo += f" {key}={value}"
        
        try:
            self._pool = ConnectionPool(
                conninfo=conninfo,
                min_size=min_size,
                max_size=max_size,
                timeout=timeout,
                max_idle=max_idle,
                kwargs={
                    "autocommit": False,  # 명시적 트랜잭션 관리
                    "row_factory": psycopg.rows.dict_row  # dict 형태로 결과 반환
                }
            )
            logger.info(
                f"DB 컨넥션 풀 초기화: {database}@{host}:{port} "
                f"(min={min_size}, max={max_size})"
            )
        except Exception as e:
            logger.error(f"DB 컨넥션 풀 초기화 실패: {e}", exc_info=True)
            raise
    
    @contextmanager
    def get_connection(self):
        """컨넥션 획득 (컨텍스트 관리자)
        
        Yields:
            psycopg.Connection: DB 컨넥션
            
        Example:
            with pool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM review LIMIT 10")
                    rows = cur.fetchall()
        """
        if self._pool is None:
            raise RuntimeError("컨넥션 풀이 초기화되지 않았습니다. initialize()를 먼저 호출하세요.")
        
        conn = None
        try:
            conn = self._pool.getconn()
            logger.debug(f"컨넥션 획득: {id(conn)}")
            yield conn
        except Exception as e:
            logger.error(f"컨넥션 사용 중 오류: {e}", exc_info=True)
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                logger.debug(f"컨넥션 반환: {id(conn)}")
                self._pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, commit: bool = False):
        """커서 획득 (컨텍스트 관리자)
        
        Args:
            commit: True이면 자동 커밋, False이면 명시적 커밋 필요
            
        Yields:
            psycopg.Cursor: DB 커서
            
        Example:
            with pool.get_cursor(commit=True) as cur:
                cur.execute("INSERT INTO review (...) VALUES (...)")
        """
        with self.get_connection() as conn:
            cursor = None
            try:
                cursor = conn.cursor()
                yield cursor
                if commit:
                    conn.commit()
            except Exception as e:
                logger.error(f"쿼리 실행 중 오류: {e}", exc_info=True)
                conn.rollback()
                raise
            finally:
                if cursor:
                    cursor.close()
    
    def execute_query(
        self,
        query: str,
        params: Optional[tuple | dict] = None,
        fetch: str = "all"
    ) -> Optional[list[Dict[str, Any]]]:
        """쿼리 실행 헬퍼
        
        Args:
            query: SQL 쿼리
            params: 쿼리 파라미터
            fetch: "all", "one", "none"
            
        Returns:
            쿼리 결과 (fetch="none"이면 None)
        """
        with self.get_cursor(commit=(fetch == "none")) as cur:
            cur.execute(query, params)
            
            if fetch == "all":
                return cur.fetchall()
            elif fetch == "one":
                result = cur.fetchone()
                return [result] if result else []
            else:
                return None
    
    def health_check(self) -> bool:
        """DB 연결 상태 확인
        
        Returns:
            True: 정상, False: 오류
        """
        try:
            result = self.execute_query("SELECT 1 AS health", fetch="one")
            return result is not None and len(result) > 0
        except Exception as e:
            logger.error(f"DB 헬스체크 실패: {e}", exc_info=True)
            return False
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """컨넥션 풀 통계
        
        Returns:
            풀 통계 정보
        """
        if self._pool is None:
            return {"status": "not_initialized"}
        
        try:
            pool = self._pool
            return {
                "status": "active",
                "size": pool.get_stats()["pool_size"],
                "available": pool.get_stats()["pool_available"],
                "waiting": pool.get_stats()["requests_waiting"]
            }
        except Exception as e:
            logger.error(f"풀 통계 조회 실패: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    def close(self) -> None:
        """컨넥션 풀 종료"""
        if self._pool is not None:
            logger.info("컨넥션 풀 종료 중...")
            self._pool.close()
            self._pool = None
            logger.info("컨넥션 풀 종료 완료")
    
    def __del__(self):
        """소멸자 - 풀 자동 종료"""
        self.close()


# 싱글톤 인스턴스
db_pool = DatabaseConnectionPool()
