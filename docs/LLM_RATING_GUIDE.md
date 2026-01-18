# LLM 응답 평가 시스템 가이드

## 개요

LLM 응답에 대한 사용자 별점 평가 시스템입니다. 다양한 프롬프트 전략(default, concise, detailed, friendly)의 효과를 A/B 테스트하고, 데이터 기반으로 최적 전략을 결정할 수 있습니다.

## 주요 기능

### 1. 응답 파일 자동 생성

LLM이 요약을 생성하면 자동으로 응답 파일이 저장됩니다:

**단일 전략:**
```
out/llm_response_20260118_123456.json
```

**다중 전략:**
```
out/llm_response_default_20260118_123456.json
out/llm_response_friendly_20260118_123457.json
out/llm_response_detailed_20260118_123458.json
```

### 2. 응답 파일 구조

```json
{
  "analysis_summary": "...",
  "key_factors": [...],
  "recommendations": [...],
  "_metadata": {
    "product_name": "삼성 갤럭시 버즈",
    "timestamp": "20260118_123456",
    "model": "claude-3-5-sonnet-20241022",
    "provider": "ClaudeLLMClient",
    "strategy": "default"  // 다중 전략인 경우에만
  },
  "_user_rating": {
    "default": {
      "rating": 5,
      "rated_at": "2026-01-18T12:35:00",
      "strategy": "default",
      "feedback": "매우 명확하고 유용했습니다"
    }
  }
}
```

### 3. API 엔드포인트

#### POST /api/v2/reviews/rate-response

LLM 응답에 평가를 추가합니다.

**요청:**
```bash
curl -X POST http://localhost:8000/api/v2/reviews/rate-response \
  -H "Content-Type: application/json" \
  -d '{
    "response_file": "llm_response_default_20260118_123456.json",
    "rating": 5,
    "strategy": "default",
    "feedback": "매우 명확하고 유용했습니다"
  }'
```

**요청 파라미터:**
- `response_file` (필수): 응답 파일명
- `rating` (필수): 1-5 별점
- `strategy` (선택): 전략 이름 (다중 전략일 경우 필수)
- `feedback` (선택): 텍스트 피드백

**응답:**
```json
{
  "success": true,
  "message": "평가가 저장되었습니다",
  "response_file": "llm_response_default_20260118_123456.json",
  "rating": 5
}
```

## 사용 예시

### 예시 1: 단일 전략 평가

```bash
# 1. 제품 분석 실행
curl -X POST http://localhost:8000/api/v2/reviews/analyze-product \
  -H "Content-Type: application/json" \
  -d '{
    "product_url": "https://smartstore.naver.com/...",
    "category_slug": "earbuds"
  }'

# 2. 응답에서 response_file 확인
# {
#   "analysis": {
#     "response_file": "llm_response_20260118_123456.json",
#     "llm_summary": "{...}"
#   }
# }

# 3. 평가 제출
curl -X POST http://localhost:8000/api/v2/reviews/rate-response \
  -H "Content-Type: application/json" \
  -d '{
    "response_file": "llm_response_20260118_123456.json",
    "rating": 4,
    "feedback": "내용은 좋은데 좀 길어요"
  }'
```

### 예시 2: 다중 전략 평가

```bash
# .env 설정
PROMPT_STRATEGY=default,friendly,concise

# 1. 제품 분석 실행
curl -X POST http://localhost:8000/api/v2/reviews/analyze-product \
  -H "Content-Type: application/json" \
  -d '{
    "product_url": "https://smartstore.naver.com/...",
    "category_slug": "earbuds"
  }'

# 2. 응답에서 각 전략의 response_file 확인
# {
#   "analysis": {
#     "llm_summaries": [
#       {
#         "strategy": "default",
#         "summary": "{...}",
#         "response_file": "llm_response_default_20260118_123456.json"
#       },
#       {
#         "strategy": "friendly",
#         "summary": "{...}",
#         "response_file": "llm_response_friendly_20260118_123457.json"
#       },
#       {
#         "strategy": "concise",
#         "summary": "{...}",
#         "response_file": "llm_response_concise_20260118_123458.json"
#       }
#     ]
#   }
# }

# 3. 각 전략별로 평가 제출
curl -X POST http://localhost:8000/api/v2/reviews/rate-response \
  -H "Content-Type: application/json" \
  -d '{
    "response_file": "llm_response_default_20260118_123456.json",
    "rating": 4,
    "strategy": "default",
    "feedback": "전문적이지만 딱딱함"
  }'

curl -X POST http://localhost:8000/api/v2/reviews/rate-response \
  -H "Content-Type: application/json" \
  -d '{
    "response_file": "llm_response_friendly_20260118_123457.json",
    "rating": 5,
    "strategy": "friendly",
    "feedback": "친근하고 이해하기 쉬워요!"
  }'

curl -X POST http://localhost:8000/api/v2/reviews/rate-response \
  -H "Content-Type: application/json" \
  -d '{
    "response_file": "llm_response_concise_20260118_123458.json",
    "rating": 3,
    "strategy": "concise",
    "feedback": "너무 짧아서 정보가 부족함"
  }'
```

## A/B 테스트 데이터 분석

### 평가 데이터 수집

```bash
# 특정 전략의 평가 데이터 추출
cat out/llm_response_default_*.json | jq '._user_rating.default.rating'

# 모든 전략의 평균 별점 계산
for strategy in default friendly concise detailed; do
  echo "=== $strategy ==="
  cat out/llm_response_${strategy}_*.json 2>/dev/null | \
    jq -r "._user_rating.${strategy}.rating" | \
    awk '{sum+=$1; count++} END {if(count>0) print sum/count; else print "No data"}'
done
```

