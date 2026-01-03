"""
기존에 수집된 리뷰 파일들을 재분석하여 factor와 question 생성

사용법:
    python scripts/reanalyze_existing_reviews.py
"""
import sys
import json
import pandas as pd
from pathlib import Path
from collections import Counter
import re

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))


# 카테고리 한글명 매핑
CATEGORY_NAMES = {
    'electronics_coffee_machine': '커피머신',
    'robot_cleaner': '로봇청소기',
    'electronics_earphone': '이어폰',
    'appliance_induction': '인덕션',
    'appliance_bedding_cleaner': '침구청소기',
    'appliance_heated_humidifier': '가습기',
    'furniture_bookshelf': '책장',
    'furniture_chair': '의자',
    'furniture_desk': '책상',
    'furniture_mattress': '매트리스',
    'appliance_rice_cooker': '밥솥',
}


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
        '배송': ['배송', '택배', '포장', '박스', '파손'],
        '조립': ['조립', '설치', '어렵', '복잡'],
        '냄새': ['냄새', '악취', '향', '페인트'],
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


def get_all_category_definitions():
    """모든 카테고리에 대한 factor 정의"""
    return {
        'electronics_coffee_machine': {
            '가격/비용': {
                'factor_key': 'capsule_cost',
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
                'factor_key': 'foam_quality',
                'display_name': '거품 품질',
                'description': '크레마 거품이 너무 많거나 적어서 아쉬운 요인',
                'anchor_terms': '거품|크레마|두껍|많|적',
                'context_terms': '커피|라떼|추출',
                'negation_terms': '적당|좋|괜찮',
                'weight': 0.8
            },
            '소음': {
                'factor_key': 'machine_noise',
                'display_name': '작동 소음',
                'description': '커피 추출 시 소음이 크게 느껴지는 요인',
                'anchor_terms': '소음|시끄럽|웅웅|돌아가|회전',
                'context_terms': '추출|작동|내릴때',
                'negation_terms': '조용|괜찮|작',
                'weight': 1.1
            },
            '고장/내구성': {
                'factor_key': 'machine_durability',
                'display_name': '기계 내구성',
                'description': '고장이 잦거나 내구성에 대한 우려',
                'anchor_terms': '고장|문제|오류|AS|수리|내구성',
                'context_terms': '사용|개월|년|이후',
                'negation_terms': '튼튼|문제없|괜찮',
                'weight': 1.3
            },
            '청소/관리': {
                'factor_key': 'cleaning_hassle',
                'display_name': '청소 번거로움',
                'description': '캡슐 제거 및 청소가 귀찮게 느껴지는 요인',
                'anchor_terms': '청소|세척|귀찮|관리|번거로',
                'context_terms': '캡슐|머신|매일',
                'negation_terms': '쉽|간편|편하',
                'weight': 1.0
            }
        },
        'robot_cleaner': {
            '소음': {
                'factor_key': 'operation_noise',
                'display_name': '작동 소음',
                'description': '작동 시 소음이 크게 느껴지는 요인',
                'anchor_terms': '소음|시끄럽|웅웅|소리|돌아가',
                'context_terms': '작동|사용|켜면|청소',
                'negation_terms': '조용|없|괜찮|작',
                'weight': 1.1
            },
            '청소/관리': {
                'factor_key': 'maintenance_burden',
                'display_name': '청소/관리 부담',
                'description': '청소나 관리가 번거롭게 느껴지는 요인',
                'anchor_terms': '청소|관리|귀찮|번거로|세척',
                'context_terms': '매일|자주|사용|물때',
                'negation_terms': '쉽|간편|편하|쉬움',
                'weight': 1.0
            },
            '배터리': {
                'factor_key': 'battery_runtime',
                'display_name': '배터리 지속시간',
                'description': '배터리 사용시간이 짧게 느껴지는 요인',
                'anchor_terms': '배터리|충전|사용시간|방전',
                'context_terms': '청소|작동|한번|시간',
                'negation_terms': '오래|충분|길|괜찮',
                'weight': 1.1
            },
            '성능': {
                'factor_key': 'cleaning_performance',
                'display_name': '청소 성능',
                'description': '청소 성능이 기대보다 아쉬운 요인',
                'anchor_terms': '약하|느리|별로|아쉽|기대|생각보다',
                'context_terms': '성능|효과|청소|흡입',
                'negation_terms': '좋|만족|훌륭|충분',
                'weight': 1.2
            },
            '고장/내구성': {
                'factor_key': 'product_durability',
                'display_name': '제품 내구성',
                'description': '고장이 잦거나 내구성이 걱정되는 요인',
                'anchor_terms': '고장|문제|오류|AS|수리|망가|안됨',
                'context_terms': '사용|개월|년|이후',
                'negation_terms': '튼튼|괜찮|문제없|잘됨',
                'weight': 1.4
            },
            '가격/비용': {
                'factor_key': 'price_value',
                'display_name': '가격 대비 가치',
                'description': '가격이나 유지비용이 부담되는 요인',
                'anchor_terms': '비싸|비용|가격|부담|비싼',
                'context_terms': '구매|유지|한달',
                'negation_terms': '저렴|싸|괜찮|합리',
                'weight': 1.3
            }
        },
        'electronics_earphone': {
            '소음': {
                'factor_key': 'anc_quality',
                'display_name': '노이즈캔슬링 성능',
                'description': 'ANC/소음차단 성능이 기대에 못 미치는 요인',
                'anchor_terms': '노캔|노이즈|차단|ANC|소음',
                'context_terms': '외부|소리|주변|음',
                'negation_terms': '좋|훌륭|잘|만족',
                'weight': 1.2
            },
            '고장/내구성': {
                'factor_key': 'connection_stability',
                'display_name': '연결 안정성',
                'description': '블루투스 연결이 끊기거나 불안정한 요인',
                'anchor_terms': '연결|끊|블루투스|페어링|튕',
                'context_terms': '연결|기기|폰|아이폰',
                'negation_terms': '안정|잘됨|문제없|괜찮',
                'weight': 1.4
            },
            '가격/비용': {
                'factor_key': 'price_satisfaction',
                'display_name': '가격 만족도',
                'description': '가격이 비싸거나 가성비가 아쉬운 요인',
                'anchor_terms': '비싸|가격|비용|부담|비싼|가성비',
                'context_terms': '구매|만원|원|돈',
                'negation_terms': '저렴|싸|괜찮|합리',
                'weight': 1.3
            },
            '배터리': {
                'factor_key': 'battery_endurance',
                'display_name': '배터리 지속력',
                'description': '배터리 사용시간이 짧게 느껴지는 요인',
                'anchor_terms': '배터리|충전|시간|방전|오래',
                'context_terms': '사용|하루|시간|케이스',
                'negation_terms': '길|오래|충분|만족',
                'weight': 1.0
            },
            '성능': {
                'factor_key': 'audio_quality',
                'display_name': '음질',
                'description': '음질이나 소리가 기대보다 아쉬운 요인',
                'anchor_terms': '음질|소리|음|저음|고음|사운드',
                'context_terms': '듣|노래|음악|통화',
                'negation_terms': '좋|훌륭|만족|깨끗',
                'weight': 1.1
            },
            '크기/무게': {
                'factor_key': 'portability',
                'display_name': '휴대성',
                'description': '케이스가 크거나 무거워서 휴대가 불편한 요인',
                'anchor_terms': '케이스|크|무겁|부피|크기',
                'context_terms': '휴대|가지고|들고|주머니',
                'negation_terms': '작|가벼|적당|괜찮',
                'weight': 0.8
            }
        },
        'appliance_induction': {
            '소음': {
                'factor_key': 'cooking_noise',
                'display_name': '조리 소음',
                'description': '조리 중 소음이 크게 느껴지는 요인',
                'anchor_terms': '소음|시끄럽|소리|웅웅',
                'context_terms': '조리|작동|사용',
                'negation_terms': '조용|괜찮|작',
                'weight': 1.0
            },
            '성능': {
                'factor_key': 'heating_power',
                'display_name': '화력',
                'description': '화력이나 조리 성능이 아쉬운 요인',
                'anchor_terms': '약하|느리|화력|별로|아쉽',
                'context_terms': '조리|요리|끓|불',
                'negation_terms': '강함|좋|빠름',
                'weight': 1.3
            },
            '청소/관리': {
                'factor_key': 'surface_cleaning',
                'display_name': '표면 청소',
                'description': '표면 청소나 관리가 불편한 요인',
                'anchor_terms': '청소|닦|얼룩|자국',
                'context_terms': '표면|유리|세척',
                'negation_terms': '쉽|간편|깨끗',
                'weight': 0.9
            },
            '크기/무게': {
                'factor_key': 'size_fit',
                'display_name': '크기/공간',
                'description': '크기가 커서 공간 차지가 부담되는 요인',
                'anchor_terms': '크|크기|공간|부피',
                'context_terms': '주방|설치|공간',
                'negation_terms': '작|적당|괜찮',
                'weight': 0.8
            },
            '고장/내구성': {
                'factor_key': 'reliability',
                'display_name': '신뢰성',
                'description': '고장이나 오작동 우려가 있는 요인',
                'anchor_terms': '고장|문제|오류|AS|작동',
                'context_terms': '사용|개월|년',
                'negation_terms': '튼튼|문제없|잘됨',
                'weight': 1.4
            },
            '가격/비용': {
                'factor_key': 'cost_effectiveness',
                'display_name': '가성비',
                'description': '가격 대비 성능이나 기능이 아쉬운 요인',
                'anchor_terms': '비싸|가격|부담|비용|가성비',
                'context_terms': '구매|대비|만원',
                'negation_terms': '저렴|싸|합리',
                'weight': 1.2
            }
        },
        'appliance_bedding_cleaner': {
            '소음': {
                'factor_key': 'vacuum_noise',
                'display_name': '흡입 소음',
                'description': '작동 시 소음이 크게 느껴지는 요인',
                'anchor_terms': '소음|시끄럽|소리|웅웅',
                'context_terms': '작동|청소|사용',
                'negation_terms': '조용|괜찮|작',
                'weight': 1.1
            },
            '성능': {
                'factor_key': 'suction_power',
                'display_name': '흡입력',
                'description': '흡입력이나 청소 성능이 아쉬운 요인',
                'anchor_terms': '약하|별로|아쉽|흡입|성능',
                'context_terms': '청소|먼지|진드기',
                'negation_terms': '강함|좋|만족',
                'weight': 1.3
            },
            '청소/관리': {
                'factor_key': 'filter_maintenance',
                'display_name': '필터 관리',
                'description': '필터 청소나 교체가 번거로운 요인',
                'anchor_terms': '청소|필터|교체|귀찮',
                'context_terms': '필터|관리|세척',
                'negation_terms': '쉽|간편|편하',
                'weight': 1.0
            },
            '크기/무게': {
                'factor_key': 'weight_handling',
                'display_name': '무게/사용감',
                'description': '무겁거나 사용이 불편한 요인',
                'anchor_terms': '무겁|크|무게|힘들',
                'context_terms': '사용|들고|청소',
                'negation_terms': '가벼|적당|편함',
                'weight': 1.1
            },
            '고장/내구성': {
                'factor_key': 'build_quality',
                'display_name': '내구성',
                'description': '고장이나 파손 우려가 있는 요인',
                'anchor_terms': '고장|문제|망가|AS',
                'context_terms': '사용|개월|년',
                'negation_terms': '튼튼|문제없|잘됨',
                'weight': 1.3
            },
            '가격/비용': {
                'factor_key': 'value_for_money',
                'display_name': '가격 대비 만족도',
                'description': '가격에 비해 성능이 아쉬운 요인',
                'anchor_terms': '비싸|가격|부담|비용',
                'context_terms': '구매|만원|원',
                'negation_terms': '저렴|싸|합리',
                'weight': 1.2
            }
        },
        'appliance_heated_humidifier': {
            '청소/관리': {
                'factor_key': 'water_maintenance',
                'display_name': '물통 관리',
                'description': '물 보충·세척·석회 관리가 귀찮게 느껴지는 요인',
                'anchor_terms': '청소|관리|석회|물때|귀찮',
                'context_terms': '매일|자주|사용',
                'negation_terms': '쉽|간편|편하',
                'weight': 1.1
            },
            '소음': {
                'factor_key': 'sleep_disturbance',
                'display_name': '수면 방해',
                'description': '밤이나 수면 중 사용 시 소음·빛으로 불편함을 느끼는 요인',
                'anchor_terms': '소음|시끄럽|웅웅|눈부시|빛|LED',
                'context_terms': '수면|밤|잠|취침|새벽',
                'negation_terms': '없|안|조용|괜찮',
                'weight': 1.2
            },
            '성능': {
                'factor_key': 'humidity_output',
                'display_name': '가습량',
                'description': '가격이나 기대에 비해 가습 성능이 아쉬운 요인',
                'anchor_terms': '기대|생각보다|별로|아쉽|적',
                'context_terms': '가습|습도|수증기',
                'negation_terms': '만족|좋|괜찮|충분',
                'weight': 1.3
            },
            '물조절': {
                'factor_key': 'water_capacity',
                'display_name': '물통 용량',
                'description': '물통이 작아서 자주 보충해야 하는 요인',
                'anchor_terms': '물|작|용량|자주|보충',
                'context_terms': '물통|리터|용량',
                'negation_terms': '크|충분|많',
                'weight': 0.9
            },
            '냄새': {
                'factor_key': 'odor_issue',
                'display_name': '냄새 문제',
                'description': '사용 중 불쾌한 냄새가 나는 요인',
                'anchor_terms': '냄새|악취|향|곰팡이',
                'context_terms': '사용|작동|물',
                'negation_terms': '없|괜찮',
                'weight': 1.0
            },
            '가격/비용': {
                'factor_key': 'price_performance',
                'display_name': '가격 대비 성능',
                'description': '가격에 비해 성능이나 기능이 아쉬운 요인',
                'anchor_terms': '비싸|가격|부담|비용',
                'context_terms': '구매|만원|원',
                'negation_terms': '저렴|싸|합리',
                'weight': 1.2
            }
        },
        'furniture_bookshelf': {
            '조립': {
                'factor_key': 'assembly_difficulty',
                'display_name': '조립 난이도',
                'description': '조립이 어렵거나 복잡한 요인',
                'anchor_terms': '조립|어렵|복잡|설명서|힘들',
                'context_terms': '조립|설치|만들',
                'negation_terms': '쉽|간단|편함',
                'weight': 1.3
            },
            '크기/무게': {
                'factor_key': 'space_fit',
                'display_name': '공간 활용',
                'description': '크기가 예상과 다르거나 공간 활용이 아쉬운 요인',
                'anchor_terms': '크|작|크기|공간|높이',
                'context_terms': '설치|공간|방',
                'negation_terms': '적당|괜찮|딱',
                'weight': 1.1
            },
            '고장/내구성': {
                'factor_key': 'structural_stability',
                'display_name': '구조 안정성',
                'description': '흔들림이나 내구성이 걱정되는 요인',
                'anchor_terms': '흔들|불안|튼튼|약|삐걱',
                'context_terms': '사용|책|무게',
                'negation_terms': '튼튼|안정|괜찮',
                'weight': 1.4
            },
            '성능': {
                'factor_key': 'storage_capacity',
                'display_name': '수납 용량',
                'description': '수납 공간이나 칸 구성이 아쉬운 요인',
                'anchor_terms': '작|좁|적|칸|공간',
                'context_terms': '수납|책|물건',
                'negation_terms': '넓|크|충분',
                'weight': 1.0
            },
            '배송': {
                'factor_key': 'delivery_damage',
                'display_name': '배송 상태',
                'description': '배송 중 파손이나 포장 불량 요인',
                'anchor_terms': '배송|택배|포장|파손|깨짐',
                'context_terms': '도착|받|포장',
                'negation_terms': '완벽|괜찮|안전',
                'weight': 1.1
            },
            '가격/비용': {
                'factor_key': 'quality_price_ratio',
                'display_name': '품질 대비 가격',
                'description': '가격 대비 품질이나 디자인이 아쉬운 요인',
                'anchor_terms': '비싸|가격|부담|저렴',
                'context_terms': '구매|만원|원',
                'negation_terms': '저렴|싸|합리',
                'weight': 1.0
            }
        },
        'furniture_chair': {
            '성능': {
                'factor_key': 'sitting_comfort',
                'display_name': '착좌감',
                'description': '앉았을 때 편안함이나 쿠션감이 아쉬운 요인',
                'anchor_terms': '불편|아프|딱딱|쿠션|푹신',
                'context_terms': '앉|사용|시간',
                'negation_terms': '편함|좋|푹신',
                'weight': 1.4
            },
            '조립': {
                'factor_key': 'chair_assembly',
                'display_name': '조립 편의성',
                'description': '조립이 어렵거나 시간이 오래 걸리는 요인',
                'anchor_terms': '조립|어렵|복잡|설명서',
                'context_terms': '조립|설치|만들',
                'negation_terms': '쉽|간단|빠름',
                'weight': 1.1
            },
            '고장/내구성': {
                'factor_key': 'chair_durability',
                'display_name': '의자 내구성',
                'description': '의자가 삐걱거리거나 파손 우려가 있는 요인',
                'anchor_terms': '삐걱|흔들|고장|망가|약',
                'context_terms': '사용|개월|년',
                'negation_terms': '튼튼|안정|괜찮',
                'weight': 1.3
            },
            '크기/무게': {
                'factor_key': 'chair_size',
                'display_name': '크기/체형',
                'description': '의자 크기가 체형에 맞지 않는 요인',
                'anchor_terms': '크|작|높이|폭|맞',
                'context_terms': '앉|체형|키',
                'negation_terms': '적당|딱|괜찮',
                'weight': 1.2
            },
            '소음': {
                'factor_key': 'chair_noise',
                'display_name': '의자 소음',
                'description': '움직일 때 삐걱거림이나 소음이 나는 요인',
                'anchor_terms': '삐걱|소리|소음|시끄',
                'context_terms': '앉|움직|회전',
                'negation_terms': '조용|없|괜찮',
                'weight': 1.0
            },
            '가격/비용': {
                'factor_key': 'chair_value',
                'display_name': '가격 만족도',
                'description': '가격 대비 품질이나 기능이 아쉬운 요인',
                'anchor_terms': '비싸|가격|부담|비용',
                'context_terms': '구매|만원|원',
                'negation_terms': '저렴|싸|합리',
                'weight': 1.2
            }
        },
        'furniture_desk': {
            '조립': {
                'factor_key': 'desk_assembly',
                'display_name': '조립 복잡도',
                'description': '조립이 어렵거나 시간이 많이 소요되는 요인',
                'anchor_terms': '조립|어렵|복잡|힘들|설명서',
                'context_terms': '조립|설치|만들',
                'negation_terms': '쉽|간단|빠름',
                'weight': 1.3
            },
            '크기/무게': {
                'factor_key': 'desk_dimensions',
                'display_name': '크기/공간',
                'description': '크기가 예상과 다르거나 공간 활용이 아쉬운 요인',
                'anchor_terms': '크|작|크기|넓이|높이',
                'context_terms': '공간|방|설치',
                'negation_terms': '적당|딱|괜찮',
                'weight': 1.2
            },
            '고장/내구성': {
                'factor_key': 'desk_stability',
                'display_name': '책상 안정성',
                'description': '흔들림이나 내구성이 걱정되는 요인',
                'anchor_terms': '흔들|불안|약|삐걱|튼튼',
                'context_terms': '사용|무게|책',
                'negation_terms': '튼튼|안정|괜찮',
                'weight': 1.4
            },
            '성능': {
                'factor_key': 'desk_functionality',
                'display_name': '기능성',
                'description': '수납이나 높이 조절 등 기능이 아쉬운 요인',
                'anchor_terms': '수납|칸|조절|높이|기능',
                'context_terms': '사용|작업|공부',
                'negation_terms': '편함|좋|충분',
                'weight': 1.1
            },
            '배송': {
                'factor_key': 'desk_delivery',
                'display_name': '배송/포장',
                'description': '배송 중 파손이나 포장 불량 요인',
                'anchor_terms': '배송|택배|포장|파손|깨짐',
                'context_terms': '도착|받|배송',
                'negation_terms': '완벽|괜찮|안전',
                'weight': 1.0
            },
            '가격/비용': {
                'factor_key': 'desk_price',
                'display_name': '가격 대비 품질',
                'description': '가격 대비 품질이나 디자인이 아쉬운 요인',
                'anchor_terms': '비싸|가격|부담|비용',
                'context_terms': '구매|만원|원',
                'negation_terms': '저렴|싸|합리',
                'weight': 1.2
            }
        },
        'furniture_mattress': {
            '성능': {
                'factor_key': 'mattress_firmness',
                'display_name': '쿠션감/단단함',
                'description': '매트리스가 너무 딱딱하거나 푹신한 요인',
                'anchor_terms': '딱딱|푹신|쿠션|단단|부드럽',
                'context_terms': '누움|잠|수면',
                'negation_terms': '적당|좋|괜찮',
                'weight': 1.4
            },
            '냄새': {
                'factor_key': 'mattress_odor',
                'display_name': '신제품 냄새',
                'description': '개봉 후 화학 냄새가 오래 지속되는 요인',
                'anchor_terms': '냄새|악취|향|화학|페인트',
                'context_terms': '개봉|처음|신품',
                'negation_terms': '없|괜찮|사라짐',
                'weight': 1.2
            },
            '크기/무게': {
                'factor_key': 'mattress_thickness',
                'display_name': '두께/높이',
                'description': '두께가 예상보다 얇거나 두꺼운 요인',
                'anchor_terms': '얇|두껍|두께|높이',
                'context_terms': '매트|높이|침대',
                'negation_terms': '적당|괜찮|딱',
                'weight': 1.0
            },
            '고장/내구성': {
                'factor_key': 'mattress_sagging',
                'display_name': '처짐/내구성',
                'description': '사용 후 처지거나 내구성이 걱정되는 요인',
                'anchor_terms': '처짐|꺼짐|내구|푹|변형',
                'context_terms': '사용|개월|년',
                'negation_terms': '튼튼|괜찮|유지',
                'weight': 1.3
            },
            '배송': {
                'factor_key': 'mattress_packaging',
                'display_name': '압축/배송',
                'description': '압축 배송 후 복원이 느리거나 문제가 있는 요인',
                'anchor_terms': '압축|복원|펴짐|배송',
                'context_terms': '개봉|도착|배송',
                'negation_terms': '빠름|잘|완벽',
                'weight': 0.9
            },
            '가격/비용': {
                'factor_key': 'mattress_value',
                'display_name': '가성비',
                'description': '가격 대비 품질이나 수명이 아쉬운 요인',
                'anchor_terms': '비싸|가격|부담|비용',
                'context_terms': '구매|만원|원',
                'negation_terms': '저렴|싸|합리',
                'weight': 1.1
            }
        },
        'appliance_rice_cooker': {
            '청소/관리': {
                'factor_key': 'pot_cleaning',
                'display_name': '내솥 청소',
                'description': '내솥이나 밥솥 청소가 불편하거나 번거로운 요인',
                'anchor_terms': '청소|세척|내솥|닦|씻|분리',
                'context_terms': '내솥|솥|뚜껑',
                'negation_terms': '쉽|간편|편하',
                'weight': 1.1
            },
            '크기/무게': {
                'factor_key': 'cooker_size',
                'display_name': '크기/보관',
                'description': '밥솥이 크거나 무거워서 보관이 불편한 요인',
                'anchor_terms': '크|무겁|크기|공간|부피',
                'context_terms': '주방|보관|수납',
                'negation_terms': '작|가벼|적당',
                'weight': 0.9
            },
            '성능': {
                'factor_key': 'rice_taste',
                'display_name': '밥맛',
                'description': '밥맛이나 취사 성능이 기대에 못 미치는 요인',
                'anchor_terms': '밥맛|맛|취사|눌음|설익',
                'context_terms': '밥|쌀|취사',
                'negation_terms': '맛있|좋|훌륭',
                'weight': 1.4
            },
            '소음': {
                'factor_key': 'steam_noise',
                'display_name': '소음/증기',
                'description': '취사 중 소음이나 증기 배출음이 시끄러운 요인',
                'anchor_terms': '소음|시끄럽|소리|쉭|증기',
                'context_terms': '취사|작동|밥',
                'negation_terms': '조용|없|작',
                'weight': 1.0
            },
            '고장/내구성': {
                'factor_key': 'coating_durability',
                'display_name': '코팅 내구성',
                'description': '내솥 코팅이 벗겨지거나 고장 우려가 있는 요인',
                'anchor_terms': '코팅|벗겨|긁힘|고장|문제',
                'context_terms': '내솥|솥|코팅',
                'negation_terms': '튼튼|괜찮|문제없',
                'weight': 1.3
            },
            '가격/비용': {
                'factor_key': 'cooker_value',
                'display_name': '가격 대비 만족도',
                'description': '가격에 비해 성능이나 기능이 아쉬운 요인',
                'anchor_terms': '비싸|가격|부담|비용',
                'context_terms': '구매|만원|원',
                'negation_terms': '저렴|싸|합리',
                'weight': 1.2
            }
        }
    }


