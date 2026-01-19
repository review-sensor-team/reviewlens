# 데이터 소스 리팩토링 완료 보고서

## 변경 개요

파일 기반 데이터 로딩을 새로운 데이터 소스 팩토리 패턴으로 전환하여, 파일/DB/하이브리드 모드를 Settings 기반으로 자동 전환할 수 있도록 개선했습니다.

## 변경된 파일

### 1. ReviewService (backend/app/services/review_service.py)

**변경 전:**
```python
from ..infra.loaders import ReviewLoaderFactory
from ..infra.storage.csv_storage import CSVStorage

self._review_loader = ReviewLoaderFactory.create(...)
self._storage = CSVStorage(...)
```

**변경 후:**
```python
from ..infra.database import get_data_source

self._data_source = get_data_source(use_settings=True)
```

**주요 업데이트:**
- `_get_review_loader()` → `_get_data_source()` 로 통합
- `_get_storage()` 제거
- `_load_from_storage()`: 데이터 소스 사용
- `_collect_from_crawler()`: 저장시 데이터 소스 사용
- `_match_review_file()`: 데이터 소스로 리뷰 조회

### 2. ChatService (backend/app/services/chat_service.py)

**변경 전:**
```python
from ..adapters.persistence.reg.store import load_csvs

reviews, factors_df, questions_df = load_csvs(self.data_dir)
```

**변경 후:**
```python
from ..infra.database import get_data_source

data_source = get_data_source(use_settings=True)
reviews = data_source.get_reviews_by_category(category=category)
factors_df = data_source.get_factors_by_category(category=category)
questions_df = data_source.get_questions_by_category(category=category)
```

**주요 업데이트:**
- `create_session()`: load_csvs 대신 데이터 소스 사용
- 카테고리별 데이터 로딩으로 더 구체적인 조회

### 3. Review Router (backend/app/api/routers/review.py)

**변경 전:**
```python
from ...adapters.persistence.reg.store import load_csvs

_, factors_df, _ = load_csvs(data_dir)
_, _, questions_df = load_csvs(get_data_dir())
```

**변경 후:**
```python
from ...infra.database import get_data_source

data_source = get_data_source(use_settings=True)
factors_df = data_source.get_factors_by_category(category=category)
questions_df = data_source.get_questions_by_category(category=category)
```

**업데이트된 엔드포인트:**
- `POST /api/v2/reviews/analyze-reviews`: Factors 로드시 데이터 소스 사용
- `POST /api/v2/reviews/analyze-product`: Factors 로드시 데이터 소스 사용
- `POST /api/v2/reviews/answer-question`: Questions 로드시 데이터 소스 사용
- `_load_factor_questions()`: 레거시 지원 (TODO: 카테고리 기반 조회)

## 레거시 호환성

일부 함수에서는 카테고리 정보가 없을 때 레거시 `load_csvs()` 폴백 유지:
```python
# 카테고리 정보 없으면 레거시 방식 사용
from ...adapters.persistence.reg.store import load_csvs
_, _, questions_df = load_csvs(get_data_dir())
```

## 설정 방법

### .env 파일 설정
```bash
# 파일 모드 (기본)
DATA_SOURCE_MODE=file
DATA_DIR=backend/data

# 하이브리드 모드 (권장 - 마이그레이션 중)
DATA_SOURCE_MODE=hybrid
DATA_DIR=backend/data
DB_HOST=localhost
DB_NAME=reviewlens
DB_USER=reviewlens
DB_PASSWORD=reviewlens

# DB 모드 (마이그레이션 완료)
DATA_SOURCE_MODE=database
```

### 코드에서 자동 적용
```python
# Settings(.env)에서 자동으로 설정 읽음
data_source = get_data_source(use_settings=True)
reviews_df = data_source.get_reviews_by_category("coffee_machine")
```

## 장점

1. **중앙 집중식 설정**: 모든 데이터 접근이 Settings를 통해 통일
2. **점진적 마이그레이션**: 파일 → 하이브리드 → DB로 안전하게 전환
3. **자동 폴백**: 하이브리드 모드에서 DB 실패시 파일 자동 사용
4. **코드 간소화**: 여러 loader/storage 클래스 대신 하나의 data_source
5. **타입 안전성**: Settings의 Pydantic 검증

## 테스트 권장사항

1. **파일 모드 테스트** (.env에 `DATA_SOURCE_MODE=file`)
   ```bash
   python -m pytest backend/app/services/test_review_service.py
   ```

2. **하이브리드 모드 테스트** (DB 시작 후)
   ```bash
   ./db_start.sh
   # .env에 DATA_SOURCE_MODE=hybrid 설정
   python -m pytest backend/app/services/test_review_service.py
   ```

3. **API 통합 테스트**
   ```bash
   curl http://localhost:8000/api/v2/reviews/products
   ```

## 향후 작업 (TODO)

1. ✅ ReviewService 업데이트 (완료)
2. ✅ ChatService 업데이트 (완료)
3. ✅ Review Router 업데이트 (완료)
4. ⏳ DialogueSession 업데이트 (backend/app/usecases/dialogue/session.py)
5. ⏳ 단위 테스트 작성
6. ⏳ 통합 테스트 작성
7. ⏳ 성능 테스트 (파일 vs DB 모드)

## 마이그레이션 체크리스트

- [x] Settings에 DB 설정 추가
- [x] .env.example 업데이트
- [x] 데이터 소스 팩토리 구현
- [x] ReviewService 리팩토링
- [x] ChatService 리팩토링
- [x] Review Router 리팩토링
- [ ] DialogueSession 리팩토링
- [ ] 테스트 작성
- [ ] 문서 업데이트
- [ ] 프로덕션 배포 준비
