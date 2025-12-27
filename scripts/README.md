# 스크립트 사용 가이드

이 디렉토리에는 리뷰 데이터 수집 및 처리를 위한 유틸리티 스크립트가 포함되어 있습니다.

## 네이버 스마트스토어 리뷰 수집

### 방법 1: 리뷰 수집 및 백엔드 형식 변환 (권장 ⭐)

수집한 리뷰를 `backend/data/review` 형식으로 자동 변환하여 저장합니다.

#### 설치
```bash
pip install selenium webdriver-manager pandas
```

#### 사용법
```bash
# 기본 사용 - CSV 형식으로 저장
python scripts/collect_smartstore_reviews.py \
  "https://brand.naver.com/airmade/products/11129902190" \
  --category appliance_heated_humidifier \
  --product-name airmade_4502 \
  --headless

# 특정 별점만 수집 (예: 5점만)
python scripts/collect_smartstore_reviews.py \
  "https://brand.naver.com/airmade/products/11129902190" \
  --category appliance_heated_humidifier \
  --product-name airmade_4502 \
  --rating 5 \
  --headless

# 특정 별점 이하만 수집 (예: 3점 이하)
python scripts/collect_smartstore_reviews.py \
  "https://brand.naver.com/airmade/products/11129902190" \
  --category appliance_heated_humidifier \
  --product-name airmade_4502 \
  --max-rating 3 \
  --headless

# 4점 이상 5점 이하 리뷰만 수집
python scripts/collect_smartstore_reviews.py \
  "https://brand.naver.com/airmade/products/11129902190" \
  --category appliance_heated_humidifier \
  --product-name airmade_4502 \
  --rating 4 \
  --max-rating 5 \
  --headless

# 최대 50개 리뷰, JSON 형식으로 저장
python scripts/collect_smartstore_reviews.py \
  "https://brand.naver.com/airmade/products/11129902190" \
  --category appliance_heated_humidifier \
  --product-name airmade_4502 \
  --max-reviews 50 \
  --format json \
  --headless

# CSV와 JSON 둘 다 생성
python scripts/collect_smartstore_reviews.py \
  "https://brand.naver.com/airmade/products/11129902190" \
  --category appliance_heated_humidifier \
  --product-name airmade_4502 \
  --max-reviews 100 \
  --format both \
  --headless

# 브라우저 창 보면서 실행 (디버깅용)
python scripts/collect_smartstore_reviews.py \
  "https://brand.naver.com/airmade/products/11129902190" \
  --category appliance_heated_humidifier \
  --product-name airmade_4502
```

#### 옵션
- `--category`, `-c`: 제품 카테고리 (필수, 예: appliance_heated_humidifier)
- `--product-name`, `-p`: 제품명 (필수, 예: airmade_4502)
- `--max-reviews`, `-m`: 최대 리뷰 수 (기본값: 100)
- `--rating`, `-r`: 수집할 별점 (1-5, 미지정시 모든 별점)
- `--max-rating`: 최대 별점 (해당 별점 이하만 수집, 1-5)
- `--format`, `-f`: 출력 형식 (csv, json, both, 기본값: csv)
- `--output-dir`, `-o`: 출력 디렉토리 (기본값: backend/data/review)
- `--headless`: 브라우저 창을 숨김 (백그라운드 실행)

#### 출력 형식

**파일명:** `reviews_smartstore_{category}_{product_name}_{YYYYMMDD}.csv|json`

**CSV/JSON 컬럼:**
- `review_id`: 리뷰 고유 ID (MD5 해시 기반)
- `rating`: 별점 (1-5)
- `text`: 리뷰 텍스트 (줄바꿈/특수문자 정규화됨)
- `created_at`: 작성일 (ISO 8601 형식: YYYY-MM-DDTHH:MM:SSZ)

**텍스트 정규화:**
- 줄바꿈(`\n`, `\r`)을 공백으로 변환
- 연속된 공백을 하나로 정리
- 제어 문자 제거
- CSV/JSON 포맷 안전성 확보

### 방법 2: Selenium 원본 수집

원본 리뷰 데이터를 그대로 수집합니다.

