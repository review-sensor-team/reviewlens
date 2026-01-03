#!/usr/bin/env python3
"""
수집된 리뷰에서 추가 factor를 발견하는 스크립트
"""

import json
import pandas as pd
from pathlib import Path
from collections import Counter
import re

def analyze_reviews_for_factors(review_file):
    """리뷰 파일에서 추가 factor 후보 찾기"""
    
    with open(review_file, 'r', encoding='utf-8') as f:
        reviews = json.load(f)
    
    print(f"\n{'='*80}")
    print(f"파일: {review_file.name}")
    print(f"총 리뷰: {len(reviews)}개")
    
    # 별점 분포 확인
    ratings = [r.get('rating', 5) for r in reviews]
    low_ratings = [r for r in ratings if r <= 3]
    print(f"별점 3점 이하: {len(low_ratings)}개")
    print(f"{'='*80}")
    
    # 부정적 키워드 패턴
    negative_patterns = {
        '배송': ['배송|택배|포장|박스|파손|상자'],
        'A/S': ['AS|A/S|서비스|센터|수리|교환|환불|반품'],
        '설치': ['설치|조립|시공|공사'],
        '냄새': ['냄새|악취|냄|향|페인트'],
        '디자인': ['디자인|외관|색상|색깔|모양|생김'],
        '호환성': ['호환|연동|페어링|앱|어플'],
        '보증': ['보증|워런티|품질보증'],
        '사용법': ['사용법|설명서|매뉴얼|조작|복잡'],
        '내구성': ['내구성|튼튼|약함|부서|깨짐|파손'],
        '효과': ['효과|성능|효율|잘안됨'],
        '안전': ['안전|위험|화상|다침'],
        '전력': ['전력|전기|소비전력|와트'],
        '용량': ['용량|크기|양|적음|부족'],
        '속도': ['속도|느림|빠름|시간'],
    }
    
    # 패턴별 발견 문장
    pattern_sentences = {key: [] for key in negative_patterns.keys()}
    
    low_rating_count = 0
    for review in reviews[:200]:  # 처음 200개 리뷰만 분석
        content = review.get('text', review.get('content', ''))
        rating = review.get('rating', 5)
        
        # 별점 3점 이하만 분석
        if rating > 3:
            continue
        
        low_rating_count += 1
            
        # 문장 분리
        sentences = re.split(r'[.!?\n]+', content)
        
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 5:
                continue
                
            # 부정적 표현 확인
            if not any(w in sent for w in ['아쉽', '불편', '실망', '후회', '별로', '안좋', '나쁨', '문제', '고장', '짜증']):
                continue
            
            # 패턴 매칭
            for category, patterns in negative_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, sent):
                        if len(pattern_sentences[category]) < 3:  # 각 카테고리당 최대 3개
                            pattern_sentences[category].append(sent)
                        break
    
    # 결과 출력
    print(f"\n분석한 저별점 리뷰: {low_rating_count}개")
    
    found_any = False
    for category, sentences in pattern_sentences.items():
        if sentences:
            found_any = True
            print(f"\n🔍 [{category}] 관련 불만 ({len(sentences)}건)")
            for sent in sentences[:3]:
                display = sent[:120] + "..." if len(sent) > 120 else sent
                print(f"  - {display}")
    
    if not found_any:
        print("\n⚠️  특정 패턴의 불만을 찾지 못했습니다.")

def main():
    """메인 함수"""
    
    # 최신 리뷰 파일들
    review_dir = Path('/Users/ssnko/app/python/reviewlens/backend/data/review')
    
    latest_files = [
        'reviews_nespressokorea_electronics_coffee_machine_nespresso_20260103_102423.json',
        'reviews_everybot_robot_cleaner_everybot_20260103_102607.json',
        'reviews_applestore_electronics_earphone_airpods_20260103_102755.json',
        'reviews_cuckoo_appliance_induction_cuckoo_20260103_102937.json',
        'reviews_haan_appliance_bedding_cleaner_haan_20260103_103114.json',
        'reviews_hanssemmall_furniture_bookshelf_hanssem_20260103_103627.json',
    ]
    
    print("\n" + "="*80)
    print("📊 리뷰 분석: 추가 Factor 발견")
    print("="*80)
    
    for filename in latest_files:
        file_path = review_dir / filename
        if file_path.exists():
            analyze_reviews_for_factors(file_path)
    
    # 현재 factor 목록 출력
    print("\n" + "="*80)
    print("📝 현재 등록된 Factor 목록")
    print("="*80)
    
    factor_file = Path('/Users/ssnko/app/python/reviewlens/backend/data/factor/reg_factor.csv')
    if factor_file.exists():
        df = pd.read_csv(factor_file)
        categories = df['category'].unique()
        
        for cat in sorted(categories):
            cat_factors = df[df['category'] == cat]
            print(f"\n[{cat}] ({len(cat_factors)}개)")
            for _, row in cat_factors.iterrows():
                print(f"  - {row['factor_key']}: {row['display_name']}")
    
    print("\n" + "="*80)
    print("💡 추천 추가 Factor")
    print("="*80)
    print("""
공통 Factor (모든 카테고리):
  - delivery_packaging: 배송/포장 상태 (파손, 포장 불량)
  - as_service: A/S 서비스 품질 (교환, 환불, 고객센터 응대)
  - manual_complexity: 사용법/설명서 복잡성
  - design_appearance: 디자인/외관 불만족

제품별 특화 Factor:
  [전자제품]
  - app_compatibility: 앱 호환성/연동 문제
  - warranty_period: 보증 기간 부족
  - power_consumption: 전력 소비 과다
  
  [가구]
  - assembly_difficulty: 조립 난이도
  - installation_service: 설치/시공 품질
  - space_fit: 공간 활용/배치 문제
  
  [가전]
  - smell_issue: 냄새 문제 (신제품 냄새, 작동 중 냄새)
  - safety_concern: 안전 우려 (화상, 과열)
  - capacity_shortage: 용량 부족
    """)

if __name__ == '__main__':
    main()
