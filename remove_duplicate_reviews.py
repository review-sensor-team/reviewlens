import json
from pathlib import Path
from collections import OrderedDict

review_dir = Path('backend/data/review')
json_files = list(review_dir.glob('reviews_*.json'))

print(f'총 {len(json_files)}개의 JSON 파일 처리\n')

for json_file in sorted(json_files):
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # reviews 필드 추출
        if isinstance(data, dict) and 'reviews' in data:
            reviews = data['reviews']
            is_dict_format = True
        elif isinstance(data, list):
            reviews = data
            is_dict_format = False
        else:
            print(f'⚠️  {json_file.name}: 알 수 없는 형식, 건너뜀')
            continue
        
        # 중복 제거 (리뷰 텍스트 기준, 순서 유지)
        seen = set()
        unique_reviews = []
        
        for review in reviews:
            if isinstance(review, dict):
                text = (review.get('review_text') or 
                       review.get('text') or 
                       review.get('content') or 
                       review.get('review_content') or '').strip()
                
                if text and text not in seen:
                    seen.add(text)
                    unique_reviews.append(review)
        
        original_count = len(reviews)
        unique_count = len(unique_reviews)
        removed_count = original_count - unique_count
        
        # 데이터 저장
        if is_dict_format:
            data['reviews'] = unique_reviews
        else:
            data = unique_reviews
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f'✅ {json_file.name}')
        print(f'   원본: {original_count}개 → 중복 제거: {unique_count}개 (제거: {removed_count}개)')
        
    except Exception as e:
        print(f'❌ {json_file.name}: 오류 - {e}')

print('\n중복 제거 완료!')
