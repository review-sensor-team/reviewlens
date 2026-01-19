"""Database Configuration Manager

DB 설정을 중앙에서 관리하고 검증
"""
import logging
from typing import Optional, Dict, Any, Union
from pathlib import Path
from dataclasses import dataclass, field
import os

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """PostgreSQL 데이터베이스 설정"""
    
    # 연결 정보
    host: str = "localhost"
    port: int = 5432
    database: str = "reviewlens"
    user: str = "reviewlens"
    password: str = "reviewlens"
    
    # 컨넥션 풀 설정
    min_size: int = 2
    max_size: int = 10
    timeout: float = 30.0
    max_idle: float = 600.0
    
    # 추가 옵션
    options: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """환경 변수에서 설정 로드
        
        .env 파일 또는 환경 변수:
            - DB_HOST (default: localhost)
            - DB_PORT (default: 5432)
            - DB_NAME (default: reviewlens)
            - DB_USER (default: reviewlens)
            - DB_PASSWORD (default: reviewlens)
            - DB_POOL_MIN_SIZE (default: 2)
            - DB_POOL_MAX_SIZE (default: 10)
            - DB_TIMEOUT (default: 30.0)
            - DB_MAX_IDLE (default: 600.0)
        """
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "reviewlens"),
            user=os.getenv("DB_USER", "reviewlens"),
            password=os.getenv("DB_PASSWORD", "reviewlens"),
            min_size=int(os.getenv("DB_POOL_MIN_SIZE", "2")),
            max_size=int(os.getenv("DB_POOL_MAX_SIZE", "10")),
            timeout=float(os.getenv("DB_TIMEOUT", "30.0")),
            max_idle=float(os.getenv("DB_MAX_IDLE", "600.0"))
        )
    
    @classmethod
    def from_settings(cls) -> 'DatabaseConfig':
        """Settings 객체에서 설정 로드
        
        Returns:
            DatabaseConfig 인스턴스
        """
        from ...core.settings import settings
        
        return cls(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            min_size=settings.DB_POOL_MIN_SIZE,
            max_size=settings.DB_POOL_MAX_SIZE,
            timeout=settings.DB_TIMEOUT,
            max_idle=settings.DB_MAX_IDLE
        )
    
    @classmethod
    def from_docker_compose(cls) -> 'DatabaseConfig':
        """Docker Compose 환경용 기본 설정"""
        return cls(
            host=os.getenv("DB_HOST", "postgres"),  # Docker service name
            port=5432,
            database="reviewlens",
            user="reviewlens",
            password="reviewlens_dev_password",
            min_size=2,
            max_size=10
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": self.password,
            "min_size": self.min_size,
            "max_size": self.max_size,
            "timeout": self.timeout,
            "max_idle": self.max_idle,
            **self.options
        }
    
    def validate(self) -> bool:
        """설정 검증
        
        Returns:
            True: 정상, False: 오류
        """
        errors = []
        
        if not self.host:
            errors.append("host가 비어있습니다")
        
        if self.port < 1 or self.port > 65535:
            errors.append(f"잘못된 port: {self.port}")
        
        if not self.database:
            errors.append("database가 비어있습니다")
        
        if not self.user:
            errors.append("user가 비어있습니다")
        
        if not self.password:
            errors.append("password가 비어있습니다")
        
        if self.min_size < 1:
            errors.append(f"min_size는 1 이상이어야 합니다: {self.min_size}")
        
        if self.max_size < self.min_size:
            errors.append(f"max_size({self.max_size})는 min_size({self.min_size}) 이상이어야 합니다")
        
        if errors:
            for error in errors:
                logger.error(f"DB 설정 오류: {error}")
            return False
        
        return True
    
    def get_connection_string(self, hide_password: bool = True) -> str:
        """연결 문자열 생성
        
        Args:
            hide_password: True이면 비밀번호 숨김
            
        Returns:
            PostgreSQL 연결 문자열
        """
        pwd = "****" if hide_password else self.password
        return f"postgresql://{self.user}:{pwd}@{self.host}:{self.port}/{self.database}"


