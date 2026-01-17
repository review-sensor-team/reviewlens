#!/usr/bin/env python3
"""
공통 factor와 question 추가 스크립트
"""

import pandas as pd
from pathlib import Path

# 파일 경로
factor_file = Path('/Users/ssnko/app/python/reviewlens/backend/data/factor/reg_factor.csv')
question_file = Path('/Users/ssnko/app/python/reviewlens/backend/data/question/reg_question.csv')

# 기존 데이터 로드
df_factor = pd.read_csv(factor_file)
df_question = pd.read_csv(question_file)

print(f"기존 Factor: {len(df_factor)}개")
print(f"기존 Question: {len(df_question)}개")

# 모든 카테고리 가져오기
categories = df_factor['category'].unique()
print(f"\n카테고리: {list(categories)}")

# 공통 factor 정의
common_factors = [
    {
        'factor_key': 'delivery_packaging',
        'display_name': '배송/포장 상태',
        'description': '배송 중 파손, 포장 불량, 배송 지연 등의 요인',
        'anchor_terms': '배송|택배|포장|박스|파손|상자|배달|늦',
        'context_terms': '도착|받|포장|상자',
        'negation_terms': '빠름|완벽|괜찮|안전',
        'weight': 0.9
    },
    {
        'factor_key': 'as_service',
        'display_name': 'A/S 서비스',
        'description': '고객 서비스, 교환/환불 처리, A/S 대응 품질에 대한 불만',
        'anchor_terms': 'AS|A/S|서비스|고객센터|교환|환불|반품|수리|응대',
        'context_terms': '센터|문의|요청',
        'negation_terms': '친절|빠름|좋|만족',
        'weight': 1.2
    },
    {
        'factor_key': 'manual_usability',
        'display_name': '사용법/설명서',
        'description': '설명서 불친절, 사용법 복잡, 조작 어려움',
        'anchor_terms': '설명서|매뉴얼|사용법|복잡|어렵|모르겠|헷갈',
        'context_terms': '조작|사용|기능',
        'negation_terms': '쉽|간단|명확|잘',
        'weight': 0.8
    }
]

# 제품별 특화 factor
category_specific_factors = {
    'furniture': [
        {
            'factor_key': 'assembly_difficulty',
            'display_name': '조립 난이도',
            'description': '조립이 어렵거나 복잡한 요인',
            'anchor_terms': '조립|설치|어렵|복잡|힘들|시간',
            'context_terms': '조립|설치',
            'negation_terms': '쉽|간단|빠름',
            'weight': 1.1
        },
        {
            'factor_key': 'installation_service',
            'display_name': '설치/시공 품질',
            'description': '설치 기사 방문, 시공 품질에 대한 불만',
            'anchor_terms': '설치|시공|기사|방문|긁|파손',
            'context_terms': '설치|기사|방문',
            'negation_terms': '꼼꼼|친절|좋|만족',
            'weight': 1.2
        }
    ],
    'electronics': [
        {
            'factor_key': 'app_compatibility',
            'display_name': '앱 호환성',
            'description': '앱 연동, 호환성, 페어링 문제',
            'anchor_terms': '앱|어플|호환|연동|페어링|연결|안됨',
            'context_terms': '앱|어플리케이션|스마트폰',
            'negation_terms': '쉽|잘됨|완벽',
            'weight': 1.0
        }
    ],
    'appliance': [
        {
            'factor_key': 'smell_issue',
            'display_name': '냄새 문제',
            'description': '신제품 냄새, 작동 중 냄새 발생',
            'anchor_terms': '냄새|악취|향|냄|페인트|플라스틱',
            'context_terms': '사용|작동|처음',
            'negation_terms': '없|괜찮',
            'weight': 0.9
        },
        {
            'factor_key': 'safety_concern',
            'display_name': '안전 우려',
            'description': '화상, 과열, 안전 사고 우려',
            'anchor_terms': '화상|과열|뜨거|위험|안전|사고',
            'context_terms': '사용|작동',
            'negation_terms': '안전|괜찮',
            'weight': 1.3
        }
    ]
}

# 새로운 factor 추가
new_factors = []

# 공통 factor를 모든 카테고리에 추가
for category in categories:
    for factor in common_factors:
        new_factor = factor.copy()
        new_factor['category'] = category
        new_factors.append(new_factor)

