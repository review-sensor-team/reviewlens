# LLM 프롬프트 팩토리 패턴

## 개요

LLM 프롬프트를 YAML 템플릿으로 관리하여 자유롭게 실험할 수 있는 시스템입니다.

## 특징

- ✅ **외부화된 프롬프트**: 코드 수정 없이 프롬프트 변경
- ✅ **다양한 전략**: default, concise, detailed, friendly
- ✅ **쉬운 전환**: 환경 변수로 전략 선택
- ✅ **커스텀 템플릿**: 사용자 정의 YAML 추가 가능
- ✅ **레거시 호환**: 기존 코드 변경 불필요

## 빠른 시작

### 1. 환경 변수 설정

`.env` 파일:
```bash
PROMPT_STRATEGY=default  # default|concise|detailed|friendly
```

### 2. 코드는 그대로

```python
from backend.llm.llm_base import PromptBuilder

# 자동으로 PROMPT_STRATEGY 전략 사용
system_prompt = PromptBuilder.build_system_prompt()
```

### 3. 전략 변경 (옵션)

```python
# 런타임 전략 변경
PromptBuilder.set_strategy("friendly")
```

## 제공 전략

| 전략 | 톤 | 길이 | 사용 케이스 |
|------|-----|------|-------------|
| **default** | 전문적 | 보통 | 일반 분석 |
| **concise** | 간결 | 짧음 | 빠른 요약 |
| **detailed** | 전문가 | 김 | 심층 분석 |
| **friendly** | 친근 | 보통 | MZ세대 |

## 파일 구조

```
backend/llm/
├── prompt_factory.py          # 팩토리 클래스
├── llm_base.py               # PromptBuilder
└── prompts/                  # YAML 템플릿
    ├── default.yaml          # 기본
    ├── concise.yaml          # 간결
    ├── detailed.yaml         # 상세
    └── friendly.yaml         # 친근
```

## 커스텀 전략 만들기

`backend/llm/prompts/my_strategy.yaml`:
```yaml
---
name: "my_strategy"
description: "나만의 프롬프트"
version: "1.0"

system_prompt: |
  여기에 시스템 프롬프트 작성

user_prompt_template: |
  제품: {product_name}
  {factors_list}
  {evidence_reviews}
  
  원하는 형식으로 응답하세요

fallback_template: |
  {{
    "summary": "{product_name}: {factors_text}"
  }}
```

사용:
```python
PromptBuilder.set_strategy("my_strategy")
```

## 상세 문서

👉 [PROMPT_FACTORY_GUIDE.md](../docs/PROMPT_FACTORY_GUIDE.md)

## 예시

### 전략별 시스템 프롬프트 비교

**default**:
> 당신은 제품 리뷰 분석 전문가입니다. 구매자들의 후회 요인을 분석하여...

**friendly**:
> 당신은 똑똑하고 친근한 쇼핑 메이트입니다. 진짜 친구처럼 솔직하게...

**concise**:
> 당신은 리뷰 분석 AI입니다. 핵심만 간결하게 전달합니다...

**detailed**:
> 당신은 20년 경력의 제품 리뷰 분석 전문가입니다. 데이터 기반으로...

## 테스트

```bash
# 간단한 테스트
python test_prompt_factory_simple.py

# 전체 테스트
python -m backend.llm.test_prompt_factory
```
