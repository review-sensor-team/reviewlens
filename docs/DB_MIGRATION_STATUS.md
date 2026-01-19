# DB 마이그레이션 상태

## 완료된 작업 (2025-01-17)

### 1. 인프라 구축 ✅
- **Connection Pool**: PostgreSQL 연결 풀 관리 (`backend/app/infra/database/connection_pool.py`)
- **Data Source 추상화**: 파일/DB/하이브리드 모드 지원 (`backend/app/infra/database/data_source.py`)
- **Factory 패턴**: 설정 기반 자동 생성 (`backend/app/infra/database/factory.py`)
- **설정 통합**: Settings.py와 .env 연동 (`backend/app/core/settings.py`)

### 2. 서비스 레이어 리팩토링 ✅
- **ReviewService**: 파일 로더 → 데이터 소스로 전환
- **ChatService**: CSV 로더 → 데이터 소스로 전환
- **Review Router**: 3개 엔드포인트 업데이트
  - `/analyze-product`
  - `/factor-reviews/{session_id}/{factor_key}`
  - `/answer-question/{session_id}`

### 3. Python 3.9 호환성 수정 ✅
- **타입 힌팅**: `str | Path` → `Union[str, Path]` 전환
- **조건부 임포트**: psycopg 선택적 의존성 처리
- **영향받은 파일**:
  - `backend/app/infra/database/data_source.py`
  - `backend/app/infra/database/factory.py`
  - `backend/app/infra/database/config.py`
  - `backend/app/services/review_service.py`
  - `backend/app/services/chat_service.py`
  - `backend/app/infra/loaders/*.py`
  - `backend/app/infra/storage/csv_storage.py`

### 4. 테스트 검증 ✅
- **파일 모드**: psycopg 없이 정상 작동 (test_data_source.py)
- **API 서버**: FastAPI 정상 응답 확인 (`/api/v2/reviews/config`)
- **pytest**: 기본 테스트 통과

## 현재 상태

### 동작 모드
```env
# .env 설정
DATA_SOURCE_MODE=file  # 기본값: 파일 모드
DATA_DIR=backend/data
FILE_FORMAT=json
```

### 파일 모드 (현재 활성)
- PostgreSQL 불필요
- 기존 파일 시스템 사용
- 즉시 사용 가능

### DB 모드 (준비 완료, 미사용)
```bash
# PostgreSQL 설치 필요
pip install 'psycopg[pool]'

# DB 시작
./db_start.sh

# .env 변경
DATA_SOURCE_MODE=database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=reviewlens
DB_USER=reviewlens
DB_PASSWORD=reviewlens
```

### 하이브리드 모드 (준비 완료, 미사용)
- 읽기: DB 우선, 실패 시 파일
- 쓰기: 파일 + DB 동시 저장
- 점진적 마이그레이션용

## 다음 단계

### 우선순위 1: DialogueSession 리팩토링
DialogueSession이 아직 load_csvs()를 직접 호출하고 있음.

**수정 필요**:
```python
# backend/app/usecases/dialogue/session.py
# Before
from backend.app.adapters.persistence.reg.store import load_csvs

# After
from backend.app.infra.database import get_data_source
data_source = get_data_source()
factors_df = data_source.get_factors_by_category(category)
```

### 우선순위 2: DB 스키마 적용
```bash
# 1. PostgreSQL 시작
./db_start.sh

# 2. 스키마 생성
psql -h localhost -U reviewlens -d reviewlens < docs/reviewlens_db_schema/schema_postgres.sql

# 3. 데이터 마이그레이션 (수동)
# - 파일 → DB 복사 스크립트 작성
# - 카테고리, 제품, 리뷰 순서로 이동
```

### 우선순위 3: 하이브리드 모드 테스트
```env
DATA_SOURCE_MODE=hybrid
```
- 파일과 DB 동시 사용
- 신뢰성 검증
- 성능 비교

## 코드 구조

```
backend/app/infra/database/
├── __init__.py              # 모듈 진입점
├── connection_pool.py       # PostgreSQL 연결 풀
├── data_source.py           # 데이터 소스 추상화
├── factory.py               # 팩토리 패턴
├── config.py                # 설정 클래스
├── README.md                # 사용 가이드
└── example_usage.py         # 예제 코드
```

## 의존성

### 파일 모드 (현재)
```
pandas
fastapi
```

### DB 모드 (선택적)
```
psycopg[pool]  # PostgreSQL 어댑터
```

### 버전 호환성
- Python 3.9+
- FastAPI 0.95.2
- Pydantic 2.x (호환성 경고 있음, 작동은 함)

## 롤백 계획

DB 마이그레이션 실패 시:
```env
# .env
DATA_SOURCE_MODE=file  # 원복
```

모든 서비스는 기존 파일 시스템으로 자동 전환됩니다.

## 참고 문서
- [DB_MIGRATION_GUIDE.md](DB_MIGRATION_GUIDE.md) - 마이그레이션 절차
- [DATA_SOURCE_REFACTORING.md](DATA_SOURCE_REFACTORING.md) - 리팩토링 상세
- [reviewlens_db_schema/README_DB.md](reviewlens_db_schema/README_DB.md) - DB 스키마
