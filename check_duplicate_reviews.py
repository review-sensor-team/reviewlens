import json
from pathlib import Path
from collections import Counter

review_dir = Path('backend/data/review')
json_files = list(review_dir.glob('reviews_*.json'))

print(f'총 {len(json_files)}개의 JSON 파일 발견\n')

for json_file in sorted(json_files):
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # reviews 필드 추출
        if isinstance(data, dict) and 'reviews' in data:
            reviews = data['reviews']
        elif isinstance(data, list):
            reviews = data
        else:
            print(f'⚠️  {json_file.name}: 알 수 없는 형식')
            continue
        
        # 리뷰 텍스트 추출
        review_texts = []
        for review in reviews:
            if isinstance(review, dict):
                text = (review.get('review_text') or 
                       review.get('text') or 
                       review.get('content') or 
                       review.get('review_content') or '')
                review_texts.append(text.strip())
        
        # 중복 카운트
        total = len(review_texts)
        unique = len(set(review_texts))
        duplicates = total - unique
        
        print(f'📄 {json_file.name}')
        print(f'   총 리뷰: {total}개')
        print(f'   고유 리뷰: {unique}개')
        print(f'   중복: {duplicates}개')
        
        # 중복된 리뷰 상세 정보
        if duplicates > 0:
            counter = Counter(review_texts)
            dup_reviews = [(text[:50], count) for text, count in counter.items() if count > 1]
            if dup_reviews:
                print(f'   중복된 리뷰 예시:')
                for text, count in sorted(dup_reviews, key=lambda x: x[1], reverse=True)[:3]:
                    print(f'      - "{text}..." ({count}번 반복)')
        print()
        
    except Exception as e:
        print(f'❌ {json_file.name}: 오류 - {e}\n')
