#!/usr/bin/env python3
"""한글 factor_key를 영문으로 변경"""

import pandas as pd
from pathlib import Path

# 파일 경로
factor_file = Path('/Users/ssnko/app/python/reviewlens/backend/data/factor/reg_factor.csv')
question_file = Path('/Users/ssnko/app/python/reviewlens/backend/data/question/reg_question.csv')

# 한글 -> 영문 매핑
key_mapping = {
    '성능': 'performance',
    '고장_내구성': 'durability',
    '크기_무게': 'size_weight',
    '청소_관리': 'cleaning_maintenance',
    '물조절': 'water_control_issue',
    '소음': 'noise_level',
    '거품': 'foam_level'
}

print("="*80)
print("🔧 한글 factor_key를 영문으로 변경")
print("="*80)

# Factor CSV 수정
df_factor = pd.read_csv(factor_file)
print(f"\n기존 Factor 수: {len(df_factor)}")

korean_keys = [k for k in df_factor['factor_key'].unique() if any('\uac00' <= c <= '\ud7a3' for c in k)]
print(f"한글 factor_key: {korean_keys}")

for korean, english in key_mapping.items():
    df_factor.loc[df_factor['factor_key'] == korean, 'factor_key'] = english
    print(f"  {korean} → {english}")

df_factor.to_csv(factor_file, index=False, encoding='utf-8-sig')
print(f"\n✅ Factor CSV 저장 완료: {len(df_factor)}개")

# Question CSV 수정
df_question = pd.read_csv(question_file)
print(f"\n기존 Question 수: {len(df_question)}")

korean_q_keys = [k for k in df_question['factor_key'].unique() if any('\uac00' <= c <= '\ud7a3' for c in k)]
print(f"한글 factor_key: {korean_q_keys}")

for korean, english in key_mapping.items():
    df_question.loc[df_question['factor_key'] == korean, 'factor_key'] = english
    df_question.loc[df_question['next_factor_hint'] == korean, 'next_factor_hint'] = english
    print(f"  {korean} → {english}")

df_question.to_csv(question_file, index=False, encoding='utf-8-sig')
print(f"\n✅ Question CSV 저장 완료: {len(df_question)}개")

print("\n" + "="*80)
print("✅ 변경 완료!")
print("="*80)