### Python 스크립트 예시

```python
import json
from pathlib import Path
from collections import defaultdict

def analyze_ratings():
    """평가 데이터 분석"""
    out_dir = Path("out")
    
    # 전략별 평가 수집
    ratings = defaultdict(list)
    feedbacks = defaultdict(list)
    
    for response_file in out_dir.glob("llm_response_*.json"):
        with open(response_file) as f:
            data = json.load(f)
        
        # 메타데이터에서 전략 확인
        strategy = data.get("_metadata", {}).get("strategy", "default")
        
        # 평가 데이터 추출
        user_ratings = data.get("_user_rating", {})
        
        for strat, rating_data in user_ratings.items():
            ratings[strat].append(rating_data["rating"])
            if "feedback" in rating_data:
                feedbacks[strat].append(rating_data["feedback"])
    
    # 통계 출력
    print("=== 전략별 평가 통계 ===\n")
    
    for strategy in sorted(ratings.keys()):
        rating_list = ratings[strategy]
        feedback_list = feedbacks[strategy]
        
        avg_rating = sum(rating_list) / len(rating_list)
        
        print(f"전략: {strategy}")
        print(f"  평가 수: {len(rating_list)}")
        print(f"  평균 별점: {avg_rating:.2f}")
        print(f"  최고 별점: {max(rating_list)}")
        print(f"  최저 별점: {min(rating_list)}")
        print(f"  피드백 수: {len(feedback_list)}")
        print()
    
    # 최고 전략 추천
    if ratings:
        best_strategy = max(ratings.keys(), 
                          key=lambda s: sum(ratings[s])/len(ratings[s]))
        print(f"✅ 추천 전략: {best_strategy}")
        print(f"   평균 별점: {sum(ratings[best_strategy])/len(ratings[best_strategy]):.2f}")

if __name__ == "__main__":
    analyze_ratings()
```

### 실행:
```bash
python scripts/analyze_ratings.py
```

**출력 예시:**
```
=== 전략별 평가 통계 ===

전략: concise
  평가 수: 15
  평균 별점: 3.47
  최고 별점: 5
  최저 별점: 2
  피드백 수: 12

전략: default
  평가 수: 20
  평균 별점: 4.15
  최고 별점: 5
  최저 별점: 3
  피드백 수: 18

전략: friendly
  평가 수: 18
  평균 별점: 4.56
  최고 별점: 5
  최저 별점: 4
  피드백 수: 15

✅ 추천 전략: friendly
   평균 별점: 4.56
```

## 프론트엔드 통합

### 단일 전략 UI 예시

```javascript
// API 응답
const analysis = response.data.analysis;

// 응답 표시
document.getElementById('llm-summary').innerHTML = 
  formatSummary(analysis.llm_summary);

// 별점 평가 UI
showRatingWidget({
  responseFile: analysis.response_file,
  onRate: async (rating, feedback) => {
    await fetch('/api/v2/reviews/rate-response', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        response_file: analysis.response_file,
        rating,
        feedback
      })
    });
  }
});
```

### 다중 전략 UI 예시

```javascript
// API 응답
const summaries = response.data.analysis.llm_summaries;

// 각 전략별 탭/카드 렌더링
summaries.forEach((item, index) => {
  const card = createStrategyCard({
    title: item.strategy,
    content: formatSummary(item.summary),
    responseFile: item.response_file,
    onRate: async (rating, feedback) => {
      await fetch('/api/v2/reviews/rate-response', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          response_file: item.response_file,
          rating,
          strategy: item.strategy,
          feedback
        })
      });
      
      showThankYouMessage();
    }
  });
  
  document.getElementById('strategies-container').appendChild(card);
});
```

## 데이터 구조

### 평가 데이터 (_user_rating)

```typescript
interface UserRating {
  [strategy: string]: {
    rating: number;           // 1-5
    rated_at: string;         // ISO 8601 timestamp
    strategy?: string;        // 전략 이름
    feedback?: string;        // 선택적 피드백
  };
}
```

### 메타데이터 (_metadata)

```typescript
interface ResponseMetadata {
  product_name: string;
  timestamp: string;         // YYYYMMDD_HHMMSS
  model: string;             // LLM 모델명
  provider: string;          // LLM 공급자
  strategy?: string;         // 전략 (다중 전략인 경우)
}
```

## 모범 사례

### 1. 충분한 데이터 수집
- 각 전략당 최소 20개 이상의 평가 수집
- 다양한 제품 카테고리에서 테스트

### 2. 피드백 활용
- 별점만으로는 개선 방향 파악 어려움
- 구체적인 피드백 수집 권장

### 3. 주기적 분석
- 주 단위로 데이터 분석
- 전략 효과 트렌드 모니터링

### 4. 점진적 롤아웃
- 새 전략은 소수 사용자에게 먼저 테스트
- 평가 좋으면 점진적 확대

## 문제 해결

### 파일을 찾을 수 없음 (404)
```bash
# out 디렉토리 확인
ls -la out/llm_response_*.json

# 파일명 정확히 확인
cat response.json | jq '.analysis.response_file'
```

### 별점 범위 오류 (400)
- rating은 1-5 사이 정수만 허용
- 요청 본문 확인: `"rating": 5` (문자열 아님)

### 다중 전략 평가 실패
- `strategy` 필드 필수 (다중 전략인 경우)
- response_file과 strategy가 일치해야 함

## 관련 문서

- [프롬프트 팩토리 가이드](PROMPT_FACTORY_GUIDE.md)
- [다중 전략 가이드](MULTI_STRATEGY_GUIDE.md)
- [프롬프트 실험 가이드](PROMPT_EXPERIMENT_GUIDE.md)
