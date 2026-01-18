# 프롬프트 팩토리 패턴 사용 가이드

## 개요

프롬프트 팩토리는 LLM 프롬프트를 YAML 파일로 관리하여 자유롭게 실험할 수 있게 해주는 시스템입니다.

## 주요 기능

1. **프롬프트 템플릿 외부화**: 프롬프트를 코드가 아닌 YAML 파일로 관리
2. **다양한 전략 제공**: default, concise, detailed, friendly 등 다양한 스타일
3. **쉬운 전환**: 설정 파일이나 환경 변수로 전략 변경
4. **커스텀 템플릿**: 사용자 정의 YAML 템플릿 추가 가능

## 파일 구조

```
backend/llm/
├── prompt_factory.py          # 팩토리 클래스
├── llm_base.py               # PromptBuilder (팩토리 사용)
└── prompts/                  # 프롬프트 템플릿 디렉토리
    ├── default.yaml          # 기본 전략
    ├── concise.yaml          # 간결한 전략
    ├── detailed.yaml         # 상세한 전략
    └── friendly.yaml         # 친근한 전략
```

## 사용 방법

### 1. 기본 사용 (기존 코드 호환)

```python
from backend.llm.llm_base import PromptBuilder

# 자동으로 설정 파일의 PROMPT_STRATEGY 사용
system_prompt = PromptBuilder.build_system_prompt()
user_prompt = PromptBuilder.build_user_prompt(...)
```

### 2. 전략 변경 (코드)

```python
from backend.llm.llm_base import PromptBuilder

# 런타임에 전략 변경
PromptBuilder.set_strategy("friendly")
system_prompt = PromptBuilder.build_system_prompt()
```

### 3. 전략 변경 (환경 변수)

`.env` 파일에서:
```bash
# 기본 전략 (default)
PROMPT_STRATEGY=default

# 친근한 톤 (friendly)
PROMPT_STRATEGY=friendly

# 간결한 스타일 (concise)
PROMPT_STRATEGY=concise

# 상세한 분석 (detailed)
PROMPT_STRATEGY=detailed
```

### 4. 직접 팩토리 사용

```python
from backend.llm.prompt_factory import PromptFactory

# 전략 생성
strategy = PromptFactory.create(strategy="detailed")

# 프롬프트 생성
system_prompt = strategy.build_system_prompt()
user_prompt = strategy.build_user_prompt(
    top_factors=[("noise_loud", 8.5), ("motor_weak", 7.2)],
    evidence_reviews=[...],
    total_turns=3,
    category_name="무선청소기",
    product_name="테스트 제품"
)
```

### 5. 사용 가능한 전략 확인

```python
from backend.llm.prompt_factory import PromptFactory

strategies = PromptFactory.list_available_strategies()
print(strategies)  # ['concise', 'default', 'detailed', 'friendly']
```

## 제공되는 전략

### 1. default (기본)
- **특징**: 전문적이고 균형잡힌 톤
- **JSON 구조**: 표준 분석 형식
- **사용 케이스**: 일반적인 리뷰 분석

### 2. concise (간결)
- **특징**: 짧고 핵심만 전달
- **JSON 구조**: 최소한의 필드
- **사용 케이스**: 빠른 요약, 모바일 환경

### 3. detailed (상세)
- **특징**: 깊이 있는 분석, 전문가 수준
- **JSON 구조**: 확장된 필드 (user_segments, confidence_level 등)
- **사용 케이스**: 심층 분석, 전문가용 리포트

### 4. friendly (친근)
- **특징**: 캐주얼하고 친근한 톤
- **JSON 구조**: 구어체 표현
- **사용 케이스**: MZ세대 타겟, 편한 분위기

## 커스텀 전략 만들기

### 1. 새 YAML 파일 생성

`backend/llm/prompts/custom.yaml`:

