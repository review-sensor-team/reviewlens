# 개발환경 셋업 가이드
## (초급 개발자용 · 쇼핑몰 리뷰 분석 챗봇)

> **최종 업데이트**: 2026-01-18  
> **현재 아키텍처**: Clean Architecture (Use Cases / Domain / Adapters)

이 문서는 **프로젝트에 처음 참여하는 개발자가**
로컬 개발환경을 셋업하고 GitHub 협업에 참여하기 위한 가이드입니다.

## 🏗️ 프로젝트 구조 이해

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

## 0. 준비물 체크리스트

- [ ] GitHub 계정
- [ ] Git 설치
- [ ] VS Code 설치
- [ ] Python 3.10 이상
- [ ] Node.js 18 이상

---

## 1. Git 설치 및 기본 설정

### 1-1. Git 설치 확인
```bash
git --version
```

없으면 설치:
- macOS: `brew install git`
- Windows: Git for Windows 설치

### 1-2. Git 사용자 정보 설정 (최초 1회)
```bash
git config --global user.name "홍길동"
git config --global user.email "hong@example.com"
```

---

## 2. GitHub 저장소 로컬로 가져오기

### 2-1. 로컬 개발 폴더 루트에서 저장소 클론
```bash
git clone https://github.com/review-sensor-team/reviewlens.git
cd reviewlens
```

---

## 3. 브랜치 생성 (중요)

⚠️ `main` 또는 `dev` 브랜치에서 절대 직접 작업하지 않습니다. 
```bash
git checkout dev
```

dev를 체크아웃 한 후 dev에 뿌리를 둔 "내작업"을 "feature/내작업"을 만들어 기능별 작업을 진행합니다.
```bash
git checkout -b feature/내작업이름
```

예시:
```bash
git checkout -b feature/llm-prompt-test
```

긴급수정(오류없음이 100%확신)이 필요한 경우 dev를 체크아웃 한 후 dev에 뿌리를 둔 "수정작업"을 "fix/수정작업-일시"을 만들어 기능별 작업을 진행합니다.
```bash
git checkout dev
```
```bash
git checkout -b fix/수정작업명-날짜
```

예시:
```bash
git checkout -b fix/front-typo-251227
```

현재 브랜치 확인:
```bash
git branch
```

---

## 4. Backend 개발환경 셋업 (FastAPI)

### 4-1. Python 가상환경 생성
```bash
cd reviewlens
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate   # Windows
```

### 4-2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4-3. 서버 실행
```bash
uvicorn backend.app.main:app --reload
```

확인:
- http://localhost:8000/docs

---

## 5. Frontend 개발환경 셋업 (Vue.js)

```bash
cd frontend
npm install
npm run dev
```

### 5-1. 확인
- 웹앱 주소: `http://localhost:5173`
- 브라우저에서 자동으로 열림

---

## 6. 환경변수 설정

### 6-1. Backend (.env)
```env
OPENAI_API_KEY=your_key_here
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
```

### 6-2. Frontend (.env.local)
```env
VUE_PUBLIC_API_BASE=http://localhost:5173
```

⚠️ `.env` 파일은 GitHub에 커밋하지 않습니다. (.gitignore 에 커밋제외 대상으로 추가)

---

## 7. 작업 → 커밋 → Push 흐름

### 7-1. 작업 상태 확인
```bash
git status
```

### 7-2. 커밋
```bash
git add .
git commit -m "feature: 리뷰 센서 태그 추출 구현"
```

### 7-3. Push
```bash
git push origin feature/내작업이름
```

---

## 8. PR 전에 반드시 해야 할 것 (중요)

### 8-1. 최신 main 반영
```bash
git checkout dev
git pull origin dev
git checkout feature/내작업이름
git merge dev
```

충돌 발생 시:
- 혼자 해결 ❌
- 즉시 팀 공유 ⭕

---

## 9. Pull Request(PR) 생성

GitHub 웹에서:
- 상단의 Pull requests 탭에서 해당 브랜치의 `Compare & Pull Request` 클릭
![alt text](img/image.png)
- Reviewers를 클릭하여 'Copilot'을 기본으로 선택하고, 관련 확인자 필요한 경우 1인 이상 선택합니다.
![alt text](img/image-1.png)
- 기본 'Copilot'의 리뷰를 통과한 후 관련 개발자가 컨펌(승인)하면 PR 아래쪽에 병합버튼이 활성화 됩니다.
![alt text](img/image-2.png)
- "Confirm squash and merge"를 선택하여 커밋 메시지를 입력한 후 "Confirm squash and merge"를 클릭하여 병합을 완료합니다. 
![alt text](img/image-3.png)
- dev에 뿌리를 두었기 때문에 PR의 'Confirm(승인)'을 통과하여 병합이 완료되면 자동으로 dev로 병합됩니다.

### PR 작성시 입력해야하는 내용 예시
```text
## 작업 내용
- 리뷰 센서 feature 추출 로직 구현

## 테스트 방법
- 샘플 리뷰 10개 로컬 테스트

## 체크리스트
- [x] 로그 추가
- [x] 에러 처리
```

---

## 10. 하루 작업 시작 전 그리고 PR "Confirm squash and merge" 이후 루틴

```bash
git checkout dev
git pull origin dev
git checkout feature/내작업이름
```

---

## 11. 문제가 생기면?

- 충돌(conflict) 발생 → 바로 공유
- push 후 커밋 실수 → 혼자 되돌리기 금지
- 모르면 질문이 가장 빠른 해결

---

## 12. 한 줄 요약

> **main(배포용소스), dev(최종병합소스)는 건드리지 않는다.  
> 브랜치에서 작업하고, PR로만 합친다.**
