"""Data Source Factory

파일 기반과 DB 기반 데이터 소스를 설정에 따라 생성
점진적 마이그레이션을 지원하는 팩토리 패턴
"""
import logging
from typing import Optional, Dict, Any, Union
from pathlib import Path
from enum import Enum

from .data_source import DataSource, FileDataSource
try:
    from .data_source import DatabaseDataSource
    from .connection_pool import db_pool
    HAS_DB = True
except (ImportError, RuntimeError):
    DatabaseDataSource = None
    db_pool = None
    HAS_DB = False

logger = logging.getLogger(__name__)


class DataSourceMode(Enum):
    """데이터 소스 모드"""
    FILE = "file"           # 파일만 사용
    DATABASE = "database"   # DB만 사용
    HYBRID = "hybrid"       # 파일과 DB 병행 (마이그레이션 중)


class HybridDataSource(DataSource):
    """하이브리드 데이터 소스
    
    파일과 DB를 병행하여 사용
    - 읽기: DB 우선, 실패시 파일 폴백
    - 쓰기: 파일과 DB 모두 저장
    """
    
    def __init__(self, file_source: FileDataSource, db_source: DatabaseDataSource):
        self.file_source = file_source
        self.db_source = db_source
        logger.info("하이브리드 데이터 소스 초기화 (파일 + DB)")
    
    def get_reviews_by_category(self, category: str, vendor: Optional[str] = None, limit: Optional[int] = None):
        """DB 우선, 실패시 파일"""
        try:
            df = self.db_source.get_reviews_by_category(category, vendor, limit)
            if not df.empty:
                logger.debug(f"리뷰 조회 성공 (DB): category={category}")
                return df
        except Exception as e:
            logger.warning(f"DB 조회 실패, 파일로 폴백: {e}")
        
        logger.debug(f"리뷰 조회 (파일): category={category}")
        return self.file_source.get_reviews_by_category(category, vendor, limit)
    
    def get_reviews_by_product(self, product_id: str, vendor: Optional[str] = None, limit: Optional[int] = None):
        """DB 우선, 실패시 파일"""
        try:
            df = self.db_source.get_reviews_by_product(product_id, vendor, limit)
            if not df.empty:
                logger.debug(f"리뷰 조회 성공 (DB): product_id={product_id}")
                return df
        except Exception as e:
            logger.warning(f"DB 조회 실패, 파일로 폴백: {e}")
        
        logger.debug(f"리뷰 조회 (파일): product_id={product_id}")
        return self.file_source.get_reviews_by_product(product_id, vendor, limit)
    
    def get_factors_by_category(self, category: str, version: Optional[str] = None):
        """DB 우선, 실패시 파일"""
        try:
            df = self.db_source.get_factors_by_category(category, version)
            if not df.empty:
                logger.debug(f"요인 조회 성공 (DB): category={category}")
                return df
        except Exception as e:
            logger.warning(f"DB 조회 실패, 파일로 폴백: {e}")
        
        logger.debug(f"요인 조회 (파일): category={category}")
        return self.file_source.get_factors_by_category(category, version)
    
    def get_questions_by_category(self, category: str, version: Optional[str] = None):
        """DB 우선, 실패시 파일"""
        try:
            df = self.db_source.get_questions_by_category(category, version)
            if not df.empty:
                logger.debug(f"질문 조회 성공 (DB): category={category}")
                return df
        except Exception as e:
            logger.warning(f"DB 조회 실패, 파일로 폴백: {e}")
        
        logger.debug(f"질문 조회 (파일): category={category}")
        return self.file_source.get_questions_by_category(category, version)
    
    def save_reviews(self, reviews_df, metadata: Dict[str, Any]) -> bool:
        """파일과 DB 모두 저장"""
        file_ok = self.file_source.save_reviews(reviews_df, metadata)
        db_ok = self.db_source.save_reviews(reviews_df, metadata)
        
        if file_ok and db_ok:
            logger.info("리뷰 저장 성공 (파일 + DB)")
            return True
        elif file_ok or db_ok:
            logger.warning(f"리뷰 부분 저장: 파일={file_ok}, DB={db_ok}")
            return True
        else:
            logger.error("리뷰 저장 실패 (파일 + DB)")
            return False
    
    def save_analysis_result(self, session_id: str, result_data: Dict[str, Any]) -> bool:
        """파일과 DB 모두 저장"""
        file_ok = self.file_source.save_analysis_result(session_id, result_data)
        db_ok = self.db_source.save_analysis_result(session_id, result_data)
        
        if file_ok and db_ok:
            logger.info("분석 결과 저장 성공 (파일 + DB)")
            return True
        elif file_ok or db_ok:
            logger.warning(f"분석 결과 부분 저장: 파일={file_ok}, DB={db_ok}")
            return True
        else:
            logger.error("분석 결과 저장 실패 (파일 + DB)")
            return False
    
    def health_check(self) -> bool:
        """파일 또는 DB 중 하나라도 정상이면 OK"""
        file_ok = self.file_source.health_check()
        db_ok = self.db_source.health_check()
        
        logger.info(f"헬스체크: 파일={file_ok}, DB={db_ok}")
        return file_ok or db_ok


