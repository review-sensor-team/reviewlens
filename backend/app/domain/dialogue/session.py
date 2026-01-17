#!/usr/bin/env python3
"""Dialogue engine: 3-5 turn conversation for factor convergence"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd

from ..reg.store import Factor, Question, load_csvs, parse_factors, parse_questions
from ..review.scoring import compute_review_factor_scores
from ..review.normalize import normalize_review, normalize_text
from ..review.retrieval import retrieve_evidence_reviews
from ...infra.observability.metrics import (
    dialogue_sessions_total,
    dialogue_turns_total,
    dialogue_completions_total,
    retrieval_duration_seconds,
    scoring_duration_seconds,
    evidence_count,
    Timer,
)
from ...core.settings import Settings

settings = Settings()

logger = logging.getLogger("pipeline.dialogue")


@dataclass
class BotTurn:
    """챗봇 턴 결과"""
    question_text: Optional[str]
    top_factors: List[Tuple[str, float]]
    is_final: bool  # 사용자가 명시적으로 대화 종료를 요청했을 때만 True
    llm_context: Optional[Dict] = None  # 수렴 달성 시 분석 결과 제공 (대화는 계속 가능)
    has_analysis: bool = False  # 분석 결과가 포함되어 있는지 여부
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

    def __init__(self, category: str, data_dir: str | Path, reviews_df: Optional[pd.DataFrame] = None, product_name: Optional[str] = None):
        self.category = category
        self.data_dir = Path(data_dir)
        self.product_name = product_name or "이 제품"  # 제품명 저장

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
        
        # 메트릭: 세션 시작 카운트
        dialogue_sessions_total.labels(category=category).inc()

        # Load data
        logger.info(f"[DialogueSession 초기화] category={category}, data_dir={data_dir}, custom_reviews={reviews_df is not None}, product_name={product_name}")
        
        if reviews_df is not None:
            # 외부에서 제공한 리뷰 사용 (세션별 수집 리뷰)
            self.reviews_df = reviews_df
            _, factors_df, questions_df = load_csvs(self.data_dir)
            logger.debug(f"  - reviews: {len(self.reviews_df)}건 (세션 데이터), factors: {len(factors_df)}건, questions: {len(questions_df)}건")
        else:
            # CSV에서 로드 (기본 동작, 테스트용)
            self.reviews_df, factors_df, questions_df = load_csvs(self.data_dir)
            logger.debug(f"  - reviews: {len(self.reviews_df)}건 (CSV), factors: {len(factors_df)}건, questions: {len(questions_df)}건")
        
        # Parse questions
        self.questions = parse_questions(questions_df)
        
        # 모든 factor 파싱 후 현재 카테고리만 필터링
        all_factors = parse_factors(factors_df)
        self.factors = [f for f in all_factors if f.category == self.category]
        
        # factor_id와 factor_key 모두로 인덱싱 (하위 호환성)
        self.factors_map = {f.factor_key: f for f in self.factors}
        self.factors_by_id = {f.factor_id: f for f in self.factors}
        logger.info(f"  - 전체 factors: {len(all_factors)}개 → 카테고리 '{self.category}' 필터링: {len(self.factors)}개")
        logger.info(f"  - 전체 questions: {len(self.questions)}개")

        # category slug 추출(빈 값이면 fallback)
        self.category_slug = category
        for f in self.factors:
            if getattr(f, "category", "").strip():
                self.category_slug = f.category.strip()
                break

    # ----------------------------- public -----------------------------

    def step(self, user_message: str, selected_factor: Optional[str] = None) -> BotTurn:
        """사용자 메시지 처리 및 다음 질문 생성
        
        Args:
            user_message: 사용자 메시지
            selected_factor: 선택된 후회 포인트 (display_name 또는 factor_key)
        """
        self.turn_count += 1
        logger.info(f"[턴 {self.turn_count}] 사용자 메시지: {user_message[:50]}..., selected_factor={selected_factor}")
        
        # 메트릭: 대화 턴 카운트
        dialogue_turns_total.labels(category=self.category).inc()

        # 히스토리: user
        self.dialogue_history.append({"role": "user", "message": user_message})

        # 1) 사용자 메시지로 factor 점수 누적(negation 감점 X)
        norm = normalize_text(user_message)
        logger.debug(f"  - 정규화된 메시지: {norm}")
        matched_factors = []
        for f in self.factors:
            base = 0.0
            if any(t in norm for t in f.anchor_terms):
                base += 1.0
                logger.debug(f"    - {f.factor_key}: anchor_terms 매칭")
            if any(t in norm for t in f.context_terms):
                base += 0.3
                logger.debug(f"    - {f.factor_key}: context_terms 매칭")

            ws = base * float(getattr(f, "weight", 1.0) or 1.0)
            if ws > 0:
                self.cumulative_scores[f.factor_key] = self.cumulative_scores.get(f.factor_key, 0.0) + ws
                matched_factors.append(f.factor_key)
        
        if matched_factors:
            logger.debug(f"  - 매칭된 factors: {matched_factors}")

        # 2) 상위 요인 계산(top3)
        top_factors = self._get_top_factors(top_k=3)
        logger.debug(f"  - 상위 3 factors: {[(k, round(s, 2)) for k, s in top_factors]}")

        # 3) 수렴(안정성) 체크: top3 Jaccard
        cur_top3 = [k for k, _ in top_factors]
        sim = _jaccard(cur_top3, self.prev_top3) if self.prev_top3 else 0.0
        from backend.app.core.settings import settings
        if sim >= settings.DIALOGUE_JACCARD_THRESHOLD:  # 3개 중 2개 이상 같으면 안정
            self.stability_hits += 1
        else:
            self.stability_hits = 1
        self.prev_top3 = cur_top3
        logger.debug(f"  - 안정성: sim={sim:.2f}, hits={self.stability_hits}")

        # 4) 분석 준비 여부 체크
        # - 최소 턴 이상이면 분석 결과 제공 (안정성 조건 제거)
        # - 분석 제공 후에도 대화는 계속 가능
        should_provide_analysis = (self.turn_count >= settings.DIALOGUE_MIN_ANALYSIS_TURNS)
        logger.info(f"  - 분석 체크: should_provide_analysis={should_provide_analysis} (turn={self.turn_count}, stability={self.stability_hits})")

        # 5) 다음 질문 생성
        # - selected_factor가 있으면 해당 factor의 여러 질문을 choices로 반환
        # - 없으면 일반 질문 1개 생성
        if selected_factor:
            question_text, question_id, answer_type, choices = self._pick_multiple_questions(selected_factor, top_factors)
            logger.info(f"  - 선택된 factor '{selected_factor}'의 질문 {len(choices or [])}개 생성")
        else:
            question_text, question_id, answer_type, choices = self._pick_next_question(top_factors)
            logger.info(f"  - 다음 질문: {question_id or 'N/A'} ({answer_type or 'no_choice'})")
            logger.debug(f"    질문 텍스트: {question_text[:50]}...")

        # 히스토리: assistant
        self.dialogue_history.append({"role": "assistant", "message": question_text})

        # 6) 분석이 준비되었으면 LLM 컨텍스트 생성 (대화는 계속)
        llm_context = None
        has_analysis = False
        if should_provide_analysis:
            logger.info(f"[분석 준비 완료] top factors: {[(k, round(s, 2)) for k, s in top_factors]}")
            llm_context = self._generate_analysis(top_factors)
            has_analysis = True

        return BotTurn(
            question_text=question_text,
            top_factors=top_factors,
            is_final=False,  # 대화는 계속 가능
            llm_context=llm_context,
            has_analysis=has_analysis,
            question_id=question_id,
            answer_type=answer_type,
            choices=choices
        )

    def finalize_now(self) -> BotTurn:
        """사용자 요청으로 즉시 분석 종료"""
        logger.info(f"[사용자 요청 종료] turn={self.turn_count}")
        top_factors = self._get_top_factors(top_k=3)
        return self._finalize(top_factors)

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

    def _pick_next_question(self, top_factors: List[Tuple[str, float]]) -> Tuple[str, Optional[str], Optional[str], Optional[List[str]]]:
        """다음 질문 선택
        
        Returns:
            (question_text, question_id, answer_type, choices)
        """
        # 질문 리스트가 없으면 기본 질문
        if not self.questions:
            logger.debug(f"  - 질문 DB 없음, fallback 사용")
            return self._fallback_question()

        # "집중 수렴" 전략:
        # - turn 1~threshold: top2까지 후보
        # - turn threshold+1부터: top1에 더 집중
        focus = 2 if self.turn_count <= settings.DIALOGUE_FOCUS_TURNS_THRESHOLD else 1
        focus_factors = [k for k, _ in top_factors[:focus]]
        logger.debug(f"  - focus_factors: {focus_factors} (turn={self.turn_count})")

        candidates: List[Tuple[int, str, str, str, Optional[List[str]]]] = []  # (prio, q_text, q_id, answer_type, choices)
        for factor_key in focus_factors:
            # factor_key로 Factor 객체 찾기
            factor_obj = self.factors_map.get(factor_key)
            if not factor_obj:
                logger.debug(f"    - factor_key '{factor_key}' not in factors_map")
                continue
            
            logger.debug(f"    - factor '{factor_key}' (id={factor_obj.factor_id}) 질문 검색 중...")
            
            # factor_id로 매칭되는 질문들 찾기
            matched_count = 0
            for question in self.questions:
                # factor_id로 매칭
                if question.factor_id != factor_obj.factor_id:
                    # 부분일치(예: noise_sleep vs noise) - factor_key 기반
                    prefix = factor_key.split("_")[0]
                    if not question.factor_key.startswith(prefix):
                        continue
                
                matched_count += 1
                
                # 이미 물어본 질문은 제외
                if question.question_text in self.asked_questions:
                    logger.debug(f"      - 질문 '{question.question_text[:30]}...' 이미 물어봄")
                    continue

                # question_id를 우선순위로 사용 (낮은 숫자가 우선)
                prio = question.question_id
                
                # choices 파싱
                choices = None
                if question.choices and question.answer_type in ["single_choice", "multiple_choice"]:
                    choices = [c.strip() for c in question.choices.split("|") if c.strip()]
                
                candidates.append((prio, question.question_text, str(question.question_id), question.answer_type, choices))
                logger.debug(f"      ✓ 후보 추가: q_id={question.question_id}, '{question.question_text[:30]}...'")
            
            logger.debug(f"    - factor '{factor_key}' 매칭 질문: {matched_count}개")

        # 우선순위 낮은 숫자 먼저
        candidates.sort(key=lambda x: x[0])

        if candidates:
            _, picked_text, picked_id, picked_type, picked_choices = candidates[0]
            self.asked_questions.add(picked_text)
            logger.debug(f"  - 선택된 질문: q_id={picked_id}, '{picked_text[:30]}...'")
            return picked_text, picked_id, picked_type, picked_choices

        logger.debug(f"  - 후보 질문 없음, fallback 사용 (asked_questions={len(self.asked_questions)}개)")
        return self._fallback_question()

    def _pick_multiple_questions(self, selected_factor: str, top_factors: List[Tuple[str, float]]) -> Tuple[str, Optional[str], str, Optional[List[str]]]:
        """선택된 factor에 대한 첫 번째 질문을 반환 (choices 포함)
        
        Args:
            selected_factor: 선택된 factor (display_name 또는 factor_key)
            top_factors: 상위 factors 리스트
        
        Returns:
            (question_text, question_id, answer_type, choices)
        """
        logger.debug(f"  - selected_factor '{selected_factor}'의 질문들 검색 중...")
        
        # selected_factor에 해당하는 Factor 객체 찾기
        factor_obj = None
        
        # 1) factor_key로 찾기
        factor_obj = self.factors_map.get(selected_factor)
        
        # 2) display_name으로 찾기
        if not factor_obj:
            for f in self.factors:
                if getattr(f, 'display_name', None) == selected_factor:
                    factor_obj = f
                    break
        
        # 3) top_factors에서 찾기 (partial match)
        if not factor_obj:
            for factor_key, _ in top_factors:
                if factor_key == selected_factor or selected_factor in factor_key:
                    factor_obj = self.factors_map.get(factor_key)
                    break
        
        if not factor_obj:
            logger.warning(f"  - factor '{selected_factor}' not found, fallback 사용")
            return self._fallback_question()
        
        logger.debug(f"    - factor 찾음: {factor_obj.factor_key} (id={factor_obj.factor_id})")
        
        # 해당 factor의 첫 번째 질문 찾기
        for question in self.questions:
            # factor_id로 매칭
            if question.factor_id == factor_obj.factor_id:
                # 이미 물어본 질문 제외
                if question.question_text not in self.asked_questions:
                    self.asked_questions.add(question.question_text)
                    
                    # choices 파싱
                    choices = None
                    if question.choices and question.answer_type in ["single_choice", "multiple_choice"]:
                        choices = [c.strip() for c in question.choices.split("|") if c.strip()]
                    
                    logger.info(f"  - factor '{factor_obj.factor_key}'의 첫 질문: q_id={question.question_id}, answer_type={question.answer_type}, choices={len(choices) if choices else 0}개")
                    
                    # 질문 + choices 반환
                    return question.question_text, str(question.question_id), question.answer_type or 'no_choice', choices
        
        logger.warning(f"  - factor '{factor_obj.factor_key}'의 질문이 없음, fallback 사용")
        return self._fallback_question()
    
    def _fallback_question(self) -> Tuple[str, Optional[str], Optional[str], Optional[List[str]]]:
        """카테고리별 기본 질문 반환
        
        Returns:
            (question_text, question_id, answer_type, choices)
        """
        # 카테고리별 맞춤 질문
        category_questions = {
            'mattress': [
                "평소 어떤 자세로 주로 주무시나요? (옆으로/바로/엎드려)",
                "현재 사용 중인 매트리스에서 가장 불편한 점이 무엇인가요?",
                "매트리스 구매 시 가장 중요하게 생각하는 요소는 무엇인가요? (지지력/푹신함/통풍/내구성 등)"
            ],
            'chair': [
                "하루에 몇 시간 정도 앉아서 작업하시나요?",
                "현재 의자에서 가장 불편한 부위는 어디인가요? (허리/목/엉덩이/팔걸이 등)",
                "의자 구매 시 가장 중요하게 생각하는 요소는 무엇인가요? (쿠션/등받이/높이조절/내구성 등)"
            ],
            'bedding_cleaner': [
                "주로 어떤 종류의 침구류를 청소하실 예정인가요? (이불/베개/매트리스 등)",
                "알레르기나 천식이 있으신가요?",
                "청소 주기는 얼마나 자주 하실 계획인가요?"
            ],
            'bedding_robot': [
                "침대 주변 환경은 어떤가요? (공간 여유/장애물 등)",
                "소음에 민감하신 편인가요?",
                "청소 자동화에서 가장 중요하게 생각하는 요소는 무엇인가요? (흡입력/배터리/소음 등)"
            ],
            'bookshelf': [
                "어느 위치에 설치 예정이신가요? (거실/방/서재 등)",
                "주로 어떤 물건을 보관하실 예정인가요? (책/소품/서류 등)",
                "책장 구매 시 가장 중요한 요소는 무엇인가요? (수납력/디자인/안정성/조립 편의성 등)"
            ],
            'coffee_machine': [
                "하루에 커피를 몇 잔 정도 드시나요?",
                "어떤 종류의 커피를 선호하시나요? (에스프레소/아메리카노/라떼 등)",
                "커피머신 구매 시 가장 중요한 요소는 무엇인가요? (맛/편의성/세척/소음 등)"
            ],
            'desk': [
                "주로 어떤 작업을 하실 예정인가요? (컴퓨터 작업/공부/그림 등)",
                "책상을 놓을 공간의 크기는 어느 정도인가요?",
                "책상 구매 시 가장 중요한 요소는 무엇인가요? (크기/수납/높이조절/내구성 등)"
            ],
            'earbuds': [
                "주로 어떤 상황에서 사용하실 예정인가요? (출퇴근/운동/업무 등)",
                "귀 모양이 특이하거나 이어폰이 잘 빠지는 편인가요?",
                "이어폰 구매 시 가장 중요한 요소는 무엇인가요? (음질/착용감/배터리/노이즈캔슬링 등)"
            ],
            'humidifier': [
                "사용하실 공간의 크기는 어느 정도인가요?",
                "소음에 민감하신 편인가요? (수면 중 사용 여부)",
                "가습기 구매 시 가장 중요한 요소는 무엇인가요? (가습량/소음/세척편의성/디자인 등)"
            ],
            'induction': [
                "주로 어떤 요리를 하시나요? (볶음/찌개/구이 등)",
                "인덕션 사용 경험이 있으신가요?",
                "인덕션 구매 시 가장 중요한 요소는 무엇인가요? (화력/소음/세척/안전성 등)"
            ]
        }
        
        # 현재 카테고리의 질문 가져오기
        defaults = category_questions.get(self.category, [
            "이 제품을 주로 어떤 상황에서 사용하실 예정인가요?",
            "비슷한 제품을 사용하면서 불편했던 점이 있다면 무엇인가요?",
            "제품 구매 시 가장 중요하게 생각하는 요소는 무엇인가요?"
        ])
        
        for q in defaults:
            if q not in self.asked_questions:
                self.asked_questions.add(q)
                return q, None, None, None
        
        # 모든 기본 질문을 다 했으면, 마지막 질문 반환 (반복 방지)
        final_question = "추가로 고려하시는 부분이 있나요?"
        if final_question not in self.asked_questions:
            self.asked_questions.add(final_question)
        return final_question, None, None, None

    def _generate_analysis(self, top_factors: List[Tuple[str, float]]) -> Dict:
        """분석 결과 생성 (대화 종료 없이)"""
        logger.info(f"[분석 생성] turn={self.turn_count}, top_factors={len(top_factors)}")
        
        # 1) 리뷰 스코어 계산(캐싱)
        if self.scored_df is None or self.factor_counts is None:
            with Timer(scoring_duration_seconds, {'category': self.category}):
                self.scored_df, self.factor_counts = compute_review_factor_scores(self.reviews_df, self.factors)

        # 2) evidence 추출
        from backend.app.core.settings import settings as app_settings
        with Timer(retrieval_duration_seconds, {'category': self.category}):
            evidence = retrieve_evidence_reviews(
                self.scored_df,
                self.factors_map,
                [(k, s) for k, s in top_factors],
                per_factor_limit=(app_settings.EVIDENCE_PER_FACTOR_MIN, app_settings.EVIDENCE_PER_FACTOR_MAX),
                max_total_evidence=app_settings.EVIDENCE_MAX_TOTAL,
                quota_by_rank={
                    0: {"NEG": app_settings.EVIDENCE_RANK0_NEG, "MIX": app_settings.EVIDENCE_RANK0_MIX, "POS": app_settings.EVIDENCE_RANK0_POS},
                    1: {"NEG": app_settings.EVIDENCE_RANK1_NEG, "MIX": app_settings.EVIDENCE_RANK1_MIX, "POS": app_settings.EVIDENCE_RANK1_POS},
                    2: {"NEG": app_settings.EVIDENCE_RANK2_NEG, "MIX": app_settings.EVIDENCE_RANK2_MIX, "POS": app_settings.EVIDENCE_RANK2_POS},
                },
            )
        
        # 메트릭: evidence 수 기록
        total_evidence = len(evidence)
        evidence_count.labels(category=self.category).observe(total_evidence)

        # 3) LLM 최종 요약 생성
        llm_summary = self._generate_llm_summary(top_factors, evidence)

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

        llm_ctx_for_frontend = {
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
            "calculation_info": calculation_info,
            "llm_summary": llm_summary,
        }

        return llm_ctx_for_frontend

    def finalize_now(self) -> BotTurn:
        """사용자 요청으로 명시적 대화 종료"""
        logger.info(f"[사용자 명시적 종료] turn={self.turn_count}")
        dialogue_completions_total.labels(category=self.category).inc()
        
        top_factors = self._get_top_factors(top_k=3)
        llm_context = self._generate_analysis(top_factors)
        
        return BotTurn(
            question_text=None,
            top_factors=top_factors,
            is_final=True,  # 명시적 종료만 True
            llm_context=llm_context,
            has_analysis=True,
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
    
    def _generate_llm_summary(
        self, 
        top_factors: List[Tuple[str, float]], 
        evidence_reviews: List[Dict]
    ) -> str:
        """LLM을 사용하여 최종 분석 요약 생성"""
        try:
            from backend.llm.llm_factory import get_llm_client
            from ...infra.observability.metrics import llm_calls_total, llm_duration_seconds, Timer
            from ...core.settings import settings
            import json
            from datetime import datetime
            from pathlib import Path
            
            # 카테고리 이름 가져오기
            category_names = {
                "electronics_coffee_machine": "커피머신",
                "robot_cleaner": "로봇청소기",
                "appliance_induction": "인덕션",
                "appliance_bedding_cleaner": "침구청소기",
                "humidifier": "가습기",
                "appliance_heated_humidifier": "가열식 가습기",
                "furniture_bookshelf": "책장",
                "furniture_chair": "의자",
                "furniture_desk": "책상",
                "furniture_mattress": "매트리스",
                "applestore_electronics_earphone": "이어폰",
            }
            category_name = category_names.get(self.category, self.category)
            
            # 제품명 (세션에 저장되어 있다면 가져오기, 없으면 기본값)
            product_name = getattr(self, 'product_name', "이 제품")
            
            # LLM 컨텍스트 준비
            llm_context = {
                "top_factors": top_factors,
                "evidence_reviews": evidence_reviews,
                "total_turns": self.turn_count,
                "category_name": category_name,
                "product_name": product_name,
                "timestamp": datetime.now().isoformat()
            }
            
            # 타임스탬프 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # out 디렉토리 생성
            out_dir = Path("out")
            out_dir.mkdir(exist_ok=True)
            
            # LLM 컨텍스트 저장
            context_file = out_dir / f"llm_context_{timestamp}.json"
            with open(context_file, "w", encoding="utf-8") as f:
                json.dump(llm_context, f, ensure_ascii=False, indent=2)
            logger.info(f"[LLM 컨텍스트 저장] {context_file}")
            
            llm_client = get_llm_client()
            provider = settings.LLM_PROVIDER
            
            # LLM 호출 시간 측정
            with Timer(llm_duration_seconds, {'provider': provider}):
                summary = llm_client.generate_summary(
                    top_factors=top_factors,
                    evidence_reviews=evidence_reviews,
                    total_turns=self.turn_count,
                    category_name=category_name,
                    product_name=product_name,
                    dialogue_history=self.dialogue_history
                )
            
            # 메트릭: LLM 호출 성공
            llm_calls_total.labels(provider=provider, status='success').inc()
            
            logger.info(f"[LLM 요약 생성 완료] {len(summary)}자")
            return summary
            
        except Exception as e:
            logger.error(f"[LLM 요약 생성 실패] {e}", exc_info=True)
            import traceback
            logger.error(f"[스택트레이스]\n{traceback.format_exc()}")
            
            # 메트릭: LLM 호출 에러 (provider 정보 시도)
            try:
                from ..app.core.settings import settings
                provider = settings.LLM_PROVIDER
            except:
                provider = 'unknown'
            llm_calls_total.labels(provider=provider, status='error').inc()
            
            # 폴백: 간단한 기본 메시지
            llm_calls_total.labels(provider=provider, status='fallback').inc()
            factors_text = ", ".join([key for key, _ in top_factors[:3]])
            return f"주요 후회 요인: {factors_text}. 구매 전 이 요인들을 꼭 확인하세요."