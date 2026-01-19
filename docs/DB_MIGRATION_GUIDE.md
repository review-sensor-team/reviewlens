# 데이터베이스 마이그레이션 가이드

## 개요

ReviewLens의 안정적인 DB 마이그레이션을 위한 가이드입니다.

## 생성된 파일

### 1. 핵심 모듈
- `backend/app/infra/database/connection_pool.py`: PostgreSQL 컨넥션 풀 관리
- `backend/app/infra/database/data_source.py`: 데이터 소스 추상화 (파일/DB)
- `backend/app/infra/database/factory.py`: 데이터 소스 팩토리 (파일/DB/하이브리드 전환)
- `backend/app/infra/database/config.py`: DB 설정 관리
- `backend/app/infra/database/__init__.py`: 모듈 진입점

### 2. 설정 및 문서
- `docker-compose.db.yml`: PostgreSQL + pgAdmin Docker 설정
- `db_start.sh`: DB 시작 스크립트
- `db_stop.sh`: DB 종료 스크립트
- `backend/app/infra/database/README.md`: 상세 사용 가이드
- `backend/app/infra/database/example_usage.py`: 사용 예시 코드

## 주요 기능

### 1. 컨넥션 풀 관리
```python
from backend.app.infra.database import db_pool

# 초기화
db_pool.initialize(
    host="localhost",
    database="reviewlens",
    user="reviewlens",
    password="reviewlens",
    min_size=2,
    max_size=10
)

# 헬스체크
if db_pool.health_check():
    print("DB 연결 정상")

# 쿼리 실행
results = db_pool.execute_query(
    "SELECT * FROM review LIMIT 10",
    fetch="all"
)
```

### 2. 데이터 소스 추상화

#### 파일 모드 (기존)
```python
from backend.app.infra.database import DataSourceFactory

data_source = DataSourceFactory.create(
    mode="file",
    data_dir="backend/data",
    file_format="json"
)
```

#### DB 모드 (마이그레이션 완료)
```python
data_source = DataSourceFactory.create(
    mode="database",
    db_config={
        "host": "localhost",
        "database": "reviewlens",
        "user": "reviewlens",
        "password": "reviewlens"
    }
)
```

#### 하이브리드 모드 (마이그레이션 중)
```python
data_source = DataSourceFactory.create(
    mode="hybrid",
    data_dir="backend/data",
    db_config={
        "host": "localhost",
        "database": "reviewlens",
        "user": "reviewlens",
        "password": "reviewlens"
    }
)
# 읽기: DB 우선, 실패시 파일 폴백
# 쓰기: 파일과 DB 모두 저장
```

### 3. 환경 변수 기반 자동 설정

**권장: `.env` 파일 사용**

프로젝트 루트의 `.env` 파일에 설정:
```bash
# Settings를 통해 자동으로 로드됨
DATA_SOURCE_MODE=hybrid
DATA_DIR=backend/data

DB_HOST=localhost
DB_NAME=reviewlens
DB_USER=reviewlens
DB_PASSWORD=reviewlens
```

코드에서 사용:
```python
from backend.app.infra.database import get_data_source

# Settings(.env)에서 자동 로드 (권장)
data_source = get_data_source()

# 또는 환경 변수 직접 사용 (레거시)
# data_source = get_data_source(use_settings=False)
``.env 파일 수정
# DATA_SOURCE_MODE=file
DATA_SOURCE_MODE=hybrid

# 애플리케이션 재시작 (새 데이터는 파일+DB 모두 저장)
```

Settings는 자동으로 `.env` 파일을 읽어서 적용합니다.. 스키마 생성 확인
docker exec reviewlens-postgres psql -U reviewlens -d reviewlens -c "\dt"

# 3. 연결 테스트
python -c "from backend.app.infra.database import db_pool; db_pool.initialize(); print('OK' if db_pool.health_check() else 'FAIL')"
```

### Phase 2: 하이브리드 모드 전환
```bash
# 환경 변수 설정
export DATA_SOURCE_MODE=hybrid
export DATA_DIR=backend/data
export DB_HOST=localhost
export DB_NAME=reviewlens
export DB_USER=reviewlens
export DB_PASSWORD=reviewlens

# 애플리케이션 재시작 (새 데이터는 파일+DB 모두 저장)
```

### Phase 3: 기존 데이터 마이그레이션
```bash
# 파일 데이터를 DB로 이관 (스크립트 별도 작성 필요)
python scripts/migrate_file_to_db.py
```

### Phase 4: DB 전환
```bash
# DB 모드로 전환
export DATA_SOURCE_MODE=database
.env 파일에서 DB 모드로 전환
# DATA_SOURCE_MODE=hybrid
션 재시작
# 파일은 백업용으로만 사용
```

## 장점

### 1. 안정성
- **점진적 마이그레이션**: 한 번에 전환하지 않고 하이브리드 모드로 안전하게 전환
- **자동 폴백**: DB 장애시 자동으로 파일 시스템 사용
- **이중 저장**: 하이브리드 모드에서 파일과 DB 모두 저장

### 2. 유연성
- **환경 변수 기반**: 코드 변경 없이 모드 전환
- **모드별 전략**: 파일/DB/하이브리드 모드 선택 가능
- **설정 중앙 관리**: DatabaseConfig, DataSourceConfig

### 3. 확장성
- **컨넥션 풀**: psycopg3 ConnectionPool로 효율적 관리
- **추상화 인터페이스**: DataSource 인터페이스로 향후 다른 DB 지원 가능

## 다음 단계

1. **데이터 마이그레이션 스크립트 작성**
   - 파일 데이터를 DB로 이관하는 스크립트
   - `scripts/migrate_file_to_db.py`

2. **서비스 레이어 통합**
   - `ReviewService`에서 `get_data_source()` 사용
   - 기존 파일 로더 대체

3. **API 레이어 업데이트**
   - 라우터에서 데이터 소스 주입
   - 환경 변수 기반 자동 전환

4. **모니터링 추가**
   - DB 컨넥션 풀 메트릭
   - 데이터 소스 헬스체크

5. **테스트 작성**
   - 각 모드별 단위 테스트
   - 통합 테스트

## 참고

- 상세 가이드: [backend/app/infra/database/README.md](backend/app/infra/database/README.md)
- 사용 예시: [backend/app/infra/database/example_usage.py](backend/app/infra/database/example_usage.py)
- DB 스키마: [docs/reviewlens_db_schema/schema_postgres.sql](docs/reviewlens_db_schema/schema_postgres.sql)