#### 사용법
```bash
# 기본 사용 (헤드리스 모드)
python scripts/fetch_smartstore_reviews_selenium.py "https://brand.naver.com/airmade/products/11129902190" --headless

# 브라우저 창 보면서 실행
python scripts/fetch_smartstore_reviews_selenium.py "https://brand.naver.com/airmade/products/11129902190"

# 최대 100개 리뷰만 수집
python scripts/fetch_smartstore_reviews_selenium.py "https://brand.naver.com/airmade/products/11129902190" --max-reviews 100 --headless

# JSON 형식으로 저장
python scripts/fetch_smartstore_reviews_selenium.py "https://brand.naver.com/airmade/products/11129902190" --format json --headless

# 출력 파일명 지정
python scripts/fetch_smartstore_reviews_selenium.py "https://brand.naver.com/airmade/products/11129902190" -o data/airmade_reviews.csv --headless
```

#### 옵션
- `--output`, `-o`: 출력 파일명 (기본값: smartstore_reviews.csv)
- `--format`, `-f`: 출력 형식 (csv, json, both)
- `--max-reviews`, `-m`: 최대 리뷰 수
- `--headless`: 브라우저 창을 숨김 (백그라운드 실행)

### 방법 3: API 직접 호출 (실험적)

네이버의 Rate Limiting으로 인해 현재는 제한적입니다.

```bash
# 먼저 API 엔드포인트 찾기
python scripts/find_review_api.py "https://brand.naver.com/airmade/products/11129902190"

# API를 찾았다면 직접 호출 스크립트 수정 후 사용
python scripts/fetch_smartstore_reviews.py "https://brand.naver.com/airmade/products/11129902190"
```

**주의**: 이 방법은 네이버의 API 변경이나 Rate Limiting으로 작동하지 않을 수 있습니다.

### 수동으로 API 찾기

브라우저 개발자 도구를 사용하여 실제 API 엔드포인트를 찾는 방법:

1. Chrome/Edge에서 상품 페이지 열기
2. 개발자 도구 열기 (F12 또는 Cmd+Option+I)
3. **Network** 탭 선택
4. **Fetch/XHR** 필터 선택
5. 페이지 새로고침 또는 리뷰 탭 클릭
6. "review" 키워드로 검색
7. 리뷰 데이터를 반환하는 API 요청 찾기
8. Request URL, Headers, Parameters 복사
9. `fetch_smartstore_reviews.py`의 `fetch_reviews()` 메서드 수정

## 기타 스크립트

### 리뷰 데이터 형식 변환

```bash
# JSONL을 CSV로 변환
python scripts/convert_reviews_jsonl_to_csv.py input.jsonl output.csv
```

## 수집된 데이터 형식

### Backend 형식 (collect_smartstore_reviews.py)

백엔드 분석 파이프라인과 호환되는 형식입니다.

**CSV 예시:**
```csv
review_id,rating,text,created_at
939543957658,5,"정말 좋아요 강력 추천합니다",2025-12-17T00:00:00Z
110779565666,4,"괜찮네요 만족합니다",2025-12-14T00:00:00Z
```

**JSON 예시:**
```json
[
  {
    "review_id": 939543957658,
    "rating": 5,
    "text": "정말 좋아요 강력 추천합니다",
    "created_at": "2025-12-17T00:00:00Z"
  },
  {
    "review_id": 110779565666,
    "rating": 4,
    "text": "괜찮네요 만족합니다",
    "created_at": "2025-12-14T00:00:00Z"
  }
]
```

### 원본 형식 (fetch_smartstore_reviews_selenium.py)

**CSV 예시:**
```csv
rating,content,author,created_at,helpful_count,is_photo,photo_count
5,"정말 좋아요",user123,2024.01.15,10,true,2
4,"괜찮네요",user456,2024.01.14,5,false,0
```

**JSON 예시:**
```json
[
  {
    "rating": 5,
    "content": "정말 좋아요",
    "author": "user123",
    "created_at": "2024.01.15",
    "helpful_count": 10,
    "is_photo": true,
    "photo_count": 2
  }
]
```

## 사용 예시

### 제품별 리뷰 수집 시나리오

