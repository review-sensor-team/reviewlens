# Backend Dependencies 가이드

## 의존성 파일 구조

```
backend/
├── requirements.txt              # 전체 의존성 (프로덕션)
├── requirements-minimal.txt      # 최소 의존성 (파일 모드)
├── requirements-db.txt          # 데이터베이스 모드
├── requirements-llm.txt         # LLM 제공자
└── requirements-dev.txt         # 개발 도구
```

## 설치 방법

### 1. 기본 설치 (권장)

모든 의존성 포함:

```bash
cd backend
pip install -r requirements.txt
```

### 2. 최소 설치 (파일 모드만)

LLM과 DB 없이 파일 기반만:

```bash
cd backend
pip install -r requirements-minimal.txt
```

### 3. 선택적 설치

#### Database 모드 추가

```bash
pip install -r requirements-db.txt
```

#### LLM 제공자 추가

```bash
# 모든 LLM 제공자
pip install -r requirements-llm.txt

# 또는 개별 설치
pip install openai          # OpenAI (GPT-4)
pip install anthropic       # Anthropic (Claude)
pip install google-generativeai  # Google (Gemini)
```

#### 개발 도구 추가

```bash
pip install -r requirements-dev.txt
```

### 4. 조합 설치

```bash
# 최소 + DB
pip install -r requirements-minimal.txt -r requirements-db.txt

# 최소 + LLM
pip install -r requirements-minimal.txt -r requirements-llm.txt

# 전체 (프로덕션)
pip install -r requirements.txt

# 전체 + 개발 도구
pip install -r requirements-dev.txt
```

## 의존성 설명

### 필수 의존성 (requirements-minimal.txt)

| 패키지 | 버전 | 용도 |
|--------|------|------|
| fastapi | 0.115.0 | Web framework |
| uvicorn | 0.32.0 | ASGI server |
| pydantic | 2.10.0 | 데이터 검증 |
| pydantic-settings | 2.6.0 | 설정 관리 |
| pandas | 2.3.3 | 데이터 처리 |
| numpy | 2.0.2 | 수치 연산 |
| requests | 2.32.3 | HTTP 클라이언트 |
| python-dotenv | >=1.0.0 | 환경 변수 |
| prometheus-client | >=0.20.0 | 메트릭 수집 |
| pytest | 8.4.2 | 테스트 |

### 데이터베이스 의존성 (requirements-db.txt)

| 패키지 | 버전 | 용도 |
|--------|------|------|
| psycopg[binary,pool] | >=3.2,<4 | PostgreSQL 드라이버 |

### LLM 의존성 (requirements-llm.txt)

| 패키지 | 버전 | 용도 |
|--------|------|------|
| openai | >=1.50.0 | OpenAI API (GPT-4, GPT-3.5) |
| anthropic | >=0.39.0 | Anthropic API (Claude) |
| google-generativeai | >=0.8.0 | Google API (Gemini) |

### 개발 의존성 (requirements-dev.txt)

| 패키지 | 용도 |
|--------|------|
| black | 코드 포매터 |
| flake8 | 린터 |
| mypy | 타입 체커 |
| isort | import 정렬 |
| pytest-cov | 테스트 커버리지 |
| pytest-mock | 모킹 |
| httpx | FastAPI 테스트 |
| ipython | 대화형 쉘 |
| jupyter | 노트북 |

## 환경별 권장 설치

### 로컬 개발

```bash
pip install -r requirements-dev.txt
```

### CI/CD 테스트

```bash
pip install -r requirements-minimal.txt
```

### 프로덕션 (파일 모드)

```bash
pip install -r requirements.txt
```

### 프로덕션 (DB 모드)

```bash
pip install -r requirements.txt
# 또는
pip install -r requirements-minimal.txt -r requirements-db.txt -r requirements-llm.txt
```

## 의존성 업데이트

```bash
# 최신 버전으로 업그레이드
pip install --upgrade -r requirements.txt

# 특정 패키지만 업그레이드
pip install --upgrade fastapi uvicorn
```

## 의존성 동결

현재 설치된 버전 저장:

```bash
pip freeze > requirements-frozen.txt
```

## 트러블슈팅

### psycopg 설치 실패

```bash
# 시스템 패키지 설치 필요 (macOS)
brew install postgresql

# 시스템 패키지 설치 필요 (Ubuntu)
sudo apt-get install libpq-dev
```

### 버전 충돌

```bash
# 가상환경 재생성
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 참고

- **Pydantic v2**: FastAPI 0.115.0부터 Pydantic 2.x 지원
- **Python 버전**: Python 3.9+ 필요
- **가상환경**: 항상 가상환경 사용 권장
