# 스크립트 사용 가이드

이 디렉토리에는 리뷰 데이터 수집 및 처리를 위한 유틸리티 스크립트가 포함되어 있습니다.

## 네이버 스마트스토어 리뷰 수집

### 개요

`collect_smartstore_reviews.py` 스크립트는 네이버 스마트스토어와 브랜드스토어에서 리뷰를 자동으로 수집하여 백엔드 분석 파이프라인에 바로 사용할 수 있는 형식으로 변환합니다.

**주요 기능:**
- ✅ **봇 탐지 우회**: undetected-chromedriver 사용으로 네이버의 봇 감지 시스템 우회
- ✅ **보안확인 처리**: CAPTCHA 수동 해결 지원 (자동 대기)
- ✅ **자동 페이징**: 여러 페이지를 순회하며 원하는 양만큼 리뷰 수집
- ✅ **멀티 사이트 지원**: smartstore.naver.com과 brand.naver.com 모두 지원
- ✅ **리뷰 탭 자동 감지**: 리뷰 탭을 자동으로 찾아 클릭
- ✅ **별점 필터링**: 특정 별점 또는 범위의 리뷰만 선택적으로 수집
- ✅ **다양한 출력 형식**: CSV, JSON 또는 둘 다 지원

### 설치

```bash
pip install selenium undetected-chromedriver pandas
```

### 기본 사용법

#### 1. 기본 수집 (50개 리뷰, CSV 형식)
```bash
python scripts/collect_smartstore_reviews.py \
  "https://smartstore.naver.com/lgpshop/products/10421972784" \
  --category electronics \
  --product-name lg_standbyme \
  --max-reviews 50
```

#### 2. 브랜드스토어에서 수집
```bash
python scripts/collect_smartstore_reviews.py \
  "https://brand.naver.com/everybot/products/11163824445" \
  --category robot_vacuum \
  --product-name everybot_x1 \
  --max-reviews 100 \
  --headless
```

#### 3. 저평점 리뷰만 수집 (후회포인트 분석용)
```bash
python scripts/collect_smartstore_reviews.py \
  "https://brand.naver.com/everybot/products/11163824445" \
  --category robot_vacuum \
  --product-name everybot_low_rating \
  --max-rating 3 \
  --max-reviews 50 \
  --headless
```

#### 4. 특정 별점만 수집
```bash
# 5점 리뷰만 수집
python scripts/collect_smartstore_reviews.py \
  "https://brand.naver.com/airmade/products/11129902190" \
  --category appliance \
  --product-name airmade_5star \
  --rating 5 \
  --max-reviews 100 \
  --headless
```

#### 5. JSON 형식으로 저장
```bash
python scripts/collect_smartstore_reviews.py \
  "https://smartstore.naver.com/lgpshop/products/10421972784" \
  --category electronics \
  --product-name lg_product \
  --max-reviews 50 \
  --format json
```

#### 6. CSV와 JSON 둘 다 생성
```bash
python scripts/collect_smartstore_reviews.py \
  "https://brand.naver.com/airmade/products/11129902190" \
  --category appliance \
  --product-name airmade_all \
  --max-reviews 100 \
  --format both \
  --headless
```

### 명령행 옵션

| 옵션 | 단축키 | 필수 | 설명 | 기본값 |
|------|--------|------|------|--------|
| `url` | - | ✅ | 스마트스토어 상품 URL | - |
| `--category` | `-c` | ✅ | 제품 카테고리 (예: electronics, appliance) | - |
| `--product-name` | `-p` | ✅ | 제품명 (예: lg_standbyme) | - |
| `--max-reviews` | `-m` | ❌ | 최대 리뷰 수 | 100 |
| `--rating` | `-r` | ❌ | 수집할 별점 (1-5) | 전체 |
| `--max-rating` | - | ❌ | 최대 별점 (해당 별점 이하만 수집) | - |
| `--format` | `-f` | ❌ | 출력 형식 (csv, json, both) | csv |
| `--output-dir` | `-o` | ❌ | 출력 디렉토리 | backend/data/review |
| `--headless` | - | ❌ | 브라우저 창 숨김 (brand.naver.com 권장) | False |

### 보안확인(CAPTCHA) 처리

네이버의 봇 감지 시스템이 활성화되면 보안확인 페이지가 나타날 수 있습니다.

**사이트별 발생 빈도:**
- `smartstore.naver.com`: 보안확인이 자주 발생할 수 있음 → `--headless` 옵션 제거 권장
- `brand.naver.com`: 보안확인이 거의 발생하지 않음 → `--headless` 옵션 사용 가능

**자동 처리 방식:**
1. 스크립트가 보안확인 페이지를 자동 감지
2. 브라우저 창에 보안확인 문제가 표시됨
3. 사용자가 수동으로 문제를 풀면 자동으로 계속 진행
4. 최대 2분간 대기 (대기 시간 초과 시 계속 진행)