```yaml
---
name: "custom"
description: "나만의 커스텀 프롬프트"
version: "1.0"

system_prompt: |
  당신은 나만의 스타일로 리뷰를 분석합니다.
  # 여기에 원하는 스타일 정의

user_prompt_template: |
  제품: {product_name}
  카테고리: {category_name}
  
  후회 요인:
  {factors_list}
  
  리뷰:
  {evidence_reviews}
  
  # 원하는 형식으로 응답 요청

fallback_template: |
  {{
    "summary": "{product_name}: {factors_text}",
    # Fallback 응답 형식
  }}
```

### 2. 커스텀 전략 사용

```python
# 파일 이름으로 사용
strategy = PromptFactory.create(strategy="custom")

# 또는 전체 경로 지정
strategy = PromptFactory.create(
    strategy_file="/path/to/custom.yaml"
)
```

## 템플릿 변수

프롬프트 템플릿에서 사용 가능한 변수:

- `{category_name}`: 제품 카테고리명
- `{product_name}`: 제품명
- `{total_turns}`: 대화 턴 수
- `{factors_list}`: 후회 요인 목록 (자동 포맷팅)
- `{evidence_reviews}`: 증거 리뷰 목록 (자동 포맷팅)
- `{evidence_count}`: 증거 리뷰 개수
- `{dialogue_section}`: 대화 내역 (옵션, 있으면 자동 포맷팅)
- `{factors_text}`: 쉼표로 구분된 요인 (fallback용)
- `{top_factor}`: 최상위 요인 (fallback용)

## 실전 예시

### A/B 테스트

```python
# A 그룹: 기본 전략
PromptBuilder.set_strategy("default")
response_a = llm_client.generate_summary(...)

# B 그룹: 친근한 전략
PromptBuilder.set_strategy("friendly")
response_b = llm_client.generate_summary(...)

# 사용자 피드백 비교
```

### 카테고리별 전략

```python
def get_strategy_for_category(category: str) -> str:
    """카테고리에 맞는 전략 선택"""
    if category in ["가전", "전자제품"]:
        return "detailed"  # 상세 분석
    elif category in ["패션", "뷰티"]:
        return "friendly"  # 친근한 톤
    else:
        return "default"

category = "무선청소기"
strategy_name = get_strategy_for_category(category)
PromptBuilder.set_strategy(strategy_name)
```

## 장점

1. **실험 용이**: 코드 변경 없이 프롬프트 수정 가능
2. **버전 관리**: YAML 파일을 Git으로 관리
3. **재사용성**: 검증된 프롬프트를 템플릿으로 공유
4. **A/B 테스트**: 다양한 전략을 쉽게 비교
5. **레거시 호환**: 기존 PromptBuilder 코드 그대로 사용

## 주의사항

1. YAML 문법 오류 시 fallback으로 hardcoded default 사용
2. 템플릿 변수 오타 시 KeyError 발생
3. JSON 형식 유지 필수 (LLM 응답 파싱용)

## 문제 해결

### Q1: 전략 파일을 찾을 수 없어요
```
[PromptFactory] 전략 파일 없음: backend/llm/prompts/custom.yaml
```

**해결**: 
- 파일 이름 확인 (대소문자 구분)
- 파일 위치 확인 (`backend/llm/prompts/` 디렉토리)
- 사용 가능한 전략: `PromptFactory.list_available_strategies()`

### Q2: 템플릿 변수가 치환되지 않아요

**해결**:
- 변수 이름 정확히 확인 (`{category_name}` not `{category}`)
- 중괄호 2개 필요 시 이스케이프: `{{` → JSON 중괄호

### Q3: 전략 변경이 적용되지 않아요

**해결**:
```python
# PromptBuilder 전략 리셋
PromptBuilder._default_strategy = None
PromptBuilder.set_strategy("new_strategy")
```

## 다음 단계

- [ ] 카테고리별 최적 전략 실험
- [ ] A/B 테스트 결과 수집
- [ ] 다국어 프롬프트 템플릿 추가
- [ ] 프롬프트 버전 관리 시스템