**1. 고평점 리뷰만 수집 (마케팅 자료용)**
```bash
python scripts/collect_smartstore_reviews.py \
  "https://brand.naver.com/airmade/products/11129902190" \
  --category appliance \
  --product-name airmade_4502 \
  --rating 5 \
  --max-reviews 100 \
  --format both \
  --headless
```

**2. 저평점 리뷰만 수집 (개선점 분석용)**
```bash
python scripts/collect_smartstore_reviews.py \
  "https://brand.naver.com/airmade/products/11129902190" \
  --category appliance \
  --product-name airmade_4502 \
  --max-rating 3 \
  --max-reviews 50 \
  --format csv \
  --headless
```

**3. 전체 리뷰 수집 (종합 분석용)**
```bash
python scripts/collect_smartstore_reviews.py \
  "https://brand.naver.com/airmade/products/11129902190" \
  --category appliance \
  --product-name airmade_4502 \
  --max-reviews 500 \
  --format both \
  --headless
```

**4. 중간 평점 리뷰 수집 (3-4점, 상세 피드백 분석용)**
```bash
python scripts/collect_smartstore_reviews.py \
  "https://brand.naver.com/airmade/products/11129902190" \
  --category appliance \
  --product-name airmade_4502 \
  --rating 3 \
  --max-rating 4 \
  --format json \
  --headless
```

## 문제 해결

### Selenium 오류
- **ChromeDriver 오류**: webdriver-manager가 자동으로 설치하지만, 수동 설치가 필요할 수 있습니다.
- **브라우저가 열리지 않음**: `--headless` 옵션 제거하고 다시 시도
- **리뷰를 찾을 수 없음**: 페이지 구조가 변경되었을 수 있습니다. 셀렉터 확인 필요

### Rate Limiting
- 너무 많은 요청을 보내면 일시적으로 차단될 수 있습니다
- 요청 사이에 지연 시간을 추가하세요
- 헤드리스 모드(`--headless`)를 사용하여 부하 감소

### 리뷰가 수집되지 않음
1. URL이 올바른지 확인 (예: `https://brand.naver.com/브랜드명/products/제품ID`)
2. 상품 페이지에 실제로 리뷰가 있는지 확인
3. 네이버의 페이지 구조가 변경되었을 수 있음 → CSS 셀렉터 업데이트 필요
4. `--headless` 옵션을 제거하여 브라우저에서 직접 확인

### 텍스트 포맷 문제
- **줄바꿈 문제**: `collect_smartstore_reviews.py`는 자동으로 줄바꿈을 공백으로 변환합니다
- **특수문자 오류**: 텍스트 정규화 기능이 제어 문자를 자동 제거합니다
- **CSV 파싱 오류**: pandas가 자동으로 처리하지만, 이상 시 JSON 형식 사용 권장

### 필터링 관련
- **별점 필터링**: `--rating`과 `--max-rating`을 함께 사용하여 범위 지정 가능
- **수량 제한**: `--max-reviews`로 수집 개수 제한
- **필터링 후 빈 결과**: 조건을 완화하거나 `max-reviews`를 증가시키세요

## 참고사항

### 권장 사용 방법
- **일반 분석**: `collect_smartstore_reviews.py` 사용 (백엔드 형식으로 자동 변환)
- **원본 데이터 보관**: `fetch_smartstore_reviews_selenium.py` 사용
- **디버깅**: `--headless` 옵션 제거하여 브라우저 동작 확인

### 데이터 수집 가이드라인
- 네이버의 로봇 감지 시스템을 우회하기 위해 적절한 지연 시간 사용
- 대량 수집 시 네이버 이용약관 준수
- 수집한 데이터는 연구/분석 목적으로만 사용
- 상업적 사용 전 법적 검토 필요

### 성능 최적화
- `--headless` 옵션으로 리소스 절약
- `--max-reviews`로 필요한 만큼만 수집
- 별점 필터링으로 불필요한 데이터 제외

### 스크립트 목록
- **collect_smartstore_reviews.py**: 리뷰 수집 및 백엔드 형식 변환 (⭐ 권장)
- **fetch_smartstore_reviews_selenium.py**: Selenium 기반 원본 리뷰 수집
- **fetch_smartstore_reviews.py**: API 직접 호출 (실험적)
- **find_review_api.py**: 리뷰 API 엔드포인트 탐색 도구
