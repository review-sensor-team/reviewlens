# 스마트스토어 리뷰 수집 기능 사용 가이드

## 개요

ChatBot.vue에서 네이버 스마트스토어 상품 URL을 입력하면 자동으로 별점이 낮은 리뷰 100건을 수집하여 대화형 분석을 시작할 수 있습니다.

## 아키텍처

### Backend

1. **Collector 모듈** (`backend/collector/`)
   - `smartstore_collector.py`: Selenium을 사용한 리뷰 수집 로직
   - scripts/collect_smartstore_reviews.py를 기반으로 API용으로 재작성
   - 별점 낮은순 정렬 지원
   - 여러 페이지 순회하여 리뷰 수집

2. **API 엔드포인트** (`backend/app/api/routes_chat.py`)
   - `POST /api/chat/collect-reviews`: 리뷰 수집 API
   - Request:
     ```json
     {
       "product_url": "https://brand.naver.com/airmade/products/11129902190",
       "max_reviews": 100,
       "sort_by_low_rating": true
     }
     ```
   - Response:
     ```json
     {
       "success": true,
       "message": "리뷰 100건을 수집했습니다.",
       "reviews": [...],
       "total_count": 100
     }
     ```

3. **Schemas** (`backend/app/schemas/`)
   - `requests.py`: CollectReviewsRequest 추가
   - `responses.py`: CollectReviewsResponse, Review 추가

### Frontend

1. **API 통신** (`frontend/src/api.js`)
   - `collectReviews()`: 리뷰 수집 API 호출 함수
   - timeout을 120초로 증가 (리뷰 수집에 시간 소요)

2. **UI 컴포넌트** (`frontend/src/components/ChatBot.vue`)
   - URL 입력 화면
   - 리뷰 수집 중 로딩 화면
   - 수집 완료 후 채팅 화면

## 사용 방법

### 1. 의존성 설치

Backend에 Selenium 관련 패키지가 필요합니다:

```bash
cd backend
pip install selenium webdriver-manager

# 선택사항: 일반 스마트스토어용 (brand.naver.com이 아닌 경우)
pip install undetected-chromedriver
```

### 2. 백엔드 실행

```bash
cd backend
uvicorn app.main:app --reload
```

### 3. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

### 4. 사용

1. 브라우저에서 `http://localhost:5173` 접속
2. 스마트스토어 상품 URL 입력
   - 예: `https://brand.naver.com/airmade/products/11129902190`
3. "리뷰 수집" 버튼 클릭
4. 리뷰 수집 완료 후 자동으로 세션 시작
5. 궁금한 점 질문

## 주요 기능

### 리뷰 수집
- **별점 낮은순 정렬**: 후회 요인 분석에 중요한 저평점 리뷰 우선 수집
- **최대 100건**: 분석에 충분한 양의 리뷰 수집
- **자동 페이징**: 여러 페이지 자동 순회
- **중복 제거**: review_id 기반 중복 제거

### UI/UX
- **단계별 안내**: URL 입력 → 수집 중 → 채팅 화면
- **로딩 인디케이터**: 리뷰 수집 진행 상황 표시
- **에러 핸들링**: 수집 실패 시 명확한 오류 메시지

## 트러블슈팅

### Chrome 드라이버 문제
```bash
# ChromeDriver 수동 설치 (선택사항)
brew install chromedriver  # macOS
```

### 리뷰 수집 실패
- 네트워크 연결 확인
- 상품 URL이 올바른지 확인
- 상품이 존재하는지 확인
- Chrome 브라우저가 설치되어 있는지 확인

### 타임아웃 에러
- 리뷰가 많은 경우 시간이 오래 걸릴 수 있습니다
- api.js의 timeout 값을 더 늘려보세요 (현재 120초)

## 파일 구조

```
backend/
├── collector/
│   ├── __init__.py
│   └── smartstore_collector.py
├── app/
│   ├── api/
│   │   └── routes_chat.py
│   └── schemas/
│       ├── requests.py
│       └── responses.py

frontend/
└── src/
    ├── api.js
    ├── config.js
    └── components/
        └── ChatBot.vue
```

## 향후 개선 사항

- [ ] 수집한 리뷰를 데이터베이스에 저장
- [ ] 리뷰 수집 진행률 표시
- [ ] 다양한 정렬 옵션 (최신순, 평점 높은순 등)
- [ ] 수집 리뷰 수 조절 가능
- [ ] 다른 쇼핑몰 지원 (쿠팡, G마켓 등)
