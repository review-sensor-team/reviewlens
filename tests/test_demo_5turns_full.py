#!/usr/bin/env python3
"""DEMO_SCENARIO_5TURNS.md 시나리오 테스트"""
import json
from pathlib import Path
import pytest
from backend.pipeline.dialogue import DialogueSession


def test_demo_5turns_full_scenario():
    """5턴 시나리오 전체 테스트 (DEMO_SCENARIO_5TURNS.md 기준)"""
    
    # 세션 시작
    session = DialogueSession(category="appliance_heated_humidifier", data_dir="backend/data")
    
    # Turn 1: 사용자 첫 질문
    user_msg_1 = "가열식 가습기 밤에 틀어도 괜찮을까요? 소음이 걱정돼요."
    bot_turn_1 = session.step(user_msg_1)
    
    print(f"\n=== Turn 1 ===")
    print(f"User: {user_msg_1}")
    print(f"Bot: {bot_turn_1.question_text}")
    print(f"Top factors: {bot_turn_1.top_factors}")
    
    assert not bot_turn_1.is_final
    assert len(bot_turn_1.top_factors) > 0
    assert bot_turn_1.top_factors[0][0] == "noise_sleep", "Turn 1에서 noise_sleep이 top이어야 함"
    
    # Turn 2
    user_msg_2 = "네, 아이 방에서 밤에 켜둘 것 같아요."
    bot_turn_2 = session.step(user_msg_2)
    
    print(f"\n=== Turn 2 ===")
    print(f"User: {user_msg_2}")
    print(f"Bot: {bot_turn_2.question_text}")
    print(f"Top factors: {bot_turn_2.top_factors}")
    
    assert not bot_turn_2.is_final
    assert bot_turn_2.top_factors[0][0] == "noise_sleep", "Turn 2에서도 noise_sleep이 top이어야 함 (안정화)"
    
    # Turn 3
    user_msg_3 = "빛도 싫고, 기계 소리에도 예민해요."
    bot_turn_3 = session.step(user_msg_3)
    
    print(f"\n=== Turn 3 ===")
    print(f"User: {user_msg_3}")
    print(f"Bot: {bot_turn_3.question_text if not bot_turn_3.is_final else 'FINAL'}")
    print(f"Top factors: {bot_turn_3.top_factors[:3]}")
    
    # Turn 3에서 종료될 수도 있고 계속될 수도 있음
    if bot_turn_3.is_final:
        print("\n=== 3턴에서 종료됨 ===")
        assert bot_turn_3.top_factors[0][0] == "noise_sleep"
        assert bot_turn_3.llm_context is not None
        assert "dialogue_history" in bot_turn_3.llm_context
        assert "safety_rules" in bot_turn_3.llm_context
        assert "calculation_info" in bot_turn_3.llm_context
        print(f"대화 턴 수: {bot_turn_3.llm_context['calculation_info']['total_turns']}")
    else:
        # 계속 진행
        top_2_factors = [f[0] for f in bot_turn_3.top_factors[:2]]
        assert "noise_sleep" in top_2_factors, "noise_sleep이 상위 2개에 있어야 함"
        
        # Turn 4
        user_msg_4 = "조금 기다려도 되는데, 청소는 귀찮아요."
        bot_turn_4 = session.step(user_msg_4)
        
        print(f"\n=== Turn 4 ===")
        print(f"User: {user_msg_4}")
        print(f"Bot: {bot_turn_4.question_text if not bot_turn_4.is_final else 'FINAL'}")
        print(f"Top factors: {bot_turn_4.top_factors[:3]}")
        
        if bot_turn_4.is_final:
            print("\n=== 4턴에서 종료됨 ===")
            top_2_factors = [f[0] for f in bot_turn_4.top_factors[:2]]
            assert "noise_sleep" in top_2_factors
            assert bot_turn_4.llm_context is not None
            print(f"대화 턴 수: {bot_turn_4.llm_context['calculation_info']['total_turns']}")
        else:
            # Turn 5
            user_msg_5 = "아이랑 같이 쓰고, 따뜻한 수증기가 좋아요."
            bot_turn_5 = session.step(user_msg_5)
            
            print(f"\n=== Turn 5 ===")
            print(f"User: {user_msg_5}")
            print(f"Bot: FINAL")
            print(f"Top factors: {bot_turn_5.top_factors[:3]}")
            
            assert bot_turn_5.is_final, "5턴에서는 반드시 종료되어야 함"
            assert bot_turn_5.llm_context is not None
            
            print(f"\n=== 최종 결과 ===")
            print(f"대화 턴 수: {bot_turn_5.llm_context['calculation_info']['total_turns']}")
            print(f"최종 top factors: {[f['factor_key'] for f in bot_turn_5.llm_context['top_factors']]}")
            print(f"증거 리뷰 수: {len(bot_turn_5.llm_context['evidence_reviews'])}")
            print(f"대화 히스토리 길이: {len(bot_turn_5.llm_context['dialogue_history'])}")
            
            # 검증
            assert "dialogue_history" in bot_turn_5.llm_context
            assert "safety_rules" in bot_turn_5.llm_context
            assert "calculation_info" in bot_turn_5.llm_context
            assert len(bot_turn_5.llm_context["safety_rules"]) == 3
            
            # 타임스탬프 파일 생성 확인
            out_dir = Path("out")
            json_files = list(out_dir.glob("llm_context_demo.*.json"))
            prompt_files = list(out_dir.glob("prompt_demo.*.txt"))
            
            assert len(json_files) > 0, "JSON 파일이 생성되어야 함"
            assert len(prompt_files) > 0, "프롬프트 파일이 생성되어야 함"
            
            # 최신 파일 확인
            latest_json = sorted(json_files)[-1]
            latest_prompt = sorted(prompt_files)[-1]
            
            print(f"\n생성된 파일:")
            print(f"  - {latest_json.name}")
            print(f"  - {latest_prompt.name}")
            
            # JSON 파일에 calculation_info가 없어야 함 (LLM API용)
            with latest_json.open("r", encoding="utf-8") as f:
                saved_ctx = json.load(f)
                assert "calculation_info" not in saved_ctx, "저장된 JSON에는 calculation_info가 없어야 함"
                assert "safety_rules" in saved_ctx
                assert "dialogue_history" in saved_ctx


if __name__ == "__main__":
    test_demo_5turns_full_scenario()
