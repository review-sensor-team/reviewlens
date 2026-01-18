#!/usr/bin/env python3
"""프롬프트 팩토리 간단 테스트"""
import sys
from pathlib import Path

# 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.llm.prompt_factory import PromptFactory

def main():
    print('=' * 80)
    print('프롬프트 팩토리 테스트')
    print('=' * 80)
    print()
    
    # 1. 사용 가능한 전략 목록
    strategies = PromptFactory.list_available_strategies()
    print(f'사용 가능한 전략: {strategies}')
    print()
    
    # 2. 각 전략 테스트
    for strategy_name in strategies:
        print(f'[{strategy_name}] 전략 테스트')
        strategy = PromptFactory.create(strategy=strategy_name)
        print(f'  이름: {strategy.name}')
        print(f'  설명: {strategy.description}')
        
        system_prompt = strategy.build_system_prompt()
        print(f'  시스템 프롬프트: {system_prompt[:120]}...')
        print(f'  (총 {len(system_prompt)} 글자)')
        print()
    
    # 3. 프롬프트 생성 테스트
    print('=' * 80)
    print('프롬프트 생성 테스트 (default 전략)')
    print('=' * 80)
    print()
    
    strategy = PromptFactory.create(strategy='default')
    
    # 샘플 데이터
    top_factors = [
        ("noise_loud", 8.5),
        ("motor_weak", 7.2),
    ]
    
    evidence_reviews = [
        {"label": "NEG", "rating": 2, "excerpt": "소음이 심합니다"},
        {"label": "MIX", "rating": 3, "excerpt": "성능은 보통입니다"},
    ]
    
    user_prompt = strategy.build_user_prompt(
        top_factors=top_factors,
        evidence_reviews=evidence_reviews,
        total_turns=3,
        category_name="무선청소기",
        product_name="테스트 청소기",
        dialogue_history=None
    )
    
    print(f'생성된 유저 프롬프트 ({len(user_prompt)} 글자):')
    print(user_prompt[:400])
    print('...')
    print()
    
    print('✅ 모든 테스트 성공!')

if __name__ == '__main__':
    main()
