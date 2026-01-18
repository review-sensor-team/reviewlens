"""
프롬프트 팩토리 테스트

실행 방법:
    cd /Users/ssnko/app/python/reviewlens
    python -m backend.llm.test_prompt_factory
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from llm.prompt_factory import PromptFactory
from llm.llm_base import PromptBuilder


def test_list_strategies():
    """사용 가능한 전략 목록 조회"""
    print("=" * 80)
    print("테스트 1: 사용 가능한 전략 목록")
    print("=" * 80)
    
    strategies = PromptFactory.list_available_strategies()
    print(f"사용 가능한 전략: {strategies}")
    print()


def test_load_default_strategy():
    """기본 전략 로드 테스트"""
    print("=" * 80)
    print("테스트 2: 기본 전략 (default) 로드")
    print("=" * 80)
    
    strategy = PromptFactory.create(strategy="default")
    print(f"전략 이름: {strategy.name}")
    print(f"설명: {strategy.description}")
    print(f"버전: {strategy.version}")
    print()
    
    # 시스템 프롬프트
    system_prompt = strategy.build_system_prompt()
    print("시스템 프롬프트:")
    print(system_prompt[:200] + "...")
    print()


def test_load_all_strategies():
    """모든 전략 로드 테스트"""
    print("=" * 80)
    print("테스트 3: 모든 전략 로드")
    print("=" * 80)
    
    strategies = PromptFactory.list_available_strategies()
    
    for strategy_name in strategies:
        print(f"\n[{strategy_name}]")
        strategy = PromptFactory.create(strategy=strategy_name)
        print(f"  이름: {strategy.name}")
        print(f"  설명: {strategy.description}")
        print(f"  시스템 프롬프트 길이: {len(strategy.build_system_prompt())} 글자")
    print()


def test_prompt_generation():
    """프롬프트 생성 테스트"""
    print("=" * 80)
    print("테스트 4: 프롬프트 생성 (default 전략)")
    print("=" * 80)
    
    # 샘플 데이터
    top_factors = [
        ("noise_loud", 8.5),
        ("motor_weak", 7.2),
        ("battery_short", 6.1)
    ]
    
    evidence_reviews = [
        {"label": "NEG", "rating": 2, "excerpt": "소음이 너무 심해서 아침에 사용하기 곤란합니다"},
        {"label": "MIX", "rating": 3, "excerpt": "성능은 괜찮은데 배터리가 금방 닳아요"},
        {"label": "POS", "rating": 4, "excerpt": "가격 대비 나쁘지 않습니다"}
    ]
    
    dialogue_history = [
        {"role": "user", "message": "무선청소기 구매 고민 중입니다"},
        {"role": "assistant", "message": "어떤 점이 가장 중요하신가요?"},
        {"role": "user", "message": "소음이 적었으면 좋겠어요"}
    ]
    
    # 기본 전략으로 프롬프트 생성
    strategy = PromptFactory.create(strategy="default")
    user_prompt = strategy.build_user_prompt(
        top_factors=top_factors,
        evidence_reviews=evidence_reviews,
        total_turns=3,
        category_name="무선청소기",
        product_name="테스트 청소기 X100",
        dialogue_history=dialogue_history
    )
    
    print("생성된 유저 프롬프트:")
    print(user_prompt[:500] + "...")
    print()


def test_strategy_comparison():
    """전략별 비교 테스트"""
    print("=" * 80)
    print("테스트 5: 전략별 시스템 프롬프트 비교")
    print("=" * 80)
    
    strategies = ["default", "concise", "detailed", "friendly"]
    
    for strategy_name in strategies:
        try:
            strategy = PromptFactory.create(strategy=strategy_name)
            system_prompt = strategy.build_system_prompt()
            
            print(f"\n[{strategy_name}]")
            print(f"{system_prompt[:150]}...")
            print(f"(총 {len(system_prompt)} 글자)")
        except Exception as e:
            print(f"\n[{strategy_name}] 로드 실패: {e}")
    print()


def test_prompt_builder_integration():
    """PromptBuilder 통합 테스트"""
    print("=" * 80)
    print("테스트 6: PromptBuilder 통합 (레거시 호환성)")
    print("=" * 80)
    
    # PromptBuilder를 통한 사용 (기존 코드와 동일하게 사용 가능)
    system_prompt = PromptBuilder.build_system_prompt()
    print(f"시스템 프롬프트 (PromptBuilder): {system_prompt[:100]}...")
    print()
    
    # 전략 변경 테스트
    print("전략을 'friendly'로 변경...")
    PromptBuilder.set_strategy("friendly")
    
    system_prompt = PromptBuilder.build_system_prompt()
    print(f"시스템 프롬프트 (friendly): {system_prompt[:100]}...")
    print()


def main():
    """전체 테스트 실행"""
    try:
        test_list_strategies()
        test_load_default_strategy()
        test_load_all_strategies()
        test_prompt_generation()
        test_strategy_comparison()
        test_prompt_builder_integration()
        
        print("=" * 80)
        print("✅ 모든 테스트 완료!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
