# LLM 설정 가이드

ReviewLens는 최종 분석 요약 생성을 위해 LLM을 사용합니다.
Gemini, OpenAI, Claude 중 원하는 제공자를 선택할 수 있습니다.

## 설정 방법

### 1. .env 파일 생성

프로젝트 루트에 `.env` 파일을 생성하세요:

```bash
cp .env.example .env
```

### 2. API 키 설정

사용할 LLM 제공자의 API 키를 설정하세요:

```bash
# Gemini 사용 (기본값)
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_api_key_here

# 또는 OpenAI 사용
LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here

# 또는 Claude 사용
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=your_api_key_here
```

### 3. API 키 발급 방법

#### Gemini (추천 - 무료 tier 제공)
1. https://aistudio.google.com/app/apikey 접속
2. "Get API Key" 클릭
3. 생성된 키를 `.env`에 입력

#### OpenAI
1. https://platform.openai.com/api-keys 접속
2. "Create new secret key" 클릭
3. 생성된 키를 `.env`에 입력

#### Claude (Anthropic)
1. https://console.anthropic.com/ 접속
2. "Get API Keys" 클릭
3. 생성된 키를 `.env`에 입력

### 4. 의존성 설치

```bash
cd backend
pip install -r requirements.txt
```

## 사용 가능한 설정

```bash
# LLM 제공자 선택
LLM_PROVIDER=gemini  # gemini, openai, claude

# 모델 선택 (선택사항, 기본값 사용)
GEMINI_MODEL=gemini-1.5-flash
OPENAI_MODEL=gpt-4o-mini
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# 생성 파라미터
LLM_TEMPERATURE=0.7      # 0.0-1.0, 낮을수록 결정적
LLM_MAX_TOKENS=2000      # 최대 토큰 수
```

## API 키 없이 사용하기

API 키가 없어도 시스템은 동작합니다.
LLM 요약 대신 기본 메시지가 표시됩니다.

```bash
# API 키 없이 실행
LLM_PROVIDER=gemini
# GEMINI_API_KEY는 설정하지 않음
```

## 비용 정보

- **Gemini**: 무료 tier 제공 (일일 1500 요청)
- **OpenAI**: 유료 (gpt-4o-mini: 약 $0.15/1M input tokens)
- **Claude**: 유료 (claude-3-5-sonnet: 약 $3/1M input tokens)

## 문제 해결

### API 키가 작동하지 않을 때

```bash
# 로그 확인
tail -f logs/app.log | grep LLM
```

### 다른 모델 사용하기

```bash
# Gemini의 다른 모델
GEMINI_MODEL=gemini-1.5-pro

# OpenAI의 다른 모델
OPENAI_MODEL=gpt-4o

# Claude의 다른 모델
CLAUDE_MODEL=claude-3-opus-20240229
```
