#!/usr/bin/env python3
"""다중 프롬프트 전략 테스트"""
import sys
import os
from pathlib import Path

# 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

# 환경 변수 설정 (테스트용)
os.environ['PROMPT_STRATEGY'] = 'default,friendly'

from backend.app.core.settings import Settings

def test_strategy_parsing():
    """전략 파싱 테스트"""
    print('=' * 80)
    print('다중 프롬프트 전략 파싱 테스트')
    print('=' * 80)
    print()
    
    settings = Settings()
    
    # 1. 기본 설정 확인
    print(f'PROMPT_STRATEGY 원본: "{settings.PROMPT_STRATEGY}"')
    print()
    
    # 2. 파싱 결과
    strategies = settings.get_prompt_strategies()
    print(f'파싱 결과: {strategies}')
    print(f'전략 개수: {len(strategies)}')
    print()
    
    # 3. 각 전략 출력
    for i, strategy in enumerate(strategies, 1):
        print(f'{i}. {strategy}')
    print()
    
    # 4. 다양한 케이스 테스트
    test_cases = [
        ('default', ['default']),
        ('default,friendly', ['default', 'friendly']),
        ('default, friendly, concise', ['default', 'friendly', 'concise']),
        ('default,concise,detailed,friendly', ['default', 'concise', 'detailed', 'friendly']),
        ('', ['default']),  # 빈 문자열
        ('  default  ,  friendly  ', ['default', 'friendly']),  # 공백 포함
    ]
    
    print('=' * 80)
    print('다양한 케이스 테스트')
    print('=' * 80)
    print()
    
    for input_str, expected in test_cases:
        os.environ['PROMPT_STRATEGY'] = input_str
        settings = Settings()
        result = settings.get_prompt_strategies()
        
        status = '✅' if result == expected else '❌'
        print(f'{status} 입력: "{input_str}"')
        print(f'   기대: {expected}')
        print(f'   결과: {result}')
        print()

if __name__ == '__main__':
    test_strategy_parsing()
    print('✅ 테스트 완료!')