```
⚠️  보안확인 페이지가 감지되었습니다.
브라우저에서 보안확인 문제를 풀어주세요.
문제를 풀면 자동으로 계속 진행됩니다...

대기 중... (10초 경과)
✓ 보안확인 완료! 페이지 로딩 중...
```

**참고:** `--headless` 옵션을 사용하면 브라우저 창이 보이지 않아 CAPTCHA를 풀 수 없으므로, 보안확인이 예상되는 경우 headless 모드를 사용하지 마세요.

### 페이징 처리

스크립트는 자동으로 여러 페이지를 순회하며 리뷰를 수집합니다.

**작동 방식:**
1. 첫 페이지(20개 리뷰) 수집
2. 다음 페이지 번호 클릭
3. 새 페이지의 리뷰(20개) 수집 및 누적
4. 목표 수량 도달 또는 마지막 페이지까지 반복

**진행 상황 표시:**
```
리뷰 데이터 수집 중...
페이지 1: +20개 (총 20개)
페이지 2: +20개 (총 40개)
페이지 3: +20개 (총 60개)
✓ 목표 리뷰 수(50)에 도달했습니다.
```

### 출력 형식

**파일명 규칙:**
```
reviews_smartstore_{category}_{product_name}_{YYYYMMDD_HHMMSS}.csv|json
```

**예시:**
- `reviews_smartstore_electronics_lg_standbyme_20251229_204828.csv`
- `reviews_smartstore_robot_vacuum_everybot_x1_20251229_205023.json`

**CSV/JSON 스키마:**
```csv
review_id,rating,text,created_at
178732791109,5,"32인치 딱 적당하고, 소리는 좋습니다...",2025-12-03T17:40:39Z
225210586419,5,"요즘 집에서 TV를 보는 시간이...",2025-12-18T22:36:21Z
```

**컬럼 설명:**
- `review_id`: 리뷰 고유 ID (텍스트 MD5 해시 기반)
- `rating`: 별점 (1-5)
- `text`: 리뷰 텍스트 (정규화됨)
- `created_at`: 작성일 (ISO 8601 형식)

**텍스트 정규화:**
- 줄바꿈(`\n`, `\r`)을 공백으로 변환
- 연속된 공백을 하나로 통합
- 제어 문자 제거
- CSV/JSON 포맷 안전성 확보

### 사용 시나리오

**1. 고평점 리뷰 수집 (만족 포인트 분석)**
```bash
python scripts/collect_smartstore_reviews.py \
  "https://brand.naver.com/everybot/products/11163824445" \
  --category robot_vacuum \
  --product-name everybot_5star \
  --rating 5 \
  --max-reviews 100 \
  --format csv \
  --headless
```

**2. 저평점 리뷰 수집 (후회 포인트 분석)**
```bash
python scripts/collect_smartstore_reviews.py \
  "https://brand.naver.com/everybot/products/11163824445" \
  --category robot_vacuum \
  --product-name everybot_low \
  --max-rating 3 \
  --max-reviews 50 \
  --format csv \
  --headless
```

**3. 대량 수집 (전체 분석)**
```bash
python scripts/collect_smartstore_reviews.py \
  "https://smartstore.naver.com/lgpshop/products/10421972784" \
  --category electronics \
  --product-name lg_standbyme_all \
  --max-reviews 200 \
  --format both
```

**4. 중간 평점 리뷰 (개선점 발견)**
```bash
python scripts/collect_smartstore_reviews.py \
  "https://brand.naver.com/airmade/products/11129902190" \
  --category appliance \
  --product-name airmade_mid \
  --max-rating 4 \
  --max-reviews 80 \
  --format json \
  --headless
```

## 문제 해결

### 봇 감지 및 CAPTCHA

**증상:**
- "보안확인 페이지가 감지되었습니다" 메시지
- 브라우저에 CAPTCHA 문제 표시

**해결 방법:**
1. `--headless` 옵션 제거 (브라우저 창이 보여야 CAPTCHA를 풀 수 있음)
2. 브라우저에 표시된 보안확인 문제를 수동으로 해결
3. 스크립트가 자동으로 계속 진행

**예방 방법:**
- 요청 간격을 두고 여러 번 나눠서 수집
- 하루에 수집하는 총량 제한

### 페이징 문제

**증상:**
- "더 이상 페이지가 없습니다" 메시지가 너무 빨리 나옴
- 페이지 순환 감지

**해결 방법:**
1. `--headless` 옵션 제거하고 브라우저 확인
2. 페이지 네비게이션이 정상적으로 작동하는지 확인
3. 리뷰 수가 적은 상품의 경우 정상 동작

