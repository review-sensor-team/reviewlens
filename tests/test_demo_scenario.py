import json
from pathlib import Path

import pytest

from backend.pipeline.dialogue import DialogueSession


def test_demo_3to5_turns():
    # 세션 시작
    session = DialogueSession(category="appliance_heated_humidifier", data_dir="backend/data")

    # 시나리오에 따른 사용자 입력들
    user_turns = [
        "밤에 가동하면 너무 시끄럽나요?",
        "잠자기 전에 틀면 팬 소리가 거슬려서 잠이 어려워요",
        "네, 팬 소리가 지속적으로 들리고 밤에 더 신경써져요",
    ]

    expected_final_factor = "noise_sleep"

    bot_turn = None
    for i, umsg in enumerate(user_turns, start=1):
        bot_turn = session.step(umsg)
        # 질문 텍스트는 비어있지 않아야 함
        assert bot_turn.question_text is None or isinstance(bot_turn.question_text, str)
        # top_factors 존재
        assert bot_turn.top_factors and isinstance(bot_turn.top_factors[0][0], str)

        # if not final, question should exist
        if not bot_turn.is_final:
            # collect candidate questions from questions_df for top_factors
            candidates = set()
            for fk, _ in bot_turn.top_factors:
                matches = session.questions_df[session.questions_df['factor_key'] == fk]
                for rec in matches.to_dict(orient="records"):
                    # question_text 또는 question 컬럼 확인
                    q_text = rec.get("question_text") or rec.get("question") or ""
                    if q_text:
                        candidates.add(str(q_text))
            
            # 질문이 있어야 함
            assert bot_turn.question_text is not None
            # 질문이 candidates에 있거나, 기본 질문이어야 함
            if len(candidates) > 0:
                assert bot_turn.question_text in candidates or "궁금하신" in bot_turn.question_text

    # After the simulated turns, we should have a final turn (either by stability or reaching 3)
    assert bot_turn is not None
    # If not final yet, keep stepping until final (up to 5)
    while not bot_turn.is_final and session.turn < 5:
        bot_turn = session.step("계속 사례 추가합니다")

    assert bot_turn.is_final is True
    assert bot_turn.llm_context is not None

    # 타임스탬프 기반 파일이 생성되었는지 확인
    out_dir = Path("out")
    json_files = list(out_dir.glob("llm_context_demo.*.json"))
    assert len(json_files) > 0, "No timestamped JSON files found"
    
    # 가장 최근 파일 확인
    latest_json = sorted(json_files)[-1]
    assert latest_json.exists()
    
    with latest_json.open("r", encoding="utf-8") as f:
        ctx = json.load(f)

    # evidence_reviews 길이 검사
    evidence = ctx.get("evidence_reviews") or []
    assert len(evidence) >= 3, f"evidence_reviews too small: {len(evidence)}"

    # top_factors 상위 1개가 기대 factor로 고정되었는지 검사
    topf = ctx.get("top_factors") or []
    assert topf and topf[0].get("factor_key") == expected_final_factor
    
    # dialogue_history 존재 확인
    assert "dialogue_history" in ctx
    assert len(ctx["dialogue_history"]) > 0
    
    # safety_rules 존재 확인
    assert "safety_rules" in ctx
    assert len(ctx["safety_rules"]) == 3
