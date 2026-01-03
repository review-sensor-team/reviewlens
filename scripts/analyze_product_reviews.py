"""
제품 리뷰를 수집하고 분석하여 reg_factor와 reg_question을 자동 생성하는 스크립트

사용법:
    python scripts/analyze_product_reviews.py <product_url> [--max-reviews 200] [--category category_name] [--product-name product_name]

예시:
    python scripts/analyze_product_reviews.py https://brand.naver.com/everybot/products/11163824445 --category robot_cleaner --product-name edge
    python scripts/analyze_product_reviews.py https://brand.naver.com/nespressokorea/products/5762090671 --category coffee_machine --product-name vertuo_plus
"""
import sys
import argparse
import pandas as pd
import json
from pathlib import Path
from collections import Counter
from datetime import datetime
import re

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.collector.smartstore_collector import SmartStoreCollector


def extract_keywords_from_reviews(df, min_rating=3):
    """리뷰에서 주요 키워드와 문제점 추출"""
    
    # 낮은 별점 리뷰
    low_rating = df[df['rating'] <= min_rating]
    
    # 부정적 키워드 카테고리
    issue_patterns = {
        '소음': ['소음', '시끄럽', '웅웅', '소리', '조용'],
        '가격/비용': ['비싸', '비용', '가격', '부담', '비싼'],
        '성능': ['약하', '느리', '별로', '아쉽', '기대', '생각보다'],
        '고장/내구성': ['고장', '문제', '오류', 'AS', '수리', '망가', '안됨', '작동'],
        '청소/관리': ['청소', '관리', '귀찮', '번거로', '세척', '물때'],
        '크기/무게': ['크', '무겁', '작', '크기', '공간'],
        '배터리': ['배터리', '충전', '사용시간', '방전'],
        '물조절': ['물', '양', '조절', '추가', '마음대로'],
        '거품': ['거품', '크레마', '두껍', '많'],
    }
    
    # 모든 리뷰 텍스트
    all_text = ' '.join(df['text'].tolist())
    low_rating_text = ' '.join(low_rating['text'].tolist()) if len(low_rating) > 0 else ''
    
    # 이슈별 언급 횟수
    issue_counts = {}
    for issue, keywords in issue_patterns.items():
        count = sum(all_text.count(kw) for kw in keywords)
        if count > 0:
            issue_counts[issue] = count
    
    return issue_counts, low_rating


