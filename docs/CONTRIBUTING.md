# 개발 기여 가이드 (Contributing Guide)
## ReviewLens 프로젝트 참여 통합 가이드

> **최종 업데이트**: 2026-01-18  
> **현재 아키텍처**: Clean Architecture (Use Cases / Domain / Adapters)  
> **코드 품질**: 58% 코드 감소, 36개 헬퍼 함수 추출

이 문서는 **ReviewLens 프로젝트에 참여하는 모든 개발자를 위한 통합 가이드**입니다.  
개발환경 설정부터 코드 스타일, PR 제출까지 모든 내용을 포함합니다.

---

## 📋 목차

1. [기본 원칙](#1-기본-원칙)
2. [프로젝트 구조](#2-프로젝트-구조)
3. [개발환경 준비](#3-개발환경-준비)
4. [Backend 설정](#4-backend-설정)
5. [Frontend 설정](#5-frontend-설정)
6. [브랜치 전략](#6-브랜치-전략)
7. [코드 스타일](#7-코드-스타일)
8. [작업 흐름](#8-작업-흐름)
9. [Pull Request](#9-pull-request)
10. [일일 루틴](#10-일일-루틴)

---

## 1. 기본 원칙

### 개발 철학
- **문서 우선 (Docs First)**: 코드 변경 전 문서화
- **Clean Architecture**: 명확한 레이어 분리 (Use Cases / Domain / Adapters)
- **인터페이스 기준 개발**: 타입 안전성 보장
- **모든 변경은 PR 기반**: 코드 리뷰 필수
- **단일 책임 원칙**: 함수는 40줄 이하, 복잡도 5 이하 권장
- **DRY 원칙**: 중복 코드 제거, 공통 로직은 constants.py

### 레이어별 책임

#### Domain Layer (`domain/rules/`)
- **순수 비즈니스 로직**: 외부 의존성 없음
- 예: 텍스트 정규화, 스코어링 규칙, 리뷰 추출 로직

#### Use Cases Layer (`usecases/`)
- **애플리케이션 로직**: 대화 플로우, 상태 관리
- Domain과 Adapters 조합

#### Adapters Layer (`adapters/`)
- **외부 연동**: CSV 파일, 데이터베이스, API
- Domain에 의존하지만 Use Cases에 의존되지 않음

---

## 2. 프로젝트 구조

ReviewLens는 **Clean Architecture** 원칙에 따라 구성됩니다:

```
backend/app/
├── domain/              # 도메인 레이어 (비즈니스 규칙)
│   ├── entities/        # 도메인 엔티티 (향후)
│   └── rules/
│       └── review/      # normalize, scoring, retrieval
├── usecases/            # 유스케이스 레이어 (대화 로직)
│   └── dialogue/        # DialogueSession (3-5턴)
├── adapters/            # 어댑터 레이어 (외부 연동)
│   └── persistence/
│       └── reg/         # Factor/Question CSV 접근
├── services/            # 서비스 레이어
│   ├── review_service.py
│   └── prompt_service.py
└── api/                 # API 레이어 (FastAPI)
    └── routers/
        └── review.py    # V2 엔드포인트
```

**의존성 방향**: API → Services → Use Cases → Domain ← Adapters

---

## 3. 개발환경 준비

### 준비물 체크리스트

- [ ] GitHub 계정
- [ ] Git 설치
- [ ] VS Code 설치
- [ ] Python 3.10 이상
- [ ] Node.js 18 이상

### Git 설치 및 설정

```bash
# Git 설치 확인
git --version

# Git 사용자 정보 설정 (최초 1회)
git config --global user.name "홍길동"
git config --global user.email "hong@example.com"

# 저장소 클론
git clone https://github.com/review-sensor-team/reviewlens.git
cd reviewlens
```

---

## 4. Backend 설정

### Python 가상환경 및 의존성 설치
```bash
cd reviewlens
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### 환경변수 설정
```bash
# backend/.env 파일 생성
OPENAI_API_KEY=your_key_here
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
```

⚠️ `.env` 파일은 GitHub에 커밋하지 않습니다 (.gitignore에 포함됨)

### 서버 실행
```bash
uvicorn backend.app.main:app --reload
```

확인: http://localhost:8000/docs

---

## 5. Frontend 설정

### 의존성 설치 및 개발 서버 실행
```bash
cd frontend
npm install
npm run dev
```

### 환경변수 설정
```bash
# frontend/.env.local 파일 생성
VUE_PUBLIC_API_BASE=http://localhost:5173
```

확인: http://localhost:5173

---

## 6. 브랜치 전략

### 브랜치 종류
- `main`: 안정 버전 (프로덕션)
- `dev`: 통합 개발 (테스트 완료)
- `feature/*`: 기능 개발 (예: feature/#18-chat_bot_bug)
- `fix/*`: 긴급 수정 (예: fix/import-error-20260118)

### 기능 개발 시작

⚠️ **중요**: `main` 또는 `dev` 브랜치에서 절대 직접 작업하지 않습니다!

```bash
# dev 브랜치로 이동
git checkout dev
git pull origin dev

# 새 기능 브랜치 생성
git checkout -b feature/내작업이름

# 예시
git checkout -b feature/llm-prompt-test
```

### 긴급 수정
```bash
git checkout dev
git checkout -b fix/수정작업명-날짜

# 예시
git checkout -b fix/front-typo-20260118
```

---

## 7. 코드 스타일

### Python 스타일
- **Import 순서**: 표준 라이브러리 → 서드파티 → 로컬 모듈
- **함수 크기**: 40줄 이하 권장 (복잡한 로직은 헬퍼 함수로 추출)
- **타입 힌트**: 모든 함수에 타입 힌트 추가
- **Docstring**: 공개 함수/클래스는 Google 스타일 docstring

### 리팩토링 가이드
1. **함수 크기 확인**: `python scripts/analyze_refactor.py` 실행
2. **40줄 이상 함수**: Extract Method 패턴으로 분리
3. **중복 코드**: DRY 원칙에 따라 공통 함수 추출
4. **내부 import**: 파일 상단으로 이동
5. **커밋 메시지**: "리팩토링: [함수명] - [변경 내용]"

### 커밋 메시지 형식
```
기능: 리뷰 센서 태그 추출 구현
수정: Vue 템플릿 v-for key 배치 오류 해결
리팩토링: DialogueSession._select_factors - 헬퍼 함수 추출
문서: Clean Architecture 재구성 반영
개선: 대화 히스토리에 전체 흐름 포함
```

---

## 8. 작업 흐름

### 하루 작업 시작 전
```bash
git checkout dev
git pull origin dev
git checkout feature/내작업이름
```

### 작업 중
```bash
# 작업 상태 확인
git status

# 변경사항 스테이징
git add .

# 커밋
git commit -m "기능: 리뷰 센서 태그 추출 구현"
```

### Push
```bash
git push origin feature/내작업이름
```

### PR 전 최신 dev 반영
```bash
git checkout dev
git pull origin dev
git checkout feature/내작업이름
git merge dev
```

⚠️ 충돌 발생 시: 혼자 해결 ❌ / 즉시 팀 공유 ⭕

---

## 9. Pull Request

### PR 생성
1. GitHub 웹에서 `Pull requests` 탭 클릭
2. `Compare & Pull Request` 버튼 클릭
3. Reviewers에서 'Copilot' 선택 (기본) + 필요시 개발자 1인 이상 추가

### PR 작성 예시
```markdown
## 작업 내용
- 리뷰 센서 feature 추출 로직 구현
- DialogueSession 리팩토링 (7개 함수 추출)

## 테스트 방법
- 샘플 리뷰 10개 로컬 테스트
- pytest 통과 확인

## 체크리스트
- [x] 로그 추가
- [x] 에러 처리
- [x] 문서 업데이트
```

### 병합 절차
1. Copilot 리뷰 통과
2. 지정된 리뷰어 승인
3. "Confirm squash and merge" 클릭
4. dev 브랜치로 자동 병합

---

## 10. 일일 루틴

### 작업 시작
```bash
git checkout dev
git pull origin dev
git checkout feature/내작업이름
```

### 작업 종료
```bash
git add .
git commit -m "기능: ..."
git push origin feature/내작업이름
```

### 문제 발생 시
- 충돌(conflict) → 바로 공유
- push 후 커밋 실수 → 혼자 되돌리기 금지
- 모르면 질문이 가장 빠른 해결

---

## 📌 한 줄 요약

> **main(배포용), dev(최종병합)는 건드리지 않는다.  
> 브랜치에서 작업하고, PR로만 합친다.**