def generate_factor_key(issue_name, category_name):
    """이슈명에서 영문 factor_key 자동 생성"""
    
    # 한글 → 영문 매핑
    issue_mapping = {
        '소음': 'noise',
        '가격/비용': 'price',
        '성능': 'performance',
        '고장/내구성': 'durability',
        '청소/관리': 'maintenance',
        '크기/무게': 'size',
        '배터리': 'battery',
        '물조절': 'water_control',
        '거품': 'foam',
        '배송': 'delivery',
        '조립': 'assembly',
        '냄새': 'odor',
    }
    
    # 카테고리별 접두사
    category_prefixes = {
        'electronics_coffee_machine': 'coffee',
        'robot_cleaner': 'robot',
        'electronics_earphone': 'earphone',
        'appliance_induction': 'induction',
        'appliance_bedding_cleaner': 'bedding',
        'appliance_heated_humidifier': 'humidifier',
        'furniture_bookshelf': 'bookshelf',
        'furniture_chair': 'chair',
        'furniture_desk': 'desk',
        'furniture_mattress': 'mattress',
        'appliance_rice_cooker': 'cooker',
    }
    
    base_key = issue_mapping.get(issue_name, issue_name.lower().replace('/', '_'))
    prefix = category_prefixes.get(category_name, 'product')
    
    return f"{prefix}_{base_key}"


