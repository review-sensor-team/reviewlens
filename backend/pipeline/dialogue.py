#!/usr/bin/env python3
"""Dialogue engine: 3-5 turn conversation for factor convergence"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd

from .reg_store import Factor, load_csvs, parse_factors
from .sensor import compute_review_factor_scores
from .ingest import normalize
from .retrieval import retrieve_evidence_reviews


@dataclass
class BotTurn:
    """챗봇 턴 결과"""
    question_text: Optional[str]
    top_factors: List[Tuple[str, float]]
    is_final: bool
    llm_context: Optional[Dict] = None
    # 질문 정보
    question_id: Optional[str] = None
    answer_type: Optional[str] = None  # 'no_choice' | 'single_choice'
    choices: Optional[str] = None  # '예|아니오|잘 모르겠음' 형식


def _jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


class DialogueSession:
    """3~5턴 대화 세션(수렴 로직: top3 Jaccard 기반)"""

    def __init__(self, category: str, data_dir: str | Path):
        self.category = category
        self.data_dir = Path(data_dir)

        self.turn_count = 0
        self.cumulative_scores: Dict[str, float] = {}

        # 수렴 체크용
        self.prev_top3: List[str] = []
        self.stability_hits = 0  # 유사도 기준 안정 횟수

        self.asked_questions: set[str] = set()
        self.dialogue_history: List[Dict[str, str]] = []

        # 캐시(성능)
        self.scored_df: Optional[pd.DataFrame] = None
        self.factor_counts: Optional[Dict[str, int]] = None

        # Load data
        self.reviews_df, self.factors_df, self.questions_df = load_csvs(self.data_dir)
        self.factors = parse_factors(self.factors_df)
        self.factors_map = {f.factor_key: f for f in self.factors}

        # category slug 추출(빈 값이면 fallback)
        self.category_slug = category
        for f in self.factors:
            if getattr(f, "category", "").strip():
                self.category_slug = f.category.strip()
                break

        # 질문 DF 컬럼 유연화(한 번만 결정)
        self.q_key_col = None
        for c in ["factor_key", "factor", "key"]:
            if c in self.questions_df.columns:
                self.q_key_col = c
                break

        self.q_text_col = None
        for c in ["question_text", "question", "text"]:
            if c in self.questions_df.columns:
                self.q_text_col = c
                break

        self.q_prio_col = "priority" if "priority" in self.questions_df.columns else None

    # ----------------------------- public -----------------------------

    def step(self, user_message: str) -> BotTurn:
        """사용자 메시지 처리 및 다음 질문 생성"""
        self.turn_count += 1

        # 히스토리: user
        self.dialogue_history.append({"role": "user", "message": user_message})

        # 1) 사용자 메시지로 factor 점수 누적(negation 감점 X)
        norm = normalize(user_message)
        for f in self.factors:
            base = 0.0
            if any(t in norm for t in f.anchor_terms):
                base += 1.0
            if any(t in norm for t in f.context_terms):
                base += 0.3

            ws = base * float(getattr(f, "weight", 1.0) or 1.0)
            if ws > 0:
                self.cumulative_scores[f.factor_key] = self.cumulative_scores.get(f.factor_key, 0.0) + ws

        # 2) 상위 요인 계산(top3)
        top_factors = self._get_top_factors(top_k=3)

        # 3) 수렴(안정성) 체크: top3 Jaccard
        cur_top3 = [k for k, _ in top_factors]
        sim = _jaccard(cur_top3, self.prev_top3) if self.prev_top3 else 0.0
        if sim >= 0.67:  # 3개 중 2개 이상 같으면 꽤 안정
            self.stability_hits += 1
        else:
            self.stability_hits = 1
        self.prev_top3 = cur_top3

        # 4) 종료 조건
        # - 최소 3턴
        # - 안정성(유사도) 2회 연속 충족이면 종료
        # - 또는 최대 5턴에서 강제 종료
        is_final = (self.turn_count >= 3 and self.stability_hits >= 2) or (self.turn_count >= 5)

        if is_final:
            return self._finalize(top_factors)

        # 5) 다음 질문 1개 생성(상위요인 중심 + 중복방지)
        question_text, question_id, answer_type, choices = self._pick_next_question(top_factors)

        # 히스토리: assistant
        self.dialogue_history.append({"role": "assistant", "message": question_text})

        return BotTurn(
            question_text=question_text,
            top_factors=top_factors,
            is_final=False,
            question_id=question_id,
            answer_type=answer_type,
            choices=choices
        )

    # ----------------------------- internals -----------------------------

    def _get_top_factors(self, top_k: int = 3) -> List[Tuple[str, float]]:
        if self.cumulative_scores:
            sorted_f = sorted(self.cumulative_scores.items(), key=lambda x: x[1], reverse=True)
            top = [(k, float(s)) for k, s in sorted_f if s > 0][:top_k]
            if top:
                return top

        # fallback: weight 상위
        if self.factors:
            by_w = sorted(self.factors, key=lambda x: float(getattr(x, "weight", 1.0) or 1.0), reverse=True)[:top_k]
            return [(f.factor_key, float(getattr(f, "weight", 1.0) or 1.0)) for f in by_w]
        return []

    def _pick_next_question(self, top_factors: List[Tuple[str, float]]) -> str:
        # 질문 테이블이 없으면 기본 질문
        if self.questions_df is None or self.questions_df.empty or not self.q_key_col or not self.q_text_col:
            return self._fallback_question()

        # “집중 수렴” 전략:
        # - turn 1~2: top2까지 후보
        # - turn 3부터: top1에 더 집중
        focus = 2 if self.turn_count <= 2 else 1
        focus_factors = [k for k, _ in top_factors[:focus]]

        candidates: List[Tuple[int, str]] = []
        for factor_key in focus_factors:
            matches = self.questions_df[self.questions_df[self.q_key_col] == factor_key]

            # 부분일치(예: noise_sleep vs noise)
            if len(matches) == 0:
                prefix = factor_key.split("_")[0]
                matches = self.questions_df[self.questions_df[self.q_key_col].astype(str).str.contains(prefix, na=False)]

            if len(matches) == 0:
                continue

            for rec in matches.to_dict(orient="records"):
                q_text = str(rec.get(self.q_text_col) or "").strip()
                if not q_text:
                    continue
                if q_text in self.asked_questions:
                    continue

                prio = 999
                if self.q_prio_col:
                    try:
                        prio = int(rec.get(self.q_prio_col) or 999)
                    except Exception:
                        prio = 999

                candidates.append((prio, q_text))

        # 우선순위 낮은 숫자 먼저
        candidates.sort(key=lambda x: x[0])

        if candidates:
            picked = candidates[0][1]
            self.asked_questions.add(picked)
            return picked

        return self._fallback_question()

    def _fallback_question(self) -> str:
        defaults = [
            "구매 전에 가장 걱정되는 점(소음/관리/내구성/안전 등) 하나만 콕 집어 말해줄래요?",
            "사용 환경(방 크기, 사용 시간대, 민감한 요소)을 알려주면 더 정확히 볼 수 있어요. 어떤 환경인가요?",
            "비슷한 제품에서 예전에 실망했던 경험이 있다면 무엇이었나요?",
        ]
        for q in defaults:
            if q not in self.asked_questions:
                self.asked_questions.add(q)
                return q
        return "추가로 고려하시는 부분이 있나요?"

    def _finalize(self, top_factors: List[Tuple[str, float]]) -> BotTurn:
        # 1) 리뷰 스코어 계산(캐싱)
        if self.scored_df is None or self.factor_counts is None:
            self.scored_df, self.factor_counts = compute_review_factor_scores(self.reviews_df, self.factors)

        # 2) evidence 추출(label 포함됨: retrieval.py에서 생성 + quota 적용)
        evidence = retrieve_evidence_reviews(
            self.scored_df,
            self.factors_map,
            [(k, s) for k, s in top_factors],
            per_factor_limit=(8, 8),
            max_total_evidence=15,  # ✅ 전체 증거 상한
            quota_by_rank={  # ✅ rank별 quota(원하면 튜닝)
                0: {"NEG": 3, "MIX": 2, "POS": 1},  # top1
                1: {"NEG": 2, "MIX": 2, "POS": 1},  # top2
                2: {"NEG": 2, "MIX": 2, "POS": 1},  # top3
            },
        )

        safety_rules = [
            "가짜리뷰 여부를 단정하지 말 것",
            "근거 리뷰는 짧게 인용할 것",
            "의학/법률 조언 금지",
        ]

        calculation_info = {
            "total_turns": self.turn_count,
            "convergence": {
                "method": "top3_jaccard",
                "stability_hits": self.stability_hits,
                "prev_top3": self.prev_top3,
            },
            "scoring_formula": "base_score × factor_weight × rating_multiplier",
            "rating_multiplier_formula": "1.0 + (5 - rating) × 0.2",
            "cumulative_scores": {k: round(v, 2) for k, v in self.cumulative_scores.items()},
            "factor_definitions": [
                {
                    "factor_key": f.factor_key,
                    "display_name": getattr(f, "display_name", f.factor_key) or f.factor_key,
                    "weight": float(getattr(f, "weight", 1.0) or 1.0),
                    "anchor_terms": f.anchor_terms,
                    "context_terms": f.context_terms,
                    "negation_terms": f.negation_terms,
                }
                for f in self.factors
            ],
        }

        llm_ctx_for_api = {
            "category_slug": self.category_slug,
            "dialogue_history": self.dialogue_history,
            "top_factors": [
                {
                    "factor_key": k,
                    "display_name": getattr(self.factors_map.get(k), "display_name", k) if self.factors_map.get(k) else k,
                    "score": float(s),
                }
                for k, s in top_factors
            ],
            "evidence_reviews": [
                {
                    "review_id": e.get("review_id"),
                    "rating": e.get("rating", 0),
                    "excerpt": e.get("excerpt", ""),
                    "reason": e.get("reason", []),
                    "label": e.get("label", "NEU"),
                    "factor": e.get("factor") or e.get("factor_key"),
                    "score": float(e.get("score") or 0.0),
                }
                for e in evidence
            ],
            "safety_rules": safety_rules,
        }

        llm_ctx_for_frontend = {
            **llm_ctx_for_api,
            "calculation_info": calculation_info,
        }

        prompt = self._build_llm_prompt(llm_ctx_for_api)

        # 저장(데모)
        from datetime import datetime
        import json

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path("out")
        out_dir.mkdir(parents=True, exist_ok=True)

        output_file = out_dir / f"llm_context_demo.{timestamp}.json"
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(llm_ctx_for_api, f, ensure_ascii=False, indent=2)

        prompt_file = out_dir / f"prompt_demo.{timestamp}.txt"
        with prompt_file.open("w", encoding="utf-8") as f:
            f.write(prompt)

        return BotTurn(
            question_text=None,
            top_factors=top_factors,
            is_final=True,
            llm_context=llm_ctx_for_frontend,
        )

    def _build_llm_prompt(self, llm_ctx: Dict) -> str:
        # 대화 히스토리 포맷팅
        dialogue_text = ""
        for turn in llm_ctx.get("dialogue_history", []):
            role = "사용자" if turn["role"] == "user" else "상담원"
            dialogue_text += f"{role}: {turn['message']}\n"

        # 상위 요인 포맷팅(표시명 사용)
        factors_lines: List[str] = []
        for idx, factor in enumerate(llm_ctx.get("top_factors", []), 1):
            factor_key = factor["factor_key"]
            score = float(factor.get("score") or 0.0)
            display_name = str(factor.get("display_name") or "").strip()
            if not display_name:
                factor_obj = self.factors_map.get(factor_key)
                display_name = (getattr(factor_obj, "display_name", "") or factor_key) if factor_obj else factor_key
            factors_lines.append(f"{idx}. {display_name} ({factor_key}) (점수: {score:.2f})")
        factors_text = "\n".join(factors_lines)

        # 증거 리뷰 포맷팅(label 포함 + review_id 강조)
        reviews_lines: List[str] = []
        for idx, review in enumerate(llm_ctx.get("evidence_reviews", []), 1):
            rid = review.get("review_id")
            rating = review.get("rating", 0)
            label = review.get("label", "NEU")
            excerpt = (review.get("excerpt") or "").strip()
            fkey = review.get("factor") or review.get("factor_key") or ""
            reviews_lines.append(
                f"[{idx}] review_id={rid} | rating={rating} | label={label} | factor={fkey}\n{excerpt}"
            )
        reviews_text = "\n\n".join(reviews_lines)

        safety_text = "\n".join(f"- {rule}" for rule in llm_ctx.get("safety_rules", []))

        # v2 JSON 출력 스키마(근거 review_id 강제)
        prompt = f"""당신은 리뷰 분석 전문가입니다. 사용자와의 대화 내용을 바탕으로 '후회 요인'을 분석하고, 아래의 리뷰 발췌(excerpt)만을 근거로 답변을 작성하세요.

