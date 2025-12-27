#!/usr/bin/env python3
import json
import csv
from pathlib import Path
from datetime import datetime

INPUT = Path('scripts/reviews_api.json')
OUTPUT = Path('scripts/reviews_parsed.csv')


def ts_to_iso(ms):
    try:
        return datetime.utcfromtimestamp(ms/1000).isoformat() + 'Z'
    except Exception:
        return ''


def extract_reviews_from_obj(obj):
    reviews = []
    try:
        rd = obj.get('rData') or obj.get('data') or obj
        paging = rd.get('paging') if isinstance(rd, dict) else None
        if paging and isinstance(paging, dict):
            contents = paging.get('contents') or paging.get('list') or []
        else:
            # try common keys
            contents = []
            for key in ['reviews','reviewList','items','contents','list']:
                if key in rd and isinstance(rd[key], list):
                    contents = rd[key]
                    break
        for it in contents:
            if not isinstance(it, dict):
                continue
            review_id = it.get('reviewId') or it.get('id') or it.get('seq') or ''
            rating = it.get('rating') or it.get('score') or ''
            text = it.get('content') or it.get('reviewContent') or it.get('text') or ''
            created = it.get('createdAt') or it.get('reviewAt') or it.get('created') or ''
            created_iso = ts_to_iso(created) if isinstance(created, (int,float)) else str(created)
            reviews.append({'review_id': str(review_id), 'rating': str(rating), 'text': (text or '').replace('\n',' ').strip(), 'created_at': created_iso})
    except Exception as e:
        print('extract error', e)
    return reviews


def main():
    if not INPUT.exists():
        print('Input file missing:', INPUT)
        return
    all_reviews = []
    with INPUT.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                # try to recover if line contains leading/trailing junk
                try:
                    # find first { and last }
                    s = line
                    start = s.find('{')
                    end = s.rfind('}')
                    if start != -1 and end != -1:
                        obj = json.loads(s[start:end+1])
                    else:
                        continue
                except Exception:
                    continue
            reviews = extract_reviews_from_obj(obj)
            all_reviews.extend(reviews)

    if not all_reviews:
        print('No reviews extracted')
        return
    # write CSV
    with OUTPUT.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['review_id','rating','text','created_at'])
        writer.writeheader()
        for r in all_reviews:
            writer.writerow(r)

    print(f'Saved {len(all_reviews)} reviews -> {OUTPUT}')

if __name__ == '__main__':
    main()
