# 데이터베이스 설정 가이드

## 개요

ReviewLens는 파일 기반 시스템에서 PostgreSQL 기반 시스템으로 안전하게 마이그레이션할 수 있도록 설계되었습니다.

## 데이터 소스 모드

### 1. 파일 모드 (기본)
- 기존 CSV/JSON 파일 사용
- 마이그레이션 전 상태
- 설정: `DATA_SOURCE_MODE=file`

### 2. 하이브리드 모드 (권장 - 마이그레이션 중)
- 파일과 DB 병행 사용
- **읽기**: DB 우선, 실패시 파일 폴백
- **쓰기**: 파일과 DB 모두 저장
- 설정: `DATA_SOURCE_MODE=hybrid`

### 3. DB 모드 (마이그레이션 완료)
- PostgreSQL만 사용
- 최종 목표 상태
- 설정: `DATA_SOURCE_MODE=database`

## 환경 변수 설정

### .env 파일 설정 (권장)

프로젝트 루트의 `.env` 파일에 설정 추가:

```bash
# 데이터 소스 모드
DATA_SOURCE_MODE=file          # file, database, hybrid 중 선택

# 파일 설정
DATA_DIR=backend/data
FILE_FORMAT=json

# PostgreSQL 설정
DB_HOST=localhost
DB_PORT=5432
DB_NAME=reviewlens
DB_USER=reviewlens
DB_PASSWORD=reviewlens

# 컨넥션 풀 설정
DB_POOL_MIN_SIZE=2
DB_POOL_MAX_SIZE=10
DB_TIMEOUT=30.0
DB_MAX_IDLE=600.0
```

### 모드별 설정 예시

#### 파일 모드
```bash
export DATA_SOURCE_MODE=file
export DATA_DIR=backend/data
export FILE_FORMAT=json
```

### 하이브리드 모드
```bash
export DATA_SOURCE_MODE=hybrid
export DATA_DIR=backend/data
export FILE_FORMAT=json

# DB 설정
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=reviewlens
export DB_USER=reviewlens
export DB_PASSWORD=reviewlens

# 컨넥션 풀 설정 (선택)
export DB_POOL_MIN_SIZE=2
export DB_POOL_MAX_SIZE=10
export DB_TIMEOUT=30.0
export DB_MAX_IDLE=600.0
```

### DB 모드
```bash
export DATA_SOURCE_MODE=database

# DB 설정
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=reviewlens
export DB_USER=reviewlens
export DB_PASSWORD=reviewlens
```

## Docker Compose 설정

`docker-compose.yml`에 PostgreSQL 서비스 추가:

```yaml
services:
  postgres:
    image: postgres:14
    container_name: reviewlens-postgres
    environment:
      POSTGRES_DB: reviewlens
      POSTGRES_USER: reviewlens
      POSTGRES_PASSWORD: reviewlens_dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./docs/reviewlens_db_schema/schema_postgres.sql:/docker-entrypoint-initdb.d/01-schema.sql
    networks:
      - reviewlens
    restart: unless-stopped

  backend:
    # ... 기존 설정 ...
    environment:
      # 하이브리드 모드로 설정
      DATA_SOURCE_MODE: hybrid
      DATA_DIRSettings 기반 - 권장)

`.env` 파일 설정 후:

```python
from backend.app.infra.database import get_data_source

# Settings(.env)에서 자동으로 설정 로드
data_source = get_data_source()

# 리뷰 조회
reviews_df = data_source.get_reviews_by_category("coffee_machine")

# 요인 조회
factors_df = data_source.get_factors_by_category("coffee_machine")

# 질문 조회
questions_df = data_source.get_questions_by_category("coffee_machine")
```

### 2. 환경 변수 직접 사용 (레거시ackend/data
      FILE_FORMAT: json
      
      # DB 연결 설정
      DB_HOST: postgres  # Docker service name
      DB_PORT: 5432
      DB_NAME: reviewlens
      DB_USER: reviewlens
      DB_PASSWORD: reviewlens_dev_password
      
      # 컨넥션 풀 설정
      DB_POOL_MIN_SIZE: 2
      DB_POOL_MAX_SIZE: 10
    depends_on:
      - postgres
    networks:
      - reviewlens

volumes:
  postgres_data:

networks:
  reviewlens:
    driver: bridge
```

