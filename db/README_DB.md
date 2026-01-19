# ReviewLens – Database (Architecture · Operation · Analytics)

본 문서는 ReviewLens 프로젝트의 **Database 설계, 초기화, 운영, 분석 가능 범위**를 정리한다.
DB는 **Docker 기반 PostgreSQL + Redis**로 구성되며, **GUI 없이 스크립트 중심 운영**을 전제로 한다.

---
## Prerequisites

- Docker Desktop (WSL2 backend)
- Python 3.10+


---
## Quick smoke test (DB end-to-end)

아래 3단계로 DB 파이프라인이 정상 동작하는지 확인할 수 있습니다.

```bash
# 1) DB 컨테이너 초기화 (기존 데이터 제거 후 재기동)
docker compose -f docker-compose.db.yml down -v
docker compose -f docker-compose.db.yml up -d

# 2) 스키마 적용 + Reference 데이터 적재 + 검증 출력
.\.venv\Scripts\python.exe db\scripts\init_db.py

# 3) DB export / backup 결과 생성
.\.venv\Scripts\python.exe db\scripts\export_db_artifacts.py


---

## 1. DB 구성 개요

### Containers

* **PostgreSQL 16**

  * Reference Data (정적 기준 데이터)
  * Runtime Data (대화 로그 / 분석용)
* **Redis 7**

  * 세션/속도용 보조 저장소

DB는 `docker-compose.db.yml` 기준으로 **독립 기동**된다.

---

## 2. 디렉터리 구조 (DB 관련)

```
db/
 ├─ schema/
 │   ├─ schema_reference.sql   # Reference schema
 │   └─ schema_runtime.sql     # Runtime / Analytics schema
 │
 └─ scripts/
     ├─ init_db.py             # 단일 진입점 (schema + reference 적재 + 검증)
     ├─ load_reference_data.py # Reference Data 적재 로직
     └─ export_db_artifacts.py # Export / Backup 자동화

backend/
 └─ data/
     └─ reference/
         ├─ reg_factor_v4.csv
         │   # 초기 factor 정의 버전
         │
         ├─ reg_factor_v4_1.csv
         │   # v4 확장본
         │   # - product_no, factor_seq 컬럼 추가
         │   # - Reference DB 적재에 실제로 사용되는 파일
         │
         ├─ reg_question_v6.csv
         │   # 대화 질문 템플릿 (factor_id 기준)
         │
         └─ {product_no}_reviews_smartstore_*.json
             # 상품별 리뷰 원문
             # 파일명에서 product_no를 파싱하여 DB 적재

out/
 ├─ db_exports/   # CSV export 결과 (공유/확인용)
 └─ db_backups/   # DB 전체 스냅샷 (pg_dump)
```

* `out/` 하위는 **자동 생성 산출물(artifact)**
* 현재 단계에서는 **공유 목적**으로 커밋됨

---

## 3. Schema 설계 원칙

### Reference Schema (`schema_reference.sql`)

* `ref_products`
* `ref_factors`
* `ref_questions`
* `ref_reviews`
* `reference_data_versions`
  → Reference 적재 **실행 이력용 append-only 로그**

### Runtime Schema (`schema_runtime.sql`)

* `dialogue_sessions`
* `dialogue_turns`
* `llm_runs`

**Reference / Runtime을 물리적으로 분리**하여

* 기준 데이터 안정성
* 실험/로그 유연성
  을 동시에 확보한다.

---

## 4. DB Lifecycle (기동 및 초기화)

### DB 기동

```bash
docker compose -f docker-compose.db.yml up -d
```

### DB 초기화 (최초 1회 실행)

```bash
python db/scripts/init_db.py
```

이 스크립트는 다음을 수행한다.

1. Reference Schema 적용 (`schema_reference.sql`)
2. Runtime Schema 적용 (`schema_runtime.sql`)
3. Reference Data 적재 (products / factors / questions / reviews)
4. 적재 결과 검증 출력

> DB를 “준비”하는 단계이며, 일반적인 개발/실행 과정에서 반복 수행하지 않는다.

---

## 5. Application Integration (개발 연동 절차)

DB가 준비된 이후, 애플리케이션은 아래 기준으로 연동한다.

* **Reference Data 조회**: `ref_*` 테이블
* **대화/실행 로그 기록**:

  * `dialogue_sessions`
  * `dialogue_turns`
  * `llm_runs`

CSV/JSON 파일을 직접 로딩하지 않고 **DB 조회 기준**으로 연동한다.
DB 초기화(`init_db.py`)는 다시 실행할 필요 없다.

---

## 6. Environment & Credentials

PostgreSQL은 Docker 컨테이너로 기동되며,
접속 계정 및 비밀번호는 로컬 `.env` 값으로 주입된다.

* 별도의 DB 계정 생성 작업은 필요 없다.
* 개발 환경에서는 동일한 비밀번호를 사용해도 무방하다.

---

## 7. DB Verification (GUI 없이)

```bash
docker compose -f docker-compose.db.yml exec postgres \
  psql -U postgres -d reviewlens -c "\dt"
```

```bash
docker compose -f docker-compose.db.yml exec postgres \
  psql -U postgres -d reviewlens \
  -c "select product_no, count(*) from ref_reviews group by product_no order by product_no;"
```

---

## 8. Export / Backup (권장 워크플로우)

### 실행

```bash
python db/scripts/export_db_artifacts.py
```

### 결과물

* `out/db_exports/`

  * 테이블별 CSV (구조/데이터 확인 및 초기 공유용)
* `out/db_backups/reviewlens_dump.sql`

  * DB 전체 스냅샷 (완전 복원용)

---

## 9. `reviewlens_dump.sql`의 의미

`reviewlens_dump.sql`은 **특정 시점의 ReviewLens DB 전체를 그대로 저장한 스냅샷**이다.

* 스키마 + 데이터 포함
* PostgreSQL만 있으면 **완전 복원 가능**
* 논의/리뷰 기준 시점을 고정하는 **타임캡슐 역할**

### 복원 예시

```bash
docker compose -f docker-compose.db.yml exec -T postgres \
  psql -U postgres -d reviewlens < out/db_backups/reviewlens_dump.sql

```
> Docker 기반 PostgreSQL 컨테이너에
> 특정 시점의 DB 스냅샷(`reviewlens_dump.sql`)을 그대로 복원한다.

---

## 10. 운영 정책 요약

* Reference Data는 **읽기 전용**
* Reference 변경 시:

  * CSV/JSON 교체 → `init_db.py` 재실행
* 초기화 필요 시:

  * 테이블 DROP 대신 **Docker volume 재생성**
* Export/Backup 산출물은:

  * 공유 목적
  * 운영 의존 대상 아님

---

## 11. 요약

> **Reference DB는 판단의 기준점이고,
> Runtime DB는 서비스 품질을 증명하는 근거다.**

현재 구성은:

* DB 자동화 진입점 단일화
* Reference / Runtime 역할 분리
* GUI 없이 운영·검증·공유 가능

을 목표로 설계되었다.

---

## 12. Analytics Overview (이 DB로 가능한 분석)

이 DB 구조를 통해 다음을 정량적으로 분석할 수 있다.

- 평균 대화 턴 수 및 수렴 비율
- 질문별 이탈 지점
- 상품별 최종 regret factor 분포
- LLM 성공/에러/fallback 비율

Reference DB는 판단의 기준점이며,  
Runtime DB는 서비스 품질을 검증하는 근거로 사용된다.