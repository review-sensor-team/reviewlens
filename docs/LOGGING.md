# ReviewLens 로깅 시스템

## 개요

ReviewLens는 전체 파이프라인을 모니터링할 수 있는 중앙집중식 로깅 시스템을 제공합니다.

## 로그 파일 구조

### 로그 디렉토리
모든 로그는 `logs/` 디렉토리에 저장됩니다.

### 로그 파일 종류

1. **app.log** - 전체 애플리케이션 로그 (DEBUG 레벨 이상)
   - 모든 모듈의 상세 로그
   - 파일 크기: 최대 10MB, 백업 5개

2. **error.log** - 에러 로그 (ERROR 레벨 이상)
   - 에러 및 크리티컬 이벤트만 기록
   - 문제 해결 시 가장 먼저 확인

3. **api.log** - API 요청 로그
   - 세션 시작/종료
   - 메시지 송수신
   - 리뷰 수집 요청
   - API 에러 추적

4. **pipeline.log** - 파이프라인 실행 로그
   - DialogueSession 초기화
   - Factor 점수 계산
   - 증거 리뷰 추출
   - 질문 생성 과정

5. **collector.log** - 리뷰 수집 로그
   - SmartStore 크롤링 과정
   - Factor 분석 결과
   - Selenium 드라이버 상태

## 로그 레벨

### 콘솔 출력
- INFO 레벨 이상만 출력
- 간단한 포맷으로 실시간 확인

### 파일 로그
- DEBUG 레벨부터 모든 로그 기록
- 상세한 포맷으로 추적 가능

## 로그 포맷

```
[2026-01-03 14:30:45] INFO     [api.chat:send_message:52] [메시지 수신] session_id=abc123, message=가습 성능이 좋나요?...
```

- **타임스탬프**: [YYYY-MM-DD HH:MM:SS]
- **로그 레벨**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **모듈 정보**: [모듈명:함수명:라인번호]
- **메시지**: 구체적인 이벤트 설명

## 주요 로깅 포인트

### 1. API Layer (`api.chat`)
```python
logger.info(f"[세션 시작] category={request.category}")
logger.info(f"[메시지 수신] session_id={request.session_id}, message={request.message[:50]}...")
logger.info(f"[리뷰 수집 시작] url={request.product_url}, max={request.max_reviews}")
```

### 2. Dialogue Pipeline (`pipeline.dialogue`)
```python
logger.info(f"[DialogueSession 초기화] category={category}, data_dir={data_dir}")
logger.info(f"[턴 {self.turn_count}] 사용자 메시지: {user_message[:50]}...")
logger.info(f"[대화 종료] 최종 top factors: {top_factors}")
```

### 3. Sensor (`pipeline.sensor`)
```python
logger.info(f"[Factor 점수 계산 시작] reviews={len(df)}, factors={len(factors)}")
logger.info(f"[Factor 점수 계산 완료] factor_counts={sum(factor_counts.values())} 총 매칭")
```

### 4. Retrieval (`pipeline.retrieval`)
```python
logger.info(f"[증거 리뷰 추출] top_factors={len(top_factors)}, max_total={max_total_evidence}")
logger.debug(f"  - factors: {[k for k, _ in top_factors]}")
```

### 5. Collector (`collector.smartstore`, `collector.factor_analyzer`)
```python
logger.info(f"[SmartStoreCollector 초기화] url={product_url}, headless={headless}")
logger.info(f"[리뷰 수집 시작] max={max_reviews}, sort_by_low_rating={sort_by_low_rating}")
logger.info(f"[FactorAnalyzer 초기화] category={category}")
```

## 로그 모니터링 방법

### 실시간 로그 확인
```bash
# 전체 로그
tail -f logs/app.log

# API 로그
tail -f logs/api.log

# 파이프라인 로그
tail -f logs/pipeline.log

# 에러만 확인
tail -f logs/error.log

# 수집기 로그
tail -f logs/collector.log
```

### 특정 키워드 검색
```bash
# 세션 관련 로그
grep "세션" logs/app.log

# 에러 추적
grep "ERROR" logs/app.log

# 특정 session_id 추적
grep "abc123" logs/api.log
```

### 최근 에러 확인
```bash
# 최근 20줄
tail -20 logs/error.log

# 오늘 발생한 에러
grep "$(date +%Y-%m-%d)" logs/error.log
```

## 로그 관리

### 자동 로테이션
- 각 로그 파일은 10MB 도달 시 자동 로테이션
- 최대 5개의 백업 파일 유지
- 오래된 파일은 자동 삭제

### 수동 정리
```bash
# 오래된 로그 삭제 (7일 이상)
find logs/ -name "*.log.*" -mtime +7 -delete

# 모든 로그 초기화
rm logs/*.log*
```

## 디버깅 팁

### 1. API 요청 추적
```bash
# 특정 세션의 전체 흐름 추적
grep "session_id=abc123" logs/api.log | less
```

### 2. 대화 흐름 분석
```bash
# 턴별 진행 확인
grep "^\[.*\] INFO.*\[턴" logs/pipeline.log
```

### 3. Factor 매칭 확인
```bash
# 어떤 factor가 매칭되었는지 확인
grep "매칭된 factors" logs/pipeline.log
```

### 4. 성능 분석
```bash
# 각 단계별 소요 시간 확인 (타임스탬프 비교)
grep "시작\|완료" logs/app.log
```

## 로그 레벨 조정

### 개발 환경
- 기본: DEBUG (모든 로그 기록)
- 상세한 추적 정보 필요 시 유용

### 프로덕션 환경
`backend/core/logging_config.py` 수정:
```python
# 콘솔 출력 레벨 상향
console_handler.setLevel(logging.WARNING)

# 파일 로그 레벨 상향
app_handler.setLevel(logging.INFO)
```

## 외부 라이브러리 로그

기본적으로 노이즈를 줄이기 위해 일부 라이브러리 로그는 제한됩니다:

```python
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("fastapi").setLevel(logging.INFO)
```

필요 시 `backend/core/logging_config.py`에서 조정 가능합니다.

## 문제 해결

### 로그가 기록되지 않는 경우
1. `logs/` 디렉토리 존재 확인
2. 파일 쓰기 권한 확인
3. 디스크 공간 확인

### 로그가 너무 많은 경우
1. 콘솔 로그 레벨을 WARNING으로 상향
2. DEBUG 로그가 필요 없는 모듈의 레벨 조정
3. 로그 로테이션 설정 확인

### 로그에서 특정 정보를 찾기 어려운 경우
1. 구조화된 로그 검색 도구 사용 (예: `jq`, `lnav`)
2. 로그 집계 도구 도입 검토 (예: ELK Stack, Grafana Loki)