## 코드에서 사용

### 1. 자동 설정 (환경 변수 기반)

```python
from backend.app.infra.database import get_data_source

# 환경 변수에서 직접 로드 (Settings 사용 안 함)
data_source = get_data_source(use_settings=False)
```

### 3. 명시적 설정

```python
from backend.app.infra.database import DataSourceFactory

# 하이브리드 모드로 생성
data_source = DataSourceFactory.create(
    mode="hybrid",
    data_dir="backend/data",
    file_format="json",
    db_config={
        "host": "localhost",
        "port": 5432,
        "database": "reviewlens",
        "user": "reviewlens",
        "password": "reviewlens",
        "min_size": 2,
        "max_size": 10
    }
)

# 사용
reviews_df = data_source.get_reviews_by_category("coffee_machine", limit=100)
```

### 3. 컨넥션 풀 직접 사용

```python
from backend.app.infra.database import db_pool

# 초기화
db_pool.initialize(
    host="localhost",
    database="reviewlens",
    user="reviewlens",
    password="reviewlens"
)

# 헬스체크
if db_pool.health_check():
    print("DB 연결 정상")

# 쿼리 실행
results = db_pool.execute_query(
    "SELECT * FROM review WHERE category_id = %(category_id)s LIMIT 10",
    params={"category_id": 1},
    fetch="all"
)

# 컨텍스트 관리자로 안전한 사용
with db_pool.get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM review")
        count = cur.fetchone()

# 종료
db_pool.close()
```

## 마이그레이션 절차

### Phase 1: 준비
1. PostgreSQL 설치 및 스키마 생성
2. 환경 변수에 DB 설정 추가
3. 연결 테스트

```bash
# DB 스키마 생성
psql -U reviewlens -d reviewlens -f docs/reviewlens_db_schema/schema_postgres.sql

# 연결 테스트
python -c "from backend.app.infra.database import db_pool; db_pool.initialize(); print('OK' if db_pool.health_check() else 'FAIL')"
```

### Phase 2: 하이브리드 모드 전환
1. `DATA_SOURCE_MODE=hybrid` 설정
2. 애플리케이션 재시작
3. 새 데이터는 파일 + DB 동시 저장
4. 읽기는 DB 우선, 실패시 파일 폴백

```bash
export DATA_SOURCE_MODE=hybrid
# 애플리케이션 재시작
```

### Phase 3: 기존 데이터 마이그레이션
1. 파일 데이터를 DB로 이관
2. 데이터 검증

```bash
# 마이그레이션 스크립트 실행 (별도 작성 필요)
python scripts/migrate_file_to_db.py
```

### Phase 4: DB 모드 전환
1. 모든 데이터가 DB에 있는지 확인
2. `DATA_SOURCE_MODE=database` 설정
3. 애플리케이션 재시작
4. 파일은 백업용으로만 보관

```bash
export DATA_SOURCE_MODE=database
# 애플리케이션 재시작
```

## 장애 대응

### DB 장애시 파일 폴백 (하이브리드 모드)
- 하이브리드 모드에서는 DB 장애시 자동으로 파일에서 데이터 조회
- 애플리케이션 재시작 불필요

### 파일 모드로 롤백
```bash
export DATA_SOURCE_MODE=file
# 애플리케이션 재시작
```

## 모니터링

### 헬스체크
```python
from backend.app.infra.database import get_data_source

data_source = get_data_source()
if data_source.health_check():
    print("✓ 데이터 소스 정상")
else:
    print("✗ 데이터 소스 오류")
```

### 컨넥션 풀 통계
```python
from backend.app.infra.database import db_pool

stats = db_pool.get_pool_stats()
print(f"풀 크기: {stats['size']}")
print(f"사용 가능: {stats['available']}")
print(f"대기 중: {stats['waiting']}")
```

## 참고

- DB 스키마: [schema_postgres.sql](../../docs/reviewlens_db_schema/schema_postgres.sql)
- 사용 예시: [example_usage.py](./example_usage.py)
- 컨넥션 풀: psycopg3 ConnectionPool 사용
