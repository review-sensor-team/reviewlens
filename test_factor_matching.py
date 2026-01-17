from pathlib import Path
from backend.app.domain.reg.store import load_csvs, parse_factors
from backend.app.domain.review.normalize import normalize_text

factor_csv, question_csv = load_csvs(Path('backend/data'))
factors = parse_factors(factor_csv)

print(f'\n총 {len(factors)}개의 factor 로드됨\n')

# noise 관련 factor 확인
noise_factors = [f for f in factors if 'noise' in f.factor_key]
print(f'Noise 관련 factor: {len(noise_factors)}개\n')

for f in noise_factors:
    print(f'Factor: {f.factor_key}')
    print(f'  - anchor_terms ({len(f.anchor_terms)}개): {f.anchor_terms[:5]}...')
    print(f'  - context_terms ({len(f.context_terms)}개): {f.context_terms[:5]}...')
    print(f'  - weight: {f.weight}')
    print()

# 정규화 테스트
test_msgs = [
    '밤에 가동하면 너무 시끄럽나요?',
    '가열식 가습기 밤에 틀어도 괜찮을까요? 소음이 걱정돼요.',
]

for test_msg in test_msgs:
    norm = normalize_text(test_msg)
    print(f'\n원본: {test_msg}')
    print(f'정규화: {norm}')
    print('매칭 결과:')
    
    for f in noise_factors:
        matched_anchor = [t for t in f.anchor_terms if t in norm]
        matched_context = [t for t in f.context_terms if t in norm]
        if matched_anchor or matched_context:
            print(f'  - {f.factor_key}: anchor={matched_anchor}, context={matched_context}')
    print()