class DataSourceFactory:
    """데이터 소스 팩토리
    
    설정에 따라 적절한 데이터 소스 인스턴스 생성
    """
    
    @staticmethod
    def create(
        mode: Union[str, DataSourceMode] = DataSourceMode.FILE,
        data_dir: Optional[Union[str, Path]] = None,
        file_format: str = "json",
        db_config: Optional[Dict[str, Any]] = None
    ) -> DataSource:
        """데이터 소스 생성
        
        Args:
            mode: 데이터 소스 모드 ("file", "database", "hybrid")
            data_dir: 파일 데이터 디렉토리 (파일 모드에 필요)
            file_format: 파일 포맷 ("json" or "csv")
            db_config: DB 설정 (DB 모드에 필요)
                {
                    "host": "localhost",
                    "port": 5432,
                    "database": "reviewlens",
                    "user": "reviewlens",
                    "password": "reviewlens",
                    "min_size": 2,
                    "max_size": 10
                }
        
        Returns:
            DataSource 인스턴스
        """
        if isinstance(mode, str):
            mode = DataSourceMode(mode.lower())
        
        logger.info(f"데이터 소스 생성: mode={mode.value}")
        
        if mode == DataSourceMode.FILE:
            if not data_dir:
                raise ValueError("파일 모드에는 data_dir이 필요합니다")
            return FileDataSource(data_dir=data_dir, file_format=file_format)
        
        elif mode == DataSourceMode.DATABASE:
            if not HAS_DB:
                raise RuntimeError(
                    "DB 모드를 사용하려면 psycopg가 필요합니다. "
                    "설치: pip install 'psycopg[pool]' 또는 psycopg2-binary"
                )
            
            if not db_config:
                raise ValueError("DB 모드에는 db_config가 필요합니다")
            
            # DB 컨넥션 풀 초기화
            if not db_pool._pool:
                db_pool.initialize(**db_config)
            
            return DatabaseDataSource(connection_pool=db_pool)
        
        elif mode == DataSourceMode.HYBRID:
            if not data_dir or not db_config:
                raise ValueError("하이브리드 모드에는 data_dir과 db_config가 모두 필요합니다")
            
            # 파일 소스 생성
            file_source = FileDataSource(data_dir=data_dir, file_format=file_format)
            
            # DB 소스 생성 (psycopg 필요)
            if not HAS_DB:
                logger.warning(
                    "하이브리드 모드: psycopg 없음, 파일 모드로 폴백됩니다. "
                    "DB 기능을 사용하려면 pip install 'psycopg[pool]'"
                )
                return file_source
            
            if not db_pool._pool:
                db_pool.initialize(**db_config)
            db_source = DatabaseDataSource(connection_pool=db_pool)
            
            # 하이브리드 소스 생성
            return HybridDataSource(file_source=file_source, db_source=db_source)
        
        else:
            raise ValueError(f"알 수 없는 데이터 소스 모드: {mode}")
    
    @staticmethod
    def create_from_env() -> DataSource:
        """환경 변수에서 설정 읽어서 생성
        
        .env 파일 또는 환경 변수:
            - DATA_SOURCE_MODE: "file", "database", "hybrid"
            - DATA_DIR: 파일 데이터 디렉토리
            - FILE_FORMAT: "json" or "csv"
            - DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
            - DB_POOL_MIN_SIZE, DB_POOL_MAX_SIZE
        """
        import os
        
        mode = os.getenv("DATA_SOURCE_MODE", "file")
        data_dir = os.getenv("DATA_DIR", "backend/data")
        file_format = os.getenv("FILE_FORMAT", "json")
        
        db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "reviewlens"),
            "user": os.getenv("DB_USER", "reviewlens"),
            "password": os.getenv("DB_PASSWORD", "reviewlens"),
            "min_size": int(os.getenv("DB_POOL_MIN_SIZE", "2")),
            "max_size": int(os.getenv("DB_POOL_MAX_SIZE", "10"))
        }
        
        return DataSourceFactory.create(
            mode=mode,
            data_dir=data_dir,
            file_format=file_format,
            db_config=db_config if mode in ["database", "hybrid"] else None
        )
    
    @staticmethod
    def create_from_settings() -> DataSource:
        """Settings 객체에서 설정 읽어서 생성
        
        backend/app/core/settings.py의 Settings 클래스 사용
        .env 파일에서 자동으로 설정 로드
        
        Returns:
            DataSource 인스턴스
        """
        from ...core.settings import settings
        
        db_config = None
        if settings.DATA_SOURCE_MODE in ["database", "hybrid"]:
            db_config = {
                "host": settings.DB_HOST,
                "port": settings.DB_PORT,
                "database": settings.DB_NAME,
                "user": settings.DB_USER,
                "password": settings.DB_PASSWORD,
                "min_size": settings.DB_POOL_MIN_SIZE,
                "max_size": settings.DB_POOL_MAX_SIZE,
                "timeout": settings.DB_TIMEOUT,
                "max_idle": settings.DB_MAX_IDLE
            }
        
        return DataSourceFactory.create(
            mode=settings.DATA_SOURCE_MODE,
            data_dir=settings.DATA_DIR,
            file_format=settings.REVIEW_FILE_FORMAT,
            db_config=db_config
        )


# 싱글톤 패턴으로 전역 데이터 소스 관리
_global_data_source: Optional[DataSource] = None


def get_data_source(use_settings: bool = True) -> DataSource:
    """전역 데이터 소스 가져오기
    
    Args:
        use_settings: True이면 Settings 사용 (권장), False이면 환경 변수 직접 사용
    
    Returns:
        DataSource 인스턴스
    """
    global _global_data_source
    
    if _global_data_source is None:
        if use_settings:
            logger.info("전역 데이터 소스 초기화 (Settings 기반)")
            _global_data_source = DataSourceFactory.create_from_settings()
        else:
            logger.info("전역 데이터 소스 초기화 (환경 변수 기반)")
            _global_data_source = DataSourceFactory.create_from_env()
    
    return _global_data_source


def set_data_source(data_source: DataSource) -> None:
    """전역 데이터 소스 설정
    
    테스트나 특정 상황에서 데이터 소스를 직접 설정할 때 사용
    
    Args:
        data_source: DataSource 인스턴스
    """
    global _global_data_source
    _global_data_source = data_source
    logger.info(f"전역 데이터 소스 설정: {type(data_source).__name__}")
