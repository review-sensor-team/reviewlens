# Contributing Guide

> **최종 업데이트**: 2026-01-18  
> **코드 품질**: 58% 코드 감소, 36개 헬퍼 함수 추출

## 기본 원칙
- **문서 우선 (Docs First)**: 코드 변경 전 문서화
- **Clean Architecture**: 명확한 레이어 분리 (Use Cases / Domain / Adapters)
- **인터페이스 기준 개발**: 타입 안전성 보장
- **모든 변경은 PR 기반**: 코드 리뷰 필수
- **단일 책임 원칙**: 함수는 40줄 이하, 복잡도 5 이하 권장
- **DRY 원칙**: 중복 코드 제거, 공통 로직은 constants.py

## 브랜치 전략
- `main`: 안정 버전 (프로덕션)
- `dev`: 통합 개발 (테스트 완료)
- `feature/*`: 기능 개발 (예: feature/#18-chat_bot_bug)
- `fix/*`: 긴급 수정 (예: fix/import-error-20260118)

## 코드 스타일

### Python
- **Import 순서**: 표준 라이브러리 → 서드파티 → 로컬 모듈
- **함수 크기**: 40줄 이하 권장 (복잡한 로직은 헬퍼 함수로 추출)
- **타입 힌트**: 모든 함수에 타입 힌트 추가
- **Docstring**: 공개 함수/클래스는 Google 스타일 docstring

### 리팩토링 가이드
1. **함수 크기 확인**: `python scripts/analyze_refactor.py` 실행
2. **40줄 이상 함수**: Extract Method 패턴으로 분리
3. **중복 코드**: DRY 원칙에 따라 공통 함수 추출
4. **내부 import**: 파일 상단으로 이동
5. **커밋 메시지**: "리팩토링: [함수명] - [변경 내용]"

## 레이어별 책임

### Domain Layer (`domain/rules/`)
- **순수 비즈니스 로직**: 외부 의존성 없음
- 예: 텍스트 정규화, 스코어링 규칙, 리뷰 추출 로직

### Use Cases Layer (`usecases/`)
- **애플리케이션 로직**: 대화 플로우, 상태 관리
- Domain과 Adapters 조합

### Adapters Layer (`adapters/`)
- **외부 연동**: CSV 파일, 데이터베이스, API
- Domain에 의존하지만 Use Cases에 의존되지 않음
