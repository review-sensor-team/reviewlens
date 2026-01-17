#!/bin/bash

# 10개 제품 일괄 분석 스크립트
cd /Users/ssnko/app/python/reviewlens
source .venv/bin/activate

echo "=================================="
echo "🚀 10개 제품 일괄 분석 시작"
echo "=================================="

# 1. 네스프레소 버츄오플러스
echo -e "\n[1/10] 네스프레소 버츄오플러스..."
python scripts/analyze_product_reviews.py https://brand.naver.com/nespressokorea/products/5762090671

# 2. 에브리봇 로봇청소기
echo -e "\n[2/10] 에브리봇 로봇청소기..."
python scripts/analyze_product_reviews.py https://brand.naver.com/everybot/products/11163824445

# 3. 애플 에어팟 프로 3
echo -e "\n[3/10] 애플 에어팟 프로 3..."
python scripts/analyze_product_reviews.py https://brand.naver.com/applestore/products/12381514295

# 4. 쿠쿠 인덕션
echo -e "\n[4/10] 쿠쿠 인덕션..."
python scripts/analyze_product_reviews.py https://brand.naver.com/cuckoo/products/5985503969

# 5. 한경희 침구청소기
echo -e "\n[5/10] 한경희 침구청소기..."
python scripts/analyze_product_reviews.py https://brand.naver.com/haan/products/9619286590

# 6. 루메나 가습기
echo -e "\n[6/10] 루메나 가습기..."
python scripts/analyze_product_reviews.py https://brand.naver.com/lumena/products/12428597856

# 7. 한샘 책장
echo -e "\n[7/10] 한샘 책장..."
python scripts/analyze_product_reviews.py https://brand.naver.com/hanssemmall/products/472505899

# 8. 시디즈 의자
echo -e "\n[8/10] 시디즈 의자..."
python scripts/analyze_product_reviews.py https://brand.naver.com/sidiz/products/11589555609

# 9. 데스커 책상
echo -e "\n[9/10] 데스커 책상..."
python scripts/analyze_product_reviews.py https://brand.naver.com/desker/products/4144647046

# 10. 지누스 매트리스
echo -e "\n[10/10] 지누스 매트리스..."
python scripts/analyze_product_reviews.py https://brand.naver.com/zinus/products/3743902988

echo -e "\n=================================="
echo "✅ 10개 제품 분석 완료!"
echo "=================================="

# 최종 통계
python -c "
import pandas as pd
factor_df = pd.read_csv('backend/data/factor/reg_factor.csv')
question_df = pd.read_csv('backend/data/question/reg_question.csv')

print('\n📊 최종 통계')
print('='*50)
print(f'총 Factor: {len(factor_df)}개')
print(f'총 Question: {len(question_df)}개')
print(f'\n카테고리별 Factor:')
for cat in sorted(factor_df['category'].unique()):
    count = len(factor_df[factor_df['category'] == cat])
    print(f'  - {cat}: {count}개')
"