def generate_factors_from_existing_review(review_file, category_name):
    """기존 리뷰 파일에서 factor 생성"""
    
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
    }
    
    # 리뷰 JSON 읽기
    with open(review_file, 'r', encoding='utf-8') as f:
        reviews = json.load(f)
    
    df = pd.DataFrame(reviews)
    
    # 이슈 추출
    issue_counts, low_rating = extract_keywords_from_reviews(df)
    
    # 카테고리별 제외 이슈 필터링
    excluded_issues = CATEGORY_EXCLUDED_ISSUES.get(category_name, [])
    filtered_issue_counts = {
        issue: count for issue, count in issue_counts.items() 
        if issue not in excluded_issues
    }
    
    print(f"\n{'='*60}")
    print(f"📊 {CATEGORY_NAMES.get(category_name, category_name)} 분석")
    print(f"{'='*60}")
    print(f"전체 리뷰: {len(df)}건")
    print(f"별점 3점 이하: {len(low_rating)}건\n")
    
    # 카테고리별 factor 정의 가져오기 (기존 정의 우선 사용)
    all_definitions = get_all_category_definitions()
    predefined_factors = all_definitions.get(category_name, {})
    
    print("🔍 감지된 이슈:")
    for issue, count in sorted(filtered_issue_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {issue}: {count}회")
    
    if excluded_issues:
        print(f"\n⚠️  제외된 이슈 ({category_name} 카테고리와 무관): {', '.join(excluded_issues)}")
    
    print(f"\n✅ 생성된 Factor:")
    factors = []
    
    # 필터링된 이슈를 factor로 생성 (최소 3회 이상)
    for issue, count in sorted(filtered_issue_counts.items(), key=lambda x: x[1], reverse=True):
        if count >= 3:
            # 기존 정의가 있으면 사용, 없으면 자동 생성
            if issue in predefined_factors:
                factor = predefined_factors[issue].copy()
            else:
                # 이슈 키워드로 자동 factor 생성
                factor_key = generate_factor_key(issue, category_name)
                anchor_terms = issue.replace('/', '|')
                
                # 컨텍스트 추론
                context_map = {
                    '소음': '작동|사용|청소',
                    '가격/비용': '구매|만원|원',
                    '성능': '사용|효과|기능',
                    '고장/내구성': '사용|개월|년',
                    '청소/관리': '청소|세척|관리',
                    '크기/무게': '공간|설치|보관',
                    '배터리': '충전|시간|사용',
                    '배송': '도착|포장|배송',
                    '조립': '조립|설치|만들',
                    '냄새': '개봉|사용|작동',
                }
                
                factor = {
                    'factor_key': factor_key,
                    'display_name': issue,
                    'description': f'{issue}에 대한 불만 요인',
                    'anchor_terms': anchor_terms,
                    'context_terms': context_map.get(issue, '사용|제품'),
                    'negation_terms': '좋|만족|괜찮|없',
                    'weight': 1.0
                }
            
            factor['category'] = category_name
            factor['category_name'] = CATEGORY_NAMES.get(category_name, category_name)
            factors.append(factor)
            print(f"  ✓ {factor['factor_key']}: {factor['display_name']} ({count}회)")
    
    return factors


def generate_questions(factors):
    """Factor 기반으로 다양한 질문 생성 (factor당 2-3개)"""
    
    # 카테고리별 question_id 시작 번호 (1000단위)
    category_id_mapping = {
        'electronics_coffee_machine': 1000,
        'robot_cleaner': 2000,
        'electronics_earphone': 3000,
        'appliance_induction': 4000,
        'appliance_bedding_cleaner': 5000,
        'appliance_heated_humidifier': 6000,
        'furniture_bookshelf': 7000,
        'furniture_chair': 8000,
        'furniture_desk': 9000,
        'furniture_mattress': 10000,
    }
    
    # 카테고리별 현재 질문 번호 추적
    category_question_counters = {}
    
    def determine_answer_type(question_text):
        """질문 텍스트를 분석하여 적절한 answer_type과 choices 결정"""
        
        # 명확한 예/아니오 질문
        yes_no_patterns = ['~하시나요?', '~인가요?', '~있으신가요?', '~괜찮으신가요?', 
                          '민감하신', '자신이 있으신', '걱정되시나요']
        for pattern in yes_no_patterns:
            if pattern.replace('~', '') in question_text:
                return 'single_choice', '예|아니오|잘 모르겠음'
        
        # 중요도 질문
        importance_patterns = ['중요한', '필요한', '고려']
        for pattern in importance_patterns:
            if pattern in question_text and '?' in question_text:
                return 'single_choice', '매우 중요|보통|상관없음'
        
        # 계획/의도 질문 - 자유 답변
        if '계획' in question_text or '원하시는' in question_text or '기대' in question_text:
            return 'no_choice', ''
        
        # 비교 질문 (A인가요, 아니면 B인가요) - 자유 답변
        if '아니면' in question_text:
            return 'no_choice', ''
        
        # 기타 - 자유 답변
        return 'no_choice', ''
    
    questions = []
    
    for factor in factors:
        factor_key = factor['factor_key']
        category = factor.get('category', '')
        display_name = factor.get('display_name', factor_key)
        anchor_terms = factor.get('anchor_terms', '')
        context_terms = factor.get('context_terms', '')
        
        # 카테고리별 question_id 계산
        base_id = category_id_mapping.get(category, 0)
        if category not in category_question_counters:
            category_question_counters[category] = 1
        
        anchor_parts = anchor_terms.split('|')[:3]
        context_parts = context_terms.split('|')[:3]
        
        # Factor별 다양한 질문 패턴 생성
        factor_questions = []
        
        # 소음 관련
        if '소음' in display_name or 'noise' in factor_key.lower():
            factor_questions = [
                f'소음에 민감하신 편인가요?',
                f'{context_parts[0] if context_parts else "사용"} 시 조용한 것이 중요한가요?',
                f'야간이나 새벽에 사용하실 계획인가요?'
            ]
        
        # 가격/비용 관련
        elif '가격' in display_name or '비용' in display_name or 'price' in factor_key.lower() or 'cost' in factor_key.lower():
            factor_questions = [
                f'가격이 구매 결정에 중요한 요소인가요?',
                f'예산이 정해져 있으신가요?',
                f'장기적인 유지비용도 고려하시나요?'
            ]
        
        # 배터리 관련
        elif '배터리' in display_name or 'battery' in factor_key.lower():
            factor_questions = [
                f'한 번 충전으로 오래 사용하고 싶으신가요?',
                f'충전 없이 연속 {context_parts[0] if context_parts else "사용"}하는 시간이 중요한가요?',
                f'배터리 교체나 수명이 걱정되시나요?'
            ]
        
        # 청소/관리 관련
        elif '청소' in display_name or '관리' in display_name or 'maintenance' in factor_key.lower() or 'cleaning' in factor_key.lower():
            factor_questions = [
                f'매일 청소하거나 관리해도 괜찮으신가요?',
                f'관리가 간편한 것이 중요한가요?',
                f'{context_parts[0] if context_parts else "제품"} 유지보수에 시간을 투자할 수 있으신가요?'
            ]
        
        # 조립 관련
        elif '조립' in display_name or 'assembly' in factor_key.lower():
            factor_questions = [
                f'제품 조립을 직접 하실 수 있으신가요?',
                f'복잡한 조립 과정도 감수하실 수 있나요?',
                f'조립 시간이 오래 걸려도 괜찮으신가요?'
            ]
        
        # 배송 관련
        elif '배송' in display_name or 'delivery' in factor_key.lower():
            factor_questions = [
                f'배송 중 파손이 걱정되시나요?',
                f'포장 상태가 중요한가요?',
                f'빠른 배송보다 안전한 배송이 중요한가요?'
            ]
        
        # 크기/무게 관련
        elif '크기' in display_name or '무게' in display_name or 'size' in factor_key.lower() or 'weight' in factor_key.lower():
            factor_questions = [
                f'{context_parts[0] if context_parts else "공간"}에 맞는 크기가 중요한가요?',
                f'제품 무게가 가벼운 것이 중요한가요?',
                f'공간 활용이나 수납을 고려하시나요?'
            ]
        
        # 성능 관련
        elif '성능' in display_name or 'performance' in factor_key.lower():
            factor_questions = [
                f'{context_parts[0] if context_parts else "제품"} 성능에 대한 기대치가 높으신가요?',
                f'최고 성능이 필요하신가요, 아니면 적당하면 되나요?',
                f'성능이 가격보다 중요한가요?'
            ]
        
        # 내구성 관련
        elif '내구성' in display_name or '고장' in display_name or 'durability' in factor_key.lower():
            factor_questions = [
                f'장기간(3년 이상) 사용을 계획하고 계신가요?',
                f'제품 내구성이 중요한가요?',
                f'A/S나 수리 가능 여부를 고려하시나요?'
            ]
        
        # 냄새 관련
        elif '냄새' in display_name or 'odor' in factor_key.lower():
            factor_questions = [
                f'냄새에 민감하신 편인가요?',
                f'{context_parts[0] if context_parts else "개봉"} 시 화학 냄새가 걱정되시나요?',
                f'신제품 냄새 제거에 시간이 걸려도 괜찮으신가요?'
            ]
        
        # 거품 관련
        elif '거품' in display_name or 'foam' in factor_key.lower():
            factor_questions = [
                f'거품의 양이나 질이 중요한가요?',
                f'{display_name}이(가) 만족스러워야 하나요?'
            ]
        
        # 물조절 관련
        elif '물' in display_name or 'water' in factor_key.lower():
            factor_questions = [
                f'물 양을 직접 조절하고 싶으신가요?',
                f'{context_parts[0] if context_parts else "사용"} 시 물 관리가 중요한가요?'
            ]
        
        # 기타 (기본 2개 질문)
        else:
            factor_questions = [
                f'{display_name}이(가) 구매 결정에 중요한 요소인가요?',
                f'{context_parts[0] if context_parts else "사용"} 시 {display_name}을(를) 고려하시나요?'
            ]
        
        # 질문 추가 (최대 3개)
        for q_text in factor_questions[:3]:
            answer_type, choices = determine_answer_type(q_text)
            
            # 카테고리별 question_id 생성 (base_id + counter)
            question_id = base_id + category_question_counters[category]
            category_question_counters[category] += 1
            
            question = {
                'question_id': question_id,
                'factor_key': factor_key,
                'question_text': q_text,
                'answer_type': answer_type,
                'choices': choices,
                'next_factor_hint': ''
            }
            questions.append(question)
    
    return questions
    return questions


def save_to_csv(all_factors, all_questions):
    """Factor와 Question을 CSV에 저장"""
    
    factor_file = 'backend/data/factor/reg_factor.csv'
    question_file = 'backend/data/question/reg_question.csv'
    
    # Factor CSV 저장 (factor_key, category, category_name 순서)
    factor_df = pd.DataFrame(all_factors)
    factor_df = factor_df[['factor_key', 'category', 'category_name', 'display_name', 'description', 'anchor_terms', 'context_terms', 'negation_terms', 'weight']]
    factor_df.to_csv(factor_file, index=False, encoding='utf-8-sig')
    
    print(f"\n{'='*60}")
    print(f"✅ Factor 저장: {factor_file}")
    print(f"   총 {len(factor_df)}개 factor")
    print(f"\n카테고리별 분포:")
    for cat in factor_df['category'].unique():
        count = len(factor_df[factor_df['category'] == cat])
        cat_name = CATEGORY_NAMES.get(cat, cat)
        print(f"  - {cat_name}({cat}): {count}개")
    
    # Question CSV 저장
    question_df = pd.DataFrame(all_questions)
    question_df.to_csv(question_file, index=False, encoding='utf-8-sig')
    
    print(f"\n✅ Question 저장: {question_file}")
    print(f"   총 {len(question_df)}개 question")


def main():
    """메인 함수"""
    
    print("="*60)
    print("🔄 기존 리뷰 재분석")
    print("="*60)
    
    review_dir = Path('backend/data/review')
    
    # 최신 리뷰 파일 찾기 (날짜별로 그룹화)
    review_files = {
        'electronics_coffee_machine': None,
        'robot_cleaner': None,
        'electronics_earphone': None,
        'appliance_induction': None,
        'appliance_bedding_cleaner': None,
        'appliance_heated_humidifier': None,
        'furniture_bookshelf': None,
        'furniture_chair': None,
        'furniture_desk': None,
        'furniture_mattress': None,
    }
    
    for review_file in review_dir.glob('reviews_*_20260103_*.json'):
        filename = review_file.stem
        for category in review_files.keys():
            if category in filename:
                # 같은 카테고리의 파일 중 가장 최신 것만 선택
                if review_files[category] is None or filename > review_files[category].stem:
                    review_files[category] = review_file
    
    # 모든 카테고리의 factor와 question 수집
    all_factors = []
    all_questions = []
    
    for category, review_file in review_files.items():
        if review_file and review_file.exists():
            factors = generate_factors_from_existing_review(review_file, category)
            all_factors.extend(factors)
    
    # Question 생성
    all_questions = generate_questions(all_factors)
    
    # CSV 저장
    save_to_csv(all_factors, all_questions)
    
    print(f"\n{'='*60}")
    print("✅ 재분석 완료!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