# 카테고리별 특화 factor 추가
for category in categories:
    # furniture_ 로 시작하는 카테고리
    if category.startswith('furniture'):
        for factor in category_specific_factors['furniture']:
            new_factor = factor.copy()
            new_factor['category'] = category
            new_factors.append(new_factor)
    
    # electronics_ 로 시작하는 카테고리
    if category.startswith('electronics'):
        for factor in category_specific_factors['electronics']:
            new_factor = factor.copy()
            new_factor['category'] = category
            new_factors.append(new_factor)
    
    # appliance_ 로 시작하는 카테고리
    if category.startswith('appliance'):
        for factor in category_specific_factors['appliance']:
            new_factor = factor.copy()
            new_factor['category'] = category
            new_factors.append(new_factor)
    
    # robot_cleaner는 appliance로 취급
    if category == 'robot_cleaner':
        for factor in category_specific_factors['appliance']:
            new_factor = factor.copy()
            new_factor['category'] = category
            new_factors.append(new_factor)

# DataFrame 생성
df_new_factors = pd.DataFrame(new_factors)

# 중복 제거 (같은 category와 factor_key 조합)
existing_keys = set(zip(df_factor['category'], df_factor['factor_key']))
df_new_factors = df_new_factors[~df_new_factors.apply(lambda x: (x['category'], x['factor_key']) in existing_keys, axis=1)]

print(f"\n추가할 Factor: {len(df_new_factors)}개")

# Factor 병합 및 저장
df_combined_factors = pd.concat([df_factor, df_new_factors], ignore_index=True)
df_combined_factors.to_csv(factor_file, index=False, encoding='utf-8-sig')

print(f"✅ Factor 저장 완료: {len(df_combined_factors)}개")

# Question 추가
question_templates = {
    'delivery_packaging': '배송/포장 상태가 구매 결정에 중요한 요소인가요?',
    'as_service': 'A/S 서비스 품질이 중요한가요?',
    'manual_usability': '사용법이 쉬워야 하나요?',
    'assembly_difficulty': '조립이 쉬워야 하나요?',
    'installation_service': '설치 서비스 품질이 중요한가요?',
    'app_compatibility': '앱 연동이 원활해야 하나요?',
    'smell_issue': '냄새에 민감하신가요?',
    'safety_concern': '안전성이 중요한가요?'
}

# 기존 question의 최대 ID
max_q_id = df_question['question_id'].str.extract(r'Q(\d+)')[0].astype(int).max()

new_questions = []
unique_factor_keys = df_new_factors['factor_key'].unique()

for idx, factor_key in enumerate(unique_factor_keys, 1):
    if factor_key in question_templates:
        new_q = {
            'question_id': f'Q{max_q_id + idx}',
            'factor_key': factor_key,
            'question_text': question_templates[factor_key],
            'answer_type': 'single_choice',
            'choices': '매우 중요|보통|상관없음',
            'priority': max_q_id + idx,
            'next_factor_hint': factor_key
        }
        new_questions.append(new_q)

df_new_questions = pd.DataFrame(new_questions)

# 중복 제거
existing_q_keys = set(df_question['factor_key'])
df_new_questions = df_new_questions[~df_new_questions['factor_key'].isin(existing_q_keys)]

print(f"\n추가할 Question: {len(df_new_questions)}개")

# Question 병합 및 저장
df_combined_questions = pd.concat([df_question, df_new_questions], ignore_index=True)
df_combined_questions.to_csv(question_file, index=False, encoding='utf-8-sig')

print(f"✅ Question 저장 완료: {len(df_combined_questions)}개")

print("\n" + "="*80)
print("📝 추가된 Factor 요약")
print("="*80)
print("\n[공통 Factor - 모든 카테고리]")
for f in common_factors:
    print(f"  - {f['factor_key']}: {f['display_name']}")

print("\n[가구 특화 Factor]")
for f in category_specific_factors['furniture']:
    print(f"  - {f['factor_key']}: {f['display_name']}")

print("\n[전자제품 특화 Factor]")
for f in category_specific_factors['electronics']:
    print(f"  - {f['factor_key']}: {f['display_name']}")

print("\n[가전 특화 Factor]")
for f in category_specific_factors['appliance']:
    print(f"  - {f['factor_key']}: {f['display_name']}")
