"""Database Infrastructure

DB 컨넥션 풀과 데이터 소스 관리

주요 컴포넌트:
- DatabaseConnectionPool: PostgreSQL 컨넥션 풀 관리
- DataSource: 파일/DB 데이터 소스 추상화
- DataSourceFactory: 설정 기반 데이터 소스 생성
- DatabaseConfig, DataSourceConfig: 설정 관리

사용 예시:
    # 1. 환경 변수 기반 자동 설정
    from backend.app.infra.database import get_data_source
    
    data_source = get_data_source()
    reviews_df = data_source.get_reviews_by_category("coffee_machine")
    
    # 2. 명시적 설정
    from backend.app.infra.database import DataSourceFactory
    
    data_source = DataSourceFactory.create(
        mode="hybrid",  # 파일과 DB 병행
        data_dir="backend/data",
        db_config={
            "host": "localhost",
            "database": "reviewlens",
            "user": "reviewlens",
            "password": "reviewlens"
        }
    )
"""

# 조건부 import (파일 모드에서는 psycopg 불필요)
try:
    from .connection_pool import DatabaseConnectionPool, db_pool
    _DB_AVAILABLE = True
except ImportError:
    DatabaseConnectionPool = None
    db_pool = None
    _DB_AVAILABLE = False

from .data_source import DataSource, FileDataSource
try:
    from .data_source import DatabaseDataSource
except (ImportError, RuntimeError):
    DatabaseDataSource = None
from .factory import DataSourceFactory, DataSourceMode, get_data_source, set_data_source
from .config import DatabaseConfig, DataSourceConfig, load_config

__all__ = [
    # Connection Pool (DB 모드에서만 사용)
    "DatabaseConnectionPool",
    "db_pool",
    
    # Data Sources
    "DataSource",
    "FileDataSource", 
    "DatabaseDataSource",
    
    # Factory
    "DataSourceFactory",
    "DataSourceMode",
    "get_data_source",
    "set_data_source",
    
    # Config
    "DatabaseConfig",
    "DataSourceConfig",
    "load_config",
]
