# ReviewLens 데모 실행 가이드

## 📋 사전 준비

1. Python 가상환경 활성화
2. Backend 의존성 설치 완료
3. Frontend npm 패키지 설치 완료

---

## 🚀 1단계: Backend API 서버 시작

### 터미널 1에서 실행

```bash
cd /Users/ssnko/app/python/reviewlens
source .venv/bin/activate
uvicorn backend.app.main:app --reload
```

### 확인
- 서버 주소: `http://localhost:8000`
- API 문서: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/chat/start`

---

## 🎨 2단계: Frontend 개발 서버 시작

### 터미널 2에서 실행

```bash
cd /Users/ssnko/app/python/reviewlens/frontend
npm run dev
```

### 확인
- 웹앱 주소: `http://localhost:5173`
- 브라우저에서 자동으로 열림

---

## 💬 3단계: 챗봇 테스트 시나리오

### Frontend UI에서 대화 진행

#### 턴 1
**사용자 입력**: "소음이 심한가요?"

**예상 동작**:
- 봇이 응답 메시지 표시
- 상위 요인 뱃지 표시 (예: noise_sleep)
- 요인 점수 표시

#### 턴 2
**사용자 입력**: "청소 상태는 어떤가요?"

**예상 동작**:
- 누적된 요인 점수 업데이트
- 새로운 질문 또는 안내 메시지
- 상위 3개 요인 갱신

#### 턴 3
**사용자 입력**: "가격 대비 만족도가 궁금합니다"

**예상 동작**:
- 대화 종료 (is_final = true)
- 최종 분석 결과 화면 표시
  - 주요 후회 요인 Top 3
  - 증거 리뷰 개수 (8개 이상)
  - 새로운 분석 시작 버튼

---

## 🔧 4단계: API 직접 테스트 (선택 사항)

### cURL로 API 테스트

#### 세션 시작
```bash
curl -X POST http://localhost:8000/api/chat/start \
  -H "Content-Type: application/json" \
  -d '{"category": "hotel"}'
```

**응답 예시**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "세션이 시작되었습니다. 무엇이 궁금하신가요?"
}
```

#### 메시지 전송
```bash
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "message": "소음이 심한가요?"
  }'
```

**응답 예시**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "bot_message": "소음 관련 질문이시네요...",
  "is_final": false,
  "top_factors": [
    {"factor_key": "noise_sleep", "score": 1.2}
  ],
  "llm_context": null
}
```

---

## 📊 5단계: 샘플 데이터 확인

### 사용 중인 데이터

```
backend/data/
├── review/review_sample.csv     # 205개 리뷰
├── reg_factor.csv               # 6개 후회 요인
└── reg_question.csv             # 3개 질문
```

### 요인 목록 (예시)
- `noise_sleep`: 소음/수면 방해
- `cleanliness`: 청결 상태
- `value_for_money`: 가격 대비 만족도
- `location`: 위치/접근성
- `service`: 서비스 품질
- `facility`: 시설 상태

---

## ✅ 6단계: 기대 동작 확인

### 정상 동작 체크리스트

- [ ] Frontend 로드 시 자동 세션 생성
- [ ] 사용자 메시지 입력 가능
- [ ] 봇 응답 표시
- [ ] 요인 뱃지 표시 (점수 포함)
- [ ] 3-5턴 대화 진행
- [ ] 최종 결과 화면 표시
  - [ ] Top 3 요인
  - [ ] 증거 리뷰 개수
  - [ ] 새로운 분석 시작 버튼

### 로그 확인

**Backend 터미널**:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Frontend 터미널**:
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

---

## 🐛 문제 해결

### CORS 오류가 발생하는 경우

**증상**: 브라우저 콘솔에 CORS 에러

**해결**:
1. `backend/app/core/settings.py` 확인
2. `ALLOWED_ORIGINS`에 `http://localhost:5173` 포함 여부 확인
3. Backend 재시작

### 연결 실패

**증상**: "서버 연결에 실패했습니다" 메시지

**해결**:
1. Backend 서버 실행 중인지 확인
2. `http://localhost:8000/docs` 접속 테스트
3. Frontend `.env` 파일의 `VITE_API_URL` 확인

### 데이터 없음

**증상**: "파일을 찾을 수 없습니다" 오류

**해결**:
1. `backend/data/` 폴더 존재 확인
2. CSV 파일 존재 확인
3. CSV 헤더 확인: `review_id`, `rating`, `text`, `created_at`

### Frontend 빌드 오류

**증상**: npm run dev 실패

**해결**:
```bash
rm -rf node_modules package-lock.json
npm install
npm run dev
```

---

## 📝 추가 테스트

### CLI 도구로 파이프라인 테스트

```bash
cd /Users/ssnko/app/python/reviewlens
source .venv/bin/activate
python -m backend.regret_bot
```

**출력 확인**:
- CSV 로딩 성공
- 중복 제거 통계
- Factor 스코어링
- LLM context JSON 생성

### Pytest로 자동화 테스트

```bash
python -m pytest tests/test_demo_scenario.py -v
```

**기대 결과**:
```
test_demo_3to5_turns PASSED
```

---

## 🎯 성공 기준

1. ✅ Backend 서버 정상 실행
2. ✅ Frontend 서버 정상 실행
3. ✅ 챗봇 UI 로딩
4. ✅ 3턴 대화 완료
5. ✅ 최종 결과 표시
6. ✅ Top 3 요인 확인
7. ✅ 증거 리뷰 8개 이상

---

## 📞 지원

문제가 지속되면 다음을 확인하세요:
1. Python 버전: 3.9+
2. Node.js 버전: 16+
3. 로그 파일 확인
4. 브라우저 개발자 도구 콘솔

Happy Testing! 🚀
