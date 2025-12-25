# ReviewLens 프로젝트 현황 (2025-12-25)

## 🎯 완료된 작업

### 1. 코드 모듈화 (Architecture-Driven Refactoring)
- ✅ 단일 파일 `regret_bot.py` → 모듈화된 pipeline 구조로 전환
- ✅ architecture.md 정의에 따른 체계적인 폴더 구조 구현
- ✅ 각 모듈의 역할 명확히 분리 (SRP 준수)

### 2. Backend Pipeline 구현
- ✅ `ingest.py`: 텍스트 정규화, SHA1 기반 중복 제거
- ✅ `reg_store.py`: REG Factor/Question CSV 로딩, 파싱
- ✅ `sensor.py`: Factor scoring (anchor/context/negation), 평점 가중치
- ✅ `retrieval.py`: 요인별 증거 리뷰 추출 (관련 문장 발췌)
- ✅ `dialogue.py`: 3-5턴 대화 엔진, 안정성 기반 종료 조건
- ✅ `prompt_builder.py`: LLM Context JSON 생성

### 3. FastAPI 백엔드
- ✅ REST API 구조 완성
- ✅ Session management (in-memory)
- ✅ Pydantic schemas (request/response validation)
- ✅ CORS middleware 설정
- ✅ API 문서 자동 생성 (/docs)

### 4. Frontend (Vue.js)
- ✅ 챗봇 UI/UX 구현
- ✅ 실시간 요인 표시
- ✅ 대화형 인터페이스
- ✅ 최종 결과 화면
- ✅ API 연동 (axios)

### 5. 테스트
- ✅ `test_demo_scenario.py`: 3-5턴 대화 시나리오 pytest
- ✅ 모든 테스트 PASSED
- ✅ End-to-end 검증 완료

### 6. 문서화
- ✅ `README.md`: 현재 구현 상태 섹션 추가
- ✅ `README_DEV.md`: 개발자 가이드 대폭 강화
- ✅ `architecture.md`: 실제 구현 반영
- ✅ `REFACTORING_SUMMARY.md`: 리팩토링 내역 정리

## 📊 통계

### 코드 구조
- Pipeline 모듈: 7개
- FastAPI 모듈: 6개
- Frontend 컴포넌트: 1개
- 테스트: 1개 시나리오
- API Endpoints: 2개

### 테스트 결과
```
test_demo_3to5_turns PASSED (0.52s)
- 3턴 대화 시뮬레이션
- LLM context JSON 생성 확인
- 증거 리뷰 8개 이상 검증
```

### 샘플 데이터
```
Input: 205 reviews
After dedup: 185 reviews (removed 20)
Factors: 6
Questions: 3
```

## 🚀 실행 방법

### Backend API 서버
```bash
cd /Users/ssnko/app/python/reviewlens
source .venv/bin/activate
uvicorn backend.app.main:app --reload
# http://localhost:8000/docs
```

### Frontend 개발 서버
```bash
cd /Users/ssnko/app/python/reviewlens/frontend
npm run dev
# http://localhost:5173
```

### 테스트
```bash
python -m pytest tests/test_demo_scenario.py -v
```

### CLI 도구
```bash
python -m backend.regret_bot
```

## 📁 프로젝트 구조

```
reviewlens/
├── backend/
│   ├── pipeline/          # 핵심 처리 로직
│   │   ├── ingest.py
│   │   ├── reg_store.py
│   │   ├── sensor.py
│   │   ├── retrieval.py
│   │   ├── dialogue.py
│   │   └── prompt_builder.py
│   ├── app/              # FastAPI 애플리케이션
│   │   ├── main.py
│   │   ├── api/
│   │   ├── services/
│   │   ├── schemas/
│   │   └── core/
│   ├── data/             # REG CSV 데이터
│   └── regret_bot.py     # CLI 도구
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── ChatBot.vue
│   │   ├── api.js
│   │   ├── config.js
│   │   └── App.vue
│   └── package.json
├── tests/
│   └── test_demo_scenario.py
├── docs/
├── README.md
├── README_DEV.md
├── architecture.md
└── REFACTORING_SUMMARY.md
```

## 🔄 다음 단계

### Phase 1: LLM 통합 (우선순위 높음)
- [ ] OpenAI/Claude API 클라이언트 구현
- [ ] LLM context → final answer 생성
- [ ] Streaming response 지원

### Phase 2: Frontend 개선 (우선순위 중간)
- [ ] 증거 리뷰 상세 표시
- [ ] 요인별 필터링
- [ ] 차트/그래프 시각화
- [ ] 반응형 디자인 최적화

### Phase 3: 기능 확장 (우선순위 중간)
- [ ] Redis 세션 저장소
- [ ] PostgreSQL 리뷰 데이터 영구 저장
- [ ] 벡터 검색 (문서 유사도)
- [ ] 카테고리별 REG 확장

### Phase 4: Production (우선순위 낮음)
- [ ] Docker 컨테이너화
- [ ] 로깅/모니터링 (Sentry, DataDog)
- [ ] CI/CD 파이프라인
- [ ] 부하 테스트

## 💡 주요 개선 사항

### Before (단일 파일)
- 모든 기능이 하나의 파일에
- 테스트 어려움
- 재사용성 낮음

### After (모듈화)
- 각 모듈 100-200 lines
- 독립적 테스트 가능
- 명확한 책임 분리
- FastAPI 통합 용이

## 📈 성능 특징

- **LLM 호출**: 마지막 1회만 (비용 절감)
- **중복 제거**: SHA1 해시 기반 (정확도 100%)
- **대화 수렴**: 3-5턴 내 (사용자 경험 최적화)
- **증거 선택**: 요인별 8개 (신뢰도 & 간결성)

## 🎓 핵심 개념

### REG (Regret Explanation Graph)
- 후회 요인을 데이터 구조로 정의
- anchor/context/negation terms
- 가중치 기반 스코어링

### Review Sensor
- 리뷰를 "증거"로 변환
- NEG/POS/MIX 라벨링
- 요인별 관련도 점수화

### Dialogue Convergence
- 3-5턴 대화로 요인 좁히기
- 안정성 기반 종료 (2턴 연속 동일 top factor)
- 불필요한 리뷰 자동 탈락

## ✅ 품질 보증

- ✅ 모든 pytest 통과
- ✅ Type hints (Pydantic)
- ✅ API 문서 자동 생성
- ✅ 한글 주석 (초보자 친화)
- ✅ 깔끔한 코드 구조

## 📞 문의

프로젝트에 대한 질문이나 제안은 GitHub Issues를 이용해주세요.