### 리뷰를 찾을 수 없음

**증상:**
- "리뷰 요소를 찾을 수 없습니다" 메시지
- 수집된 리뷰가 0개

**해결 방법:**
1. URL이 올바른지 확인
   - ✅ `https://smartstore.naver.com/상점명/products/상품ID`
   - ✅ `https://brand.naver.com/브랜드명/products/상품ID`
2. 상품 페이지에 실제로 리뷰가 있는지 확인
3. `--headless` 제거하고 브라우저에서 직접 확인
4. 리뷰 탭이 있는지 확인

### 드라이버 오류

**증상:**
- "ChromeDriver 오류"
- "element click intercepted"
- "NoSuchWindowException"

**해결 방법:**
1. undetected-chromedriver 재설치:
   ```bash
   pip uninstall undetected-chromedriver
   pip install undetected-chromedriver
   ```
2. Chrome 브라우저 최신 버전으로 업데이트
3. `--headless` 옵션 제거하고 재시도

### 텍스트 인코딩 문제

**증상:**
- CSV 파일에서 한글이 깨짐
- 특수문자가 제대로 표시되지 않음

**해결 방법:**
- CSV는 `utf-8-sig` 인코딩으로 자동 저장됨
- Excel에서 열 때: "데이터 > 텍스트 나누기 > UTF-8" 선택
- JSON 형식 사용 권장: `--format json`

### 필터링 결과가 비어있음

**증상:**
- 별점 필터링 후 수집된 리뷰가 0개

**해결 방법:**
1. 필터 조건 확인 (해당 별점의 리뷰가 실제로 있는지)
2. `--max-reviews` 값 증가
3. 필터 조건 완화 (예: `--max-rating 3` 대신 `--max-rating 4`)

## 참고사항

### 지원하는 URL 형식

✅ **지원:**
- `https://smartstore.naver.com/상점명/products/상품ID`
- `https://brand.naver.com/브랜드명/products/상품ID`

❌ **미지원:**
- 쿠팡, G마켓 등 다른 쇼핑몰
- 네이버쇼핑 검색 페이지
- 개별 리뷰 상세 페이지

### 데이터 수집 가이드라인

**법적 고려사항:**
- 네이버 이용약관 준수
- 개인정보 보호법 준수 (리뷰어 식별 정보 제외)
- 수집한 데이터는 연구/분석 목적으로만 사용
- 상업적 사용 전 법적 검토 필요

**윤리적 고려사항:**
- 적절한 요청 간격 유지
- 서버 부하 최소화
- 대량 수집 시 시간 분산

### 성능 최적화

**빠른 수집:**
- `--headless` 옵션 사용 (CAPTCHA가 없는 경우)
- `--max-reviews` 값을 적절히 설정
- 별점 필터링으로 불필요한 데이터 제외

**안정적인 수집:**
- `--headless` 옵션 제거 (브라우저 확인 가능)
- 보안확인 발생 시 수동 해결
- 여러 번에 나눠서 수집

### 백엔드 통합

수집된 데이터는 `backend/data/review/` 디렉토리에 저장되며, 백엔드 분석 파이프라인에서 바로 사용할 수 있습니다.

**사용 예시:**
```python
import pandas as pd

# CSV 로드
df = pd.read_csv('backend/data/review/reviews_smartstore_electronics_lg_standbyme_20251229_204828.csv')

# JSON 로드
import json
with open('backend/data/review/reviews_smartstore_robot_vacuum_everybot_20251229_205023.json') as f:
    reviews = json.load(f)
```

### 기술 스택

- **Python 3.9+**
- **undetected-chromedriver**: 봇 감지 우회
- **Selenium**: 웹 자동화
- **pandas**: 데이터 처리 및 저장
- **Chrome/Chromium**: 브라우저 엔진

### 추가 리소스

- [Selenium 공식 문서](https://www.selenium.dev/documentation/)
- [undetected-chromedriver GitHub](https://github.com/ultrafunkamsterdam/undetected-chromedriver)
- [pandas 공식 문서](https://pandas.pydata.org/docs/)

## 변경 이력

### 2025-12-29
- ✅ undetected-chromedriver 도입으로 봇 감지 우회
- ✅ CAPTCHA 수동 해결 지원
- ✅ 페이징 처리 구현 (여러 페이지 자동 순회)
- ✅ smartstore.naver.com과 brand.naver.com 모두 지원
- ✅ 리뷰 탭 자동 감지 및 클릭
- ✅ JavaScript 클릭으로 요소 차단 문제 해결
- ✅ 방문 페이지 추적으로 중복 방지
- ✅ 실시간 진행 상황 표시

### 이전 버전
- 기본 Selenium 기반 리뷰 수집
- CSV/JSON 출력 형식 지원
- 별점 필터링 기능
