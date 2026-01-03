#!/usr/bin/env python3
"""리뷰 샘플 출력"""

import json
from pathlib import Path

file_path = Path('/Users/ssnko/app/python/reviewlens/backend/data/review/reviews_nespressokorea_electronics_coffee_machine_nespresso_20260103_102423.json')

with open(file_path, 'r', encoding='utf-8') as f:
    reviews = json.load(f)

print(f"총 {len(reviews)}개 리뷰\n")

for i, review in enumerate(reviews[:10]):
    print(f"\n[리뷰 {i+1}] 별점: {review.get('rating')}점")
    print(f"내용: {review.get('content', '')[:200]}...")
