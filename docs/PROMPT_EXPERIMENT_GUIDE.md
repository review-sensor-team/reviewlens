# 프롬프트 전략 실험 가이드

## 사용 시나리오

### 1. 기본 사용 (변경 없음)

`.env` 파일:
```bash
PROMPT_STRATEGY=default
```

기존 코드 그대로 사용:
```python
from backend.llm.llm_factory import LLMFactory

llm = LLMFactory.create_llm()
summary = llm.generate_summary(
    top_factors=[...],
    evidence_reviews=[...],
    ...
)
```

### 2. 친근한 톤으로 변경

`.env` 파일:
```bash
PROMPT_STRATEGY=friendly
```

서버 재시작 → 친근한 톤으로 응답!

### 3. A/B 테스트

```python
from backend.llm.llm_base import PromptBuilder
from backend.llm.llm_factory import LLMFactory

# A 그룹: 기본 전략
PromptBuilder.set_strategy("default")
llm_a = LLMFactory.create_llm()
response_a = llm_a.generate_summary(...)

# B 그룹: 친근한 전략  
PromptBuilder.set_strategy("friendly")
llm_b = LLMFactory.create_llm()
response_b = llm_b.generate_summary(...)

# 사용자 만족도 비교
```

### 4. 카테고리별 맞춤 전략

```python
def get_strategy_for_category(category: str) -> str:
    """카테고리에 맞는 프롬프트 전략 선택"""
    
    tech_categories = ["무선청소기", "노트북", "스마트폰", "태블릿"]
    fashion_categories = ["의류", "신발", "가방"]
    beauty_categories = ["화장품", "스킨케어"]
    
    if category in tech_categories:
        return "detailed"  # 상세한 기술 분석
    elif category in fashion_categories or category in beauty_categories:
        return "friendly"  # 친근한 추천
    else:
        return "default"   # 기본 분석

# 사용
category = "무선청소기"
strategy = get_strategy_for_category(category)
PromptBuilder.set_strategy(strategy)
```

### 5. 새로운 전략 실험

`backend/llm/prompts/experimental.yaml`:
```yaml
---
name: "experimental"
description: "실험용 프롬프트 - 질문 형식"
version: "1.0"

system_prompt: |
  당신은 구매자에게 질문을 던지는 리뷰 분석가입니다.
  후회 요인을 분석한 뒤, 구매자가 스스로 판단하도록 질문을 제시합니다.

user_prompt_template: |
  제품: {product_name}
  후회 요인: {factors_list}
  리뷰: {evidence_reviews}
  
  다음 형식으로 응답하세요:
  {{
    "summary": "핵심 요약",
    "questions_for_buyer": [
      "당신은 {factor}에 얼마나 민감한가요?",
      "..."
    ],
    "recommendation": "구매|보류|조건부"
  }}

fallback_template: |
  {{
    "summary": "{product_name} 분석 중...",
    "questions_for_buyer": ["구매 전 검토해보세요"],
    "recommendation": "조건부"
  }}
```

사용:
```bash
# .env
PROMPT_STRATEGY=experimental
```

### 6. 프롬프트 버전 관리

```bash
# Git으로 프롬프트 변경 추적
git log backend/llm/prompts/default.yaml

# 이전 버전으로 롤백
git checkout HEAD~1 backend/llm/prompts/default.yaml

# 브랜치별 프롬프트 실험
git checkout experiment/prompt-v2
# 다른 프롬프트로 테스트
```

## 실험 체크리스트

### 새 전략 추가 시

- [ ] YAML 파일 생성 (`backend/llm/prompts/`)
- [ ] 메타데이터 작성 (name, description, version)
- [ ] 시스템 프롬프트 작성
- [ ] 유저 프롬프트 템플릿 작성 (변수 확인)
- [ ] Fallback 템플릿 작성
- [ ] 로컬 테스트
- [ ] 실제 리뷰로 검증
- [ ] A/B 테스트 (옵션)
- [ ] Git 커밋

### 기존 전략 수정 시

- [ ] 변경 이유 문서화
- [ ] 백업 (Git 커밋 전)
- [ ] 로컬 테스트
- [ ] 응답 품질 비교
- [ ] 문제 없으면 커밋
- [ ] 문제 있으면 롤백

## 팁

### 1. 빠른 프로토타이핑

```bash
# 1. YAML 파일 수정
vim backend/llm/prompts/default.yaml

# 2. 서버 재시작 (--reload 모드면 자동)
# 바로 새 프롬프트로 테스트!
```

### 2. 프롬프트 출력 확인

프롬프트는 `out/llm_prompt_*.txt`에 자동 저장됩니다:
```bash
# 최신 프롬프트 확인
ls -lt out/llm_prompt_*.txt | head -1

# 내용 확인
cat out/llm_prompt_20260118_*.txt
```

### 3. 응답 품질 비교

응답은 `out/llm_response_*.json`에 저장:
```bash
# 최신 응답들 비교
ls -lt out/llm_response_*.json | head -5
```

### 4. 전략별 성능 모니터링

```python
# 전략별 응답 시간, 토큰 사용량 기록
from prometheus_client import Summary

response_time_by_strategy = Summary(
    'llm_response_time_by_strategy',
    'LLM response time by prompt strategy',
    ['strategy']
)

def generate_with_monitoring(strategy: str):
    PromptBuilder.set_strategy(strategy)
    
    with response_time_by_strategy.labels(strategy=strategy).time():
        response = llm.generate_summary(...)
    
    return response
```

## 자주 묻는 질문

**Q: 프롬프트 변경이 즉시 반영되나요?**

A: `PromptBuilder._default_strategy = None`으로 캐시를 지우면 바로 반영됩니다. 또는 서버를 재시작하세요.

**Q: 여러 전략을 동시에 사용할 수 있나요?**

A: 네! 직접 PromptFactory를 사용하세요:
```python
strategy_a = PromptFactory.create(strategy="default")
strategy_b = PromptFactory.create(strategy="friendly")
```

**Q: 프롬프트 템플릿에 새 변수를 추가하려면?**

A: `PromptStrategy._format_*` 메서드를 수정하고, 템플릿에서 `{new_variable}` 사용하세요.

**Q: JSON 응답 형식을 바꾸려면?**

A: YAML 템플릿의 user_prompt_template에서 JSON 스키마를 수정하세요. LLM이 그대로 따라갑니다.