@dataclass
class DataSourceConfig:
    """데이터 소스 설정"""
    
    # 데이터 소스 모드
    mode: str = "file"  # "file", "database", "hybrid"
    
    # 파일 기반 설정
    data_dir: str = "backend/data"
    file_format: str = "json"  # "json" or "csv"
    
    # DB 기반 설정
    db_config: Optional[DatabaseConfig] = None
    
    @classmethod
    def from_env(cls) -> 'DataSourceConfig':
        """환경 변수에서 설정 로드
        
        .env 파일 또는 환경 변수:
            - DATA_SOURCE_MODE (default: file)
            - DATA_DIR (default: backend/data)
            - FILE_FORMAT (default: json)
            - DB_* (DatabaseConfig 참조)
        """
        mode = os.getenv("DATA_SOURCE_MODE", "file").lower()
        
        # DB 모드일 경우 DB 설정 로드
        db_config = None
        if mode in ["database", "hybrid"]:
            db_config = DatabaseConfig.from_env()
        
        return cls(
            mode=mode,
            data_dir=os.getenv("DATA_DIR", "backend/data"),
            file_format=os.getenv("FILE_FORMAT", "json"),
            db_config=db_config
        )
    
    @classmethod
    def from_settings(cls) -> 'DataSourceConfig':
        """Settings 객체에서 설정 로드
        
        Returns:
            DataSourceConfig 인스턴스
        """
        from ...core.settings import settings
        
        # DB 모드일 경우 DB 설정 로드
        db_config = None
        if settings.DATA_SOURCE_MODE in ["database", "hybrid"]:
            db_config = DatabaseConfig.from_settings()
        
        return cls(
            mode=settings.DATA_SOURCE_MODE,
            data_dir=settings.DATA_DIR,
            file_format=settings.REVIEW_FILE_FORMAT,
            db_config=db_config
        )
    
    def validate(self) -> bool:
        """설정 검증
        
        Returns:
            True: 정상, False: 오류
        """
        if self.mode not in ["file", "database", "hybrid"]:
            logger.error(f"잘못된 데이터 소스 모드: {self.mode}")
            return False
        
        if self.mode in ["file", "hybrid"]:
            data_path = Path(self.data_dir)
            if not data_path.exists():
                logger.warning(f"데이터 디렉토리가 없습니다: {self.data_dir}")
                # 생성 시도
                try:
                    data_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"데이터 디렉토리 생성: {self.data_dir}")
                except Exception as e:
                    logger.error(f"데이터 디렉토리 생성 실패: {e}")
                    return False
        
        if self.mode in ["database", "hybrid"]:
            if not self.db_config:
                logger.error("DB 설정이 필요합니다")
                return False
            
            if not self.db_config.validate():
                return False
        
        return True
    
    def get_summary(self) -> str:
        """설정 요약
        
        Returns:
            설정 요약 문자열
        """
        lines = [
            f"데이터 소스 모드: {self.mode}",
        ]
        
        if self.mode in ["file", "hybrid"]:
            lines.append(f"파일 디렉토리: {self.data_dir}")
            lines.append(f"파일 포맷: {self.file_format}")
        
        if self.mode in ["database", "hybrid"] and self.db_config:
            lines.append(f"DB 연결: {self.db_config.get_connection_string()}")
            lines.append(f"컨넥션 풀: {self.db_config.min_size}~{self.db_config.max_size}")
        
        return "\n".join(lines)


def load_config(use_settings: bool = True) -> DataSourceConfig:
    """설정 로드 및 검증
    
    Args:
        use_settings: True이면 Settings 사용, False이면 환경 변수 직접 사용
    
    Returns:
        검증된 DataSourceConfig
        
    Raises:
        ValueError: 설정 검증 실패
    """
    if use_settings:
        config = DataSourceConfig.from_settings()
    else:
        config = DataSourceConfig.from_env()
    
    if not config.validate():
        raise ValueError("데이터 소스 설정 검증 실패")
    
    logger.info("데이터 소스 설정 로드 완료:\n" + config.get_summary())
    return config