카테고리: {llm_ctx.get("category_slug", "unknown")}

대화 내용:
{dialogue_text.strip()}

분석된 주요 후회 요인(top3):
{factors_text.strip()}

관련 리뷰 증거(발췌):
{reviews_text.strip()}

응답 지침:
{safety_text}
- 라벨(label)은 참고용 힌트이며, 최종 판단은 excerpt 내용에 근거할 것
- '가짜리뷰' 여부를 단정하지 말 것(의심/가능성 언급은 가능)
- pros/cons/mixed는 반드시 증거 review_id로 연결할 것(evidence_ids)
- 의료/법률 조언 금지

반드시 아래 JSON 포맷으로만 답변하세요(설명 문장 추가 금지).
- evidence_ids에는 위 목록의 review_id를 2~5개 포함하세요.
- factor는 표시명(한국어)으로 쓰고, factor_key도 함께 제공하세요.
- final_recommendation은 "구매" | "보류" | "대안 탐색" 중 하나만 허용.

{{
  "summary": "사용자의 우려를 한 문장으로 요약",
  "key_findings": [
    {{
      "factor_key": "noise_sleep",
      "factor": "수면 중 소음/눈부심",
      "what_users_say": "리뷰에서 반복되는 주장(한 문장)",
      "risk_level": "low|mid|high",
      "evidence_ids": ["...","..."]
    }}
  ],
  "balanced_view": {{
    "pros": [
      {{"point": "긍정 근거(한 문장)", "evidence_ids": ["..."]}}
    ],
    "cons": [
      {{"point": "부정/리스크 근거(한 문장)", "evidence_ids": ["..."]}}
    ],
    "mixed": [
      {{"point": "조건부/케바케 포인트(한 문장)", "evidence_ids": ["..."]}}
    ]
  }},
  "decision_rule": {{
    "if_buy": ["구매해도 되는 조건 2~3개(체크리스트 톤)"],
    "if_hold": ["보류가 나은 조건 2~3개(체크리스트 톤)"]
  }},
  "follow_up_questions": [
    "예/아니오로 답 가능하게 질문 1",
    "예/아니오로 답 가능하게 질문 2"
  ],
  "final_recommendation": "구매|보류|대안 탐색",
  "one_line_tip": "지금 사용자 상황에 딱 맞는 실전 팁 1줄"
}}
"""
        return prompt