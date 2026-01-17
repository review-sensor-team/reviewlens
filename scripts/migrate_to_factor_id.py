#!/usr/bin/env python3
"""
factor_key (문자열) → factor_id (숫자) 마이그레이션 스크립트

수행 작업:
1. reg_factor.csv에 factor_id 컬럼 추가 (1부터 시작하는 auto-increment)
2. reg_question.csv의 factor_key를 factor_id로 변경
3. 기존 데이터 백업
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

# 경로 설정
BASE_DIR = Path(__file__).parent.parent
FACTOR_CSV = BASE_DIR / "backend/data/factor/reg_factor.csv"
QUESTION_CSV = BASE_DIR / "backend/data/question/reg_question.csv"

# 백업 디렉토리
BACKUP_DIR = BASE_DIR / "backend/data/backup"
BACKUP_DIR.mkdir(exist_ok=True)

def backup_files():
    """기존 파일 백업"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"📦 백업 생성: {timestamp}")
    
    # reg_factor.csv 백업
    backup_factor = BACKUP_DIR / f"reg_factor_{timestamp}.csv"
    pd.read_csv(FACTOR_CSV).to_csv(backup_factor, index=False, encoding='utf-8-sig')
    print(f"  ✓ {backup_factor}")
    
    # reg_question.csv 백업
    backup_question = BACKUP_DIR / f"reg_question_{timestamp}.csv"
    pd.read_csv(QUESTION_CSV).to_csv(backup_question, index=False, encoding='utf-8-sig')
    print(f"  ✓ {backup_question}")

def migrate_factor_csv():
    """reg_factor.csv에 factor_id 추가"""
    print("\n🔧 reg_factor.csv 마이그레이션")
    
    df = pd.read_csv(FACTOR_CSV)
    
    # factor_id 컬럼 추가 (1부터 시작)
    df.insert(0, 'factor_id', range(1, len(df) + 1))
    
    # factor_key와 factor_id 매핑 저장 (question CSV에서 사용)
    factor_map = dict(zip(df['factor_key'], df['factor_id']))
    
    # 컬럼 순서: factor_id, factor_key, category, ...
    cols = ['factor_id', 'factor_key'] + [c for c in df.columns if c not in ['factor_id', 'factor_key']]
    df = df[cols]
    
    # 저장
    df.to_csv(FACTOR_CSV, index=False, encoding='utf-8-sig')
    print(f"  ✓ {len(df)}개 factor에 ID 부여 (1~{len(df)})")
    
    # 샘플 출력
    print("\n  📋 샘플:")
    for _, row in df.head(5).iterrows():
        print(f"    {row['factor_id']:3d} | {row['factor_key']:30s} | {row['display_name']}")
    
    return factor_map

def migrate_question_csv(factor_map):
    """reg_question.csv의 factor_key를 factor_id로 변경"""
    print("\n🔧 reg_question.csv 마이그레이션")
    
    df = pd.read_csv(QUESTION_CSV)
    
    # factor_key → factor_id 변환
    df['factor_id'] = df['factor_key'].map(factor_map)
    
    # factor_key가 매핑되지 않은 경우 확인
    unmapped = df[df['factor_id'].isna()]
    if not unmapped.empty:
        print(f"  ⚠️  매핑되지 않은 factor_key 발견:")
        for key in unmapped['factor_key'].unique():
            print(f"    - {key}")
        raise ValueError("매핑되지 않은 factor_key가 있습니다. reg_factor.csv를 확인하세요.")
    
    # factor_id를 정수로 변환
    df['factor_id'] = df['factor_id'].astype(int)
    
    # 컬럼 순서 재조정: question_id, factor_id, factor_key(참고용), ...
    # factor_key는 참고용으로 유지 (나중에 제거 가능)
    cols = ['question_id', 'factor_id', 'factor_key'] + [c for c in df.columns if c not in ['question_id', 'factor_id', 'factor_key']]
    df = df[cols]
    
    # 저장
    df.to_csv(QUESTION_CSV, index=False, encoding='utf-8-sig')
    print(f"  ✓ {len(df)}개 question의 factor_key → factor_id 변환 완료")
    
    # 샘플 출력
    print("\n  📋 샘플:")
    for _, row in df.head(5).iterrows():
        print(f"    Q{row['question_id']:4d} | F{row['factor_id']:3d} | {row['factor_key']:30s}")

def verify_migration():
    """마이그레이션 결과 검증"""
    print("\n✅ 마이그레이션 검증")
    
    df_factor = pd.read_csv(FACTOR_CSV)
    df_question = pd.read_csv(QUESTION_CSV)
    
    # 1. factor_id 유니크 확인
    if df_factor['factor_id'].nunique() != len(df_factor):
        raise ValueError("factor_id에 중복이 있습니다!")
    print("  ✓ factor_id 중복 없음")
    
    # 2. factor_id 연속성 확인
    expected_ids = set(range(1, len(df_factor) + 1))
    actual_ids = set(df_factor['factor_id'])
    if expected_ids != actual_ids:
        missing = expected_ids - actual_ids
        raise ValueError(f"factor_id가 연속적이지 않습니다. 누락: {missing}")
    print(f"  ✓ factor_id 연속적 (1~{len(df_factor)})")
    
    # 3. question의 factor_id가 모두 유효한지 확인
    valid_factor_ids = set(df_factor['factor_id'])
    question_factor_ids = set(df_question['factor_id'])
    invalid = question_factor_ids - valid_factor_ids
    if invalid:
        raise ValueError(f"question에 유효하지 않은 factor_id가 있습니다: {invalid}")
    print(f"  ✓ 모든 question의 factor_id 유효 ({len(question_factor_ids)}개 factor 참조)")
    
    # 4. 통계
    print(f"\n  📊 통계:")
    print(f"    - 총 Factor: {len(df_factor)}개")
    print(f"    - 총 Question: {len(df_question)}개")
    print(f"    - Factor당 평균 질문 수: {len(df_question) / len(df_factor):.1f}개")

def main():
    """메인 마이그레이션 프로세스"""
    print("=" * 60)
    print("🔄 Factor Key → Factor ID 마이그레이션")
    print("=" * 60)
    
    # 1. 백업
    backup_files()
    
    # 2. Factor CSV 마이그레이션
    factor_map = migrate_factor_csv()
    
    # 3. Question CSV 마이그레이션
    migrate_question_csv(factor_map)
    
    # 4. 검증
    verify_migration()
    
    print("\n" + "=" * 60)
    print("✅ 마이그레이션 완료!")
    print("=" * 60)
    print("\n다음 단계:")
    print("  1. 백엔드 코드에서 factor_key → factor_id 변경")
    print("  2. Factor, Question 모델 업데이트")
    print("  3. 모든 파이프라인 코드에서 factor_id 사용하도록 변경")
    print("  4. 테스트 후 question CSV에서 factor_key 컬럼 제거 고려\n")

if __name__ == "__main__":
    main()
