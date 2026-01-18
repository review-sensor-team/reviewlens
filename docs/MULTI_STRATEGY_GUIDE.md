# 다중 프롬프트 전략 예시

## 단일 전략 (기존)
```bash
PROMPT_STRATEGY=default
```

## 다중 전략 (새 기능)
```bash
# 기본 + 친근한 스타일 동시에
PROMPT_STRATEGY=default,friendly

# 간결 + 상세 비교
PROMPT_STRATEGY=concise,detailed

# 모든 전략 한번에 (권장하지 않음 - 비용 증가)
PROMPT_STRATEGY=default,concise,detailed,friendly
```

## 응답 형식

### 단일 전략
```json
{
  "llm_summary": "{...}",
  "top_factors": [...],
  "evidence_reviews": [...]
}
```

### 다중 전략
```json
{
  "llm_summaries": [
    {
      "strategy": "default",
      "summary": "{...}"
    },
    {
      "strategy": "friendly",
      "summary": "{...}"
    }
  ],
  "llm_summary": "{...}",  // 첫 번째 전략 (호환성)
  "top_factors": [...],
  "evidence_reviews": [...]
}
```

## 사용 시나리오

### A/B 테스트
```bash
# 두 스타일을 동시에 제공하고 사용자 피드백 수집
PROMPT_STRATEGY=default,friendly
```

### 타겟별 맞춤
```bash
# 전문가용 + 일반인용
PROMPT_STRATEGY=detailed,concise
```

### 디버깅/개발
```bash
# 여러 전략 비교
PROMPT_STRATEGY=default,concise,detailed
```

## 주의사항

- 전략 개수만큼 LLM API 호출 → 비용 증가
- 응답 시간도 비례해서 증가
- 프로덕션에서는 1-2개 전략 권장