def generate_factors(product_url, df, category_name=None):
    """수집된 리뷰 기반으로 reg_factor 생성"""
    
    # 카테고리별 제외할 이슈 목록 (관련 없는 이슈 필터링)
    CATEGORY_EXCLUDED_ISSUES = {
        'electronics_coffee_machine': [],  # 커피머신은 모든 이슈 관련 가능
        'robot_cleaner': ['거품', '조립'],  # 로봇청소기에 거품, 조립은 관련 없음
        'electronics_earphone': ['물조절', '거품', '조립', '청소/관리'],  # 이어폰에 물조절, 거품, 조립은 관련 없음
        'appliance_induction': ['물조절', '거품', '배터리'],  # 인덕션에 물조절, 거품, 배터리는 관련 없음
        'appliance_bedding_cleaner': ['물조절', '거품', '조립'],  # 침구청소기에 물조절, 거품, 조립은 관련 없음
        'appliance_heated_humidifier': ['거품', '조립', '배터리'],  # 가습기에 거품, 조립, 배터리는 관련 없음
        'furniture_bookshelf': ['물조절', '거품', '배터리', '소음'],  # 책장에 물조절, 거품, 배터리, 소음은 관련 없음
        'furniture_chair': ['물조절', '거품', '배터리', '청소/관리'],  # 의자에 물조절, 거품, 배터리는 관련 없음
        'furniture_desk': ['물조절', '거품', '배터리', '소음'],  # 책상에 물조절, 거품, 배터리, 소음은 관련 없음
        'furniture_mattress': ['물조절', '거품', '배터리', '조립', '청소/관리'],  # 매트리스에 물조절, 거품, 배터리, 조립은 관련 없음
        'appliance_rice_cooker': ['거품', '배터리', '조립'],  # 밥솥에 거품, 배터리, 조립은 관련 없음
    }
    
    # 카테고리명 자동 추출 (URL 기반)
    if not category_name:
        brand = product_url.split('/')[-3] if 'brand.naver.com' in product_url else 'product'
        product_id = product_url.split('/')[-1]
        category_name = f"{brand}_{product_id}"
    
    # 이슈 추출
    issue_counts, low_rating = extract_keywords_from_reviews(df)
    
    # 카테고리별 제외 이슈 필터링
    excluded_issues = CATEGORY_EXCLUDED_ISSUES.get(category_name, [])
    filtered_issue_counts = {
        issue: count for issue, count in issue_counts.items() 
        if issue not in excluded_issues
    }
    
    print(f"\n{'='*60}")
    print("🔍 감지된 주요 이슈")
    print(f"{'='*60}\n")
    
    for issue, count in sorted(filtered_issue_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{issue}: {count}회 언급")
    
    if excluded_issues:
        print(f"\n⚠️  제외된 이슈 ({category_name} 카테고리와 무관): {', '.join(excluded_issues)}")
    
    factors = []
    
    # 카테고리별 factor 정의
    category_factor_definitions = {
        'appliance_heated_humidifier': {
            '소음': {
                'factor_key': 'noise_sleep',
                'display_name': '수면 중 소음/눈부심',
                'description': '밤이나 수면 중 사용 시 소음·빛으로 불편함을 느끼는 후회 요인',
                'anchor_terms': '소음|시끄럽|웅웅|눈부시|빛|LED',
                'context_terms': '수면|밤|잠|취침|새벽',
                'negation_terms': '없|안|조용|괜찮',
                'weight': 1.2
            },
            '청소/관리': {
                'factor_key': 'maintenance',
                'display_name': '관리·청소 번거로움',
                'description': '물 보충·세척·석회 관리가 귀찮게 느껴지는 요인',
                'anchor_terms': '청소|관리|석회|물때|귀찮',
                'context_terms': '매일|자주|사용',
                'negation_terms': '쉽|간편|편하',
                'weight': 1.1
            },
            '성능': {
                'factor_key': 'expectation_gap',
                'display_name': '기대 대비 성능',
                'description': '가격이나 기대에 비해 성능이 아쉽다고 느끼는 요인',
                'anchor_terms': '기대|생각보다|별로|아쉽',
                'context_terms': '가격|대비',
                'negation_terms': '만족|좋|괜찮',
                'weight': 1.3
            }
        },
        'appliance_rice_cooker': {
            '청소/관리': {
                'factor_key': 'cleaning_difficulty',
                'display_name': '내솥/청소 불편',
                'description': '내솥이나 밥솥 청소가 불편하거나 번거로운 요인',
                'anchor_terms': '청소|세척|내솥|닦|씻|분리|귀찮',
                'context_terms': '내솥|솥|뚜껑|청소|세척',
                'negation_terms': '쉽|간편|편하|쉬움',
                'weight': 1.1
            },
            '크기/무게': {
                'factor_key': 'size_storage',
                'display_name': '크기/보관 공간',
                'description': '밥솥이 크거나 무거워서 보관이 불편한 요인',
                'anchor_terms': '크|무겁|크기|공간|부피|자리',
                'context_terms': '주방|보관|수납|무게',
                'negation_terms': '작|가벼|적당|괜찮',
                'weight': 0.9
            },
            '성능': {
                'factor_key': 'cooking_quality',
                'display_name': '밥맛/취사 성능',
                'description': '밥맛이나 취사 성능이 기대에 못 미치는 요인',
                'anchor_terms': '밥맛|맛|취사|눌음|설익|질척|퍼석',
                'context_terms': '밥|쌀|취사|요리',
                'negation_terms': '맛있|좋|훌륭|완벽',
                'weight': 1.4
            },
            '소음': {
                'factor_key': 'operation_noise',
                'display_name': '작동 소음/증기음',
                'description': '취사 중 소음이나 증기 배출음이 시끄러운 요인',
                'anchor_terms': '소음|시끄럽|소리|쉭|증기|김',
                'context_terms': '취사|작동|밥|하는|중',
                'negation_terms': '조용|없|작|괜찮',
                'weight': 1.0
            },
            '고장/내구성': {
                'factor_key': 'durability_coating',
                'display_name': '코팅/내구성 문제',
                'description': '내솥 코팅이 벗겨지거나 고장이 우려되는 요인',
                'anchor_terms': '코팅|벗겨|긁힘|고장|문제|오류',
                'context_terms': '내솥|솥|코팅|사용',
                'negation_terms': '튼튼|괜찮|문제없',
                'weight': 1.3
            },
            '가격/비용': {
                'factor_key': 'price_value',
                'display_name': '가격 대비 만족도',
                'description': '가격에 비해 성능이나 기능이 아쉬운 요인',
                'anchor_terms': '비싸|가격|부담|비용|비싼|가성비',
                'context_terms': '구매|가격|만원|원',
                'negation_terms': '저렴|싸|괜찮|합리',
                'weight': 1.2
            }
        },
        'robot_cleaner': {
            '청소/관리': {
                'factor_key': 'maintenance_hassle',
                'display_name': '청소/관리 번거로움',
                'description': '청소나 관리가 번거롭게 느껴지는 요인',
                'anchor_terms': '청소|관리|귀찮|번거로|세척',
                'context_terms': '매일|자주|사용|물때',
                'negation_terms': '쉽|간편|편하|쉬움',
                'weight': 1.0
            },
            '소음': {
                'factor_key': 'noise_operation',
                'display_name': '작동 소음',
                'description': '작동 시 소음이 크게 느껴지는 요인',
                'anchor_terms': '소음|시끄럽|웅웅|소리|돌아가',
                'context_terms': '작동|사용|켜면|청소',
                'negation_terms': '조용|없|괜찮|작',
                'weight': 1.1
            },
            '배터리': {
                'factor_key': 'battery_life',
                'display_name': '배터리 지속시간',
                'description': '배터리 사용시간이 짧게 느껴지는 요인',
                'anchor_terms': '배터리|충전|사용시간|방전',
                'context_terms': '청소|작동|한번|시간',
                'negation_terms': '오래|충분|길|괜찮',
                'weight': 1.1
            },
            '성능': {
                'factor_key': 'performance_gap',
                'display_name': '기대 대비 성능',
                'description': '청소 성능이 기대보다 아쉬운 요인',
                'anchor_terms': '약하|느리|별로|아쉽|기대|생각보다',
                'context_terms': '성능|효과|청소|흡입',
                'negation_terms': '좋|만족|훌륭|충분',
                'weight': 1.2
            },
            '고장/내구성': {
                'factor_key': 'durability_issue',
                'display_name': '고장/내구성 우려',
                'description': '고장이 잦거나 내구성이 걱정되는 요인',
                'anchor_terms': '고장|문제|오류|AS|수리|망가|안됨',
                'context_terms': '사용|개월|년|이후',
                'negation_terms': '튼튼|괜찮|문제없|잘됨',
                'weight': 1.4
            },
            '가격/비용': {
                'factor_key': 'price_burden',
                'display_name': '가격 부담',
                'description': '가격이나 유지비용이 부담되는 요인',
                'anchor_terms': '비싸|비용|가격|부담|비싼',
                'context_terms': '구매|유지|한달',
                'negation_terms': '저렴|싸|괜찮|합리',
                'weight': 1.3
            }
        },
        'electronics_coffee_machine': {
            '가격/비용': {
                'factor_key': 'price_burden',
                'display_name': '캡슐 비용 부담',
                'description': '캡슐 가격이 비싸서 장기적으로 부담되는 요인',
                'anchor_terms': '캡슐|비용|비싸|가격|비싼|부담',
                'context_terms': '커피|매일|자주|한달',
                'negation_terms': '저렴|싸|괜찮',
                'weight': 1.4
            },
            '물조절': {
                'factor_key': 'water_control',
                'display_name': '물 조절 불가',
                'description': '물 추가량을 조절할 수 없어 아쉬운 요인',
                'anchor_terms': '물|추가|조절|양|못|마음대로',
                'context_terms': '커피|추출|내릴때',
                'negation_terms': '가능|조절|자유',
                'weight': 1.0
            },
            '거품': {
                'factor_key': 'foam_issue',
                'display_name': '거품 문제',
                'description': '크레마 거품이 너무 많거나 적어서 아쉬운 요인',
                'anchor_terms': '거품|크레마|두껍|많|적',
                'context_terms': '커피|라떼|추출',
                'negation_terms': '적당|좋|괜찮',
                'weight': 0.8
            },
            '소음': {
                'factor_key': 'noise_operation',
                'display_name': '작동 소음',
                'description': '커피 추출 시 소음이 크게 느껴지는 요인',
                'anchor_terms': '소음|시끄럽|웅웅|돌아가|회전',
                'context_terms': '추출|작동|내릴때',
                'negation_terms': '조용|괜찮|작',
                'weight': 1.1
            },
            '고장/내구성': {
                'factor_key': 'durability_issue',
                'display_name': '기계 내구성',
                'description': '고장이 잦거나 내구성에 대한 우려',
                'anchor_terms': '고장|문제|오류|AS|수리|내구성',
                'context_terms': '사용|개월|년|이후',
                'negation_terms': '튼튼|문제없|괜찮',
                'weight': 1.3
            },
            '청소/관리': {
                'factor_key': 'maintenance_hassle',
                'display_name': '청소 번거로움',
                'description': '캡슐 제거 및 청소가 귀찮게 느껴지는 요인',
                'anchor_terms': '청소|세척|귀찮|관리|번거로',
                'context_terms': '캡슐|머신|매일',
                'negation_terms': '쉽|간편|편하',
                'weight': 1.0
            }
        },
        'electronics_earphone': {
            '소음': {
                'factor_key': 'fit_comfort',
                'display_name': '착용감/귀 불편',
                'description': '착용감이 불편하거나 귀가 아픈 요인',
                'anchor_terms': '착용|귀|아프|불편|끼|맞',
                'context_terms': '착용|귀|귓|사용|시간',
                'negation_terms': '편|괜찮|좋|안아',
                'weight': 1.3
            },
            '소음': {
                'factor_key': 'anc_performance',
                'display_name': '노이즈캔슬링 성능',
                'description': 'ANC/소음차단 성능이 기대에 못 미치는 요인',
                'anchor_terms': '노캔|노이즈|차단|ANC|소음',
                'context_terms': '외부|소리|주변|음',
                'negation_terms': '좋|훌륭|잘|만족',
                'weight': 1.2
            },
            '성능': {
                'factor_key': 'sound_quality',
                'display_name': '음질 불만족',
                'description': '음질이나 소리가 기대보다 아쉬운 요인',
                'anchor_terms': '음질|소리|음|저음|고음|사운드',
                'context_terms': '듣|노래|음악|통화',
                'negation_terms': '좋|훌륭|만족|깨끗',
                'weight': 1.1
            },
            '고장/내구성': {
                'factor_key': 'connection_issue',
                'display_name': '연결 불안정',
                'description': '블루투스 연결이 끊기거나 불안정한 요인',
                'anchor_terms': '연결|끊|블루투스|페어링|튕',
                'context_terms': '연결|기기|폰|아이폰',
                'negation_terms': '안정|잘됨|문제없|괜찮',
                'weight': 1.4
            },
            '배터리': {
                'factor_key': 'battery_life',
                'display_name': '배터리 지속시간',
                'description': '배터리 사용시간이 짧게 느껴지는 요인',
                'anchor_terms': '배터리|충전|시간|방전|오래',
                'context_terms': '사용|하루|시간|케이스',
                'negation_terms': '길|오래|충분|만족',
                'weight': 1.0
            },
            '가격/비용': {
                'factor_key': 'price_value',
                'display_name': '가격 대비 가치',
                'description': '가격이 비싸거나 가성비가 아쉬운 요인',
                'anchor_terms': '비싸|가격|비용|부담|비싼|가성비',
                'context_terms': '구매|만원|원|돈',
                'negation_terms': '저렴|싸|괜찮|합리',
                'weight': 1.3
            },
            '크기/무게': {
                'factor_key': 'case_portability',
                'display_name': '케이스 크기/휴대성',
                'description': '케이스가 크거나 무거워서 휴대가 불편한 요인',
                'anchor_terms': '케이스|크|무겁|부피|크기',
                'context_terms': '휴대|가지고|들고|주머니',
                'negation_terms': '작|가벼|적당|괜찮',
                'weight': 0.8
            }
        }
    }
    
    # 해당 카테고리의 factor 정의 가져오기
    factor_definitions = category_factor_definitions.get(category_name, {})
    
    if not factor_definitions:
        print(f"\n⚠️  카테고리 '{category_name}'에 대한 factor 정의가 없습니다.")
        print("⚠️  기본 키워드 기반 factor는 의미가 없어 생성하지 않습니다.")
        print("💡 카테고리별 factor 정의를 추가하세요.")
        # 빈 리스트 반환 - 기본 factor 생성하지 않음
        return []
    
    print(f"\n{'='*60}")
    print("📝 생성된 Factor")
    print(f"{'='*60}\n")
    
    for issue, count in sorted(filtered_issue_counts.items(), key=lambda x: x[1], reverse=True):
        if issue in factor_definitions and count >= 3:  # 최소 3회 이상 언급
            factor = factor_definitions[issue].copy()
            factor['category'] = category_name
            factors.append(factor)
            print(f"✓ {factor['factor_key']}: {factor['display_name']} (언급 {count}회)")
    
    return factors


def generate_questions(factors):
    """Factor 기반으로 reg_question 생성"""
    
    question_templates = {
        'noise_operation': {
            'question_text': '조용한 환경에서 사용하거나 소음에 민감하신가요?',
            'choices': '민감함|보통|상관없음'
        },
        'price_burden': {
            'question_text': '가격이 구매 결정에 중요한 요소인가요?',
            'choices': '매우 중요|보통|상관없음'
        },
        'performance_gap': {
            'question_text': '제품 성능에 대한 기대치가 높은 편인가요?',
            'choices': '높음|보통|낮음'
        },
        'durability_issue': {
            'question_text': '장기간(3년 이상) 사용을 계획하고 계신가요?',
            'choices': '예|아니오'
        },
        'maintenance_hassle': {
            'question_text': '매일 청소나 관리가 필요해도 괜찮으신가요?',
            'choices': '번거로움 싫음|감수 가능'
        },
        'size_weight': {
            'question_text': '제품의 크기나 무게가 중요한가요?',
            'choices': '중요함|보통|상관없음'
        },
        'battery_life': {
            'question_text': '한 번 충전으로 오래 사용하고 싶으신가요?',
            'choices': '매우 중요|보통|상관없음'
        },
        'water_control': {
            'question_text': '커피 농도나 물 양을 세밀하게 조절하고 싶으신가요?',
            'choices': '꼭 필요함|있으면 좋음|상관없음'
        },
        'foam_issue': {
            'question_text': '커피 거품(크레마)의 양이 중요한가요?',
            'choices': '중요함|보통|상관없음'
        }
    }
    
    print(f"\n{'='*60}")
    print("❓ 생성된 Question")
    print(f"{'='*60}\n")
    
    questions = []
    for idx, factor in enumerate(factors, 1):
        factor_key = factor['factor_key']
        display_name = factor.get('display_name', factor_key)
        
        # 기존 템플릿이 있으면 사용, 없으면 자동 생성
        if factor_key in question_templates:
            template = question_templates[factor_key]
            question_text = template['question_text']
            choices = template['choices']
        else:
            # 새로운 factor에 대해 자동으로 질문 생성
            question_text = f'{display_name}이(가) 구매 결정에 중요한 요소인가요?'
            choices = '매우 중요|보통|상관없음'
        
        question = {
            'question_id': f'Q{idx}',
            'factor_key': factor_key,
            'question_text': question_text,
            'answer_type': 'single_choice',
            'choices': choices,
            'priority': idx,
            'next_factor_hint': factor_key
        }
        questions.append(question)
        print(f"Q{idx}. [{factor_key}] {question_text}")
    
    return questions


def save_to_csv(factors, questions, category_name):
    """생성된 factor와 question을 기존 CSV 파일에 병합"""
    
    factor_file = 'backend/data/factor/reg_factor.csv'
    question_file = 'backend/data/question/reg_question.csv'
    
    # 1. Factor 병합
    try:
        existing_factors = pd.read_csv(factor_file)
    except FileNotFoundError:
        existing_factors = pd.DataFrame()
    
    new_factor_df = pd.DataFrame(factors)
    
    if not existing_factors.empty:
        # 기존 factor 중 같은 category의 것 제거 (업데이트)
        existing_factors = existing_factors[existing_factors['category'] != category_name]
        # 새 factor 추가
        combined_factors = pd.concat([existing_factors, new_factor_df], ignore_index=True)
    else:
        combined_factors = new_factor_df
    
    combined_factors.to_csv(factor_file, index=False, encoding='utf-8-sig')
    print(f"\n✅ Factor 저장: {factor_file}")
    print(f"   - 기존: {len(existing_factors)}개")
    print(f"   - 새로운: {len(new_factor_df)}개")
    print(f"   - 전체: {len(combined_factors)}개")
    
    # 2. Question 병합
    try:
        existing_questions = pd.read_csv(question_file)
        max_q_num = 0
        if not existing_questions.empty:
            # 기존 question_id에서 최대 번호 찾기
            q_nums = existing_questions['question_id'].str.extract(r'Q(\d+)')[0].astype(int)
            max_q_num = q_nums.max()
    except FileNotFoundError:
        existing_questions = pd.DataFrame()
        max_q_num = 0
    
    # factor_key 목록 가져오기
    existing_factor_keys = set()
    if not existing_questions.empty:
        existing_factor_keys = set(existing_questions['factor_key'].unique())
    
    # 새 question의 ID 재할당
    new_questions_updated = []
    for i, q in enumerate(questions, 1):
        # 같은 factor_key가 이미 있으면 업데이트, 없으면 새 ID 할당
        if q['factor_key'] in existing_factor_keys:
            # 기존 question 유지 (업데이트 안함)
            continue
        else:
            # 새 ID 할당
            q['question_id'] = f"Q{max_q_num + i}"
            q['priority'] = max_q_num + i
            new_questions_updated.append(q)
    
    new_question_df = pd.DataFrame(new_questions_updated)
    
    if not existing_questions.empty and not new_question_df.empty:
        combined_questions = pd.concat([existing_questions, new_question_df], ignore_index=True)
    elif not new_question_df.empty:
        combined_questions = new_question_df
    else:
        combined_questions = existing_questions
    
    combined_questions.to_csv(question_file, index=False, encoding='utf-8-sig')
    print(f"\n✅ Question 저장: {question_file}")
    print(f"   - 기존: {len(existing_questions)}개")
    print(f"   - 새로운: {len(new_questions_updated)}개")
    print(f"   - 전체: {len(combined_questions)}개")
    
    return factor_file, question_file


def auto_detect_category_and_product(url):
    """URL에서 브랜드를 추출하고 자동으로 카테고리와 상품명 매핑"""
    
    # 브랜드 → 카테고리 & 상품명 매핑 테이블
    brand_mapping = {
        'nespressokorea': ('electronics_coffee_machine', 'nespresso'),
        'everybot': ('robot_cleaner', 'everybot'),
        'applestore': ('electronics_earphone', 'airpods_pro3'),
        'cuckoo': ('appliance_induction', 'cuckoo_induction'),
        'haan': ('appliance_bedding_cleaner', 'haan_cleaner'),
        'lumena': ('appliance_heated_humidifier', 'lumena_humidifier'),
        'hanssemmall': ('furniture_bookshelf', 'hanssem_bookshelf'),
        'sidiz': ('furniture_chair', 'sidiz_chair'),
        'desker': ('furniture_desk', 'desker_desk'),
        'zinus': ('furniture_mattress', 'zinus_mattress'),
    }
    
    # URL에서 브랜드 추출
    url_parts = url.split('/')
    brand_name = url_parts[-3] if 'brand.naver.com' in url else 'smartstore'
    
    # 매핑 테이블에서 찾기
    if brand_name in brand_mapping:
        category, product_name = brand_mapping[brand_name]
    else:
        # 기본값 (브랜드명 그대로 사용)
        category = f'general_{brand_name}'
        product_name = brand_name
    
    return brand_name, category, product_name


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='제품 리뷰를 분석하여 reg_factor와 reg_question 생성',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python scripts/analyze_product_reviews.py https://brand.naver.com/everybot/products/11163824445
  python scripts/analyze_product_reviews.py https://brand.naver.com/nespressokorea/products/5762090671 --category electronics_coffee_machine --product-name nespresso
        """
    )
    
    parser.add_argument('url', help='제품 URL')
    parser.add_argument('--max-reviews', type=int, default=200, help='수집할 최대 리뷰 수 (기본: 200)')
    parser.add_argument('--category', help='카테고리명 (미지정시 자동 추출)')
    parser.add_argument('--product-name', help='상품명 (미지정시 자동 추출)')
    
    args = parser.parse_args()
    
    try:
        # URL에서 brand, category, product_name 자동 추출
        brand_name, auto_category, auto_product = auto_detect_category_and_product(args.url)
        
        # 인자로 지정된 값이 있으면 우선 사용, 없으면 자동 추출값 사용
        category = args.category or auto_category
        product_name = args.product_name or auto_product
        
        # 파일명 생성 (reviews_brand_카테고리명_상품명_날짜_일시.json)
        now = datetime.now()
        date_str = now.strftime('%Y%m%d')
        time_str = now.strftime('%H%M%S')
        review_filename = f'reviews_{brand_name}_{category}_{product_name}_{date_str}_{time_str}.json'
        review_filepath = f'backend/data/review/{review_filename}'
        
        print(f"\n{'='*60}")
        print(f"🚀 리뷰 분석 시작")
        print(f"{'='*60}")
        print(f"URL: {args.url}")
        print(f"브랜드: {brand_name}")
        print(f"카테고리: {category}")
        print(f"상품명: {product_name}")
        print(f"최대 리뷰 수: {args.max_reviews}")
        print(f"저장 파일: {review_filename}")
        
        # 1. 리뷰 수집 (별점 낮은 순)
        print(f"\n{'='*60}")
        print("📥 리뷰 수집 중... (별점 낮은 순)")
        print(f"{'='*60}\n")
        
        collector = SmartStoreCollector(args.url, headless=True)
        reviews = collector.collect_reviews(
            max_reviews=args.max_reviews, 
            sort_by_low_rating=True  # 별점 낮은 순으로 정렬
        )
        converted = collector.convert_to_backend_format(reviews)
        
        # 리뷰 JSON 파일로 저장
        with open(review_filepath, 'w', encoding='utf-8') as f:
            json.dump(converted, f, ensure_ascii=False, indent=2)
        print(f"✅ 리뷰 저장: {review_filepath}")
        
        df = pd.DataFrame(converted)
        df_sorted = df.sort_values('rating')
        
        # 통계
        print(f"\n📊 리뷰 통계")
        print(f"{'='*60}")
        print(f"전체 리뷰: {len(df)}건")
        print(f"\n별점 분포:")
        print(df['rating'].value_counts().sort_index().to_string())
        
        low_rating = df_sorted[df_sorted['rating'] <= 3]
        print(f"\n별점 3점 이하: {len(low_rating)}건")
        
        # 2. Factor 생성
        factors = generate_factors(args.url, df, category)
        
        if not factors:
            print("\n⚠️  충분한 이슈를 찾지 못했습니다. 더 많은 리뷰를 수집하거나 수동으로 작성해주세요.")
            return
        
        # 3. Question 생성
        questions = generate_questions(factors)
        
        # 4. 기존 CSV에 병합
        save_to_csv(factors, questions, category)
        
        print(f"\n{'='*60}")
        print("✅ 완료!")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
