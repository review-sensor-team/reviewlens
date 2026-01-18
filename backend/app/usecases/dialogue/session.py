#!/usr/bin/env python3
"""Dialogue engine: 3-5 turn conversation for factor convergence"""
from __future__ import annotations

import json
import logging
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd

from ...adapters.persistence.reg.store import Factor, Question, load_csvs, parse_factors, parse_questions
from ...domain.rules.review.scoring import compute_review_factor_scores
from ...domain.rules.review.normalize import normalize_review, normalize_text
from...domain.rules.review.retrieval import retrieve_evidence_reviews
from ...infra.observability.metrics import (
    dialogue_sessions_total,
    dialogue_turns_total,
    dialogue_completions_total,
    retrieval_duration_seconds,
    scoring_duration_seconds,
    evidence_count,
    llm_calls_total,
    llm_duration_seconds,
    Timer,
)
from ...core.settings import Settings, settings
from backend.llm.llm_factory import get_llm_client

settings = Settings()

logger = logging.getLogger(__name__)


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
    """Jaccard 유사도 계산"""
    if not a or not b:
        return 0.0
    a_set = set(a)
    b_set = set(b)
    intersection = len(a_set & b_set)
    union = len(a_set | b_set)
    return float(intersection) / float(union) if union > 0 else 0.0


# 공통 상수 import
from .constants import CATEGORY_FALLBACK_QUESTIONS, DEFAULT_FALLBACK_QUESTIONS


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
        
        # 모든 factor 파싱 후 현재 카테고리만 필터링
        all_factors = parse_factors(factors_df)
        self.factors = [f for f in all_factors if f.category == self.category]
        
        # factor_id와 factor_key 모두로 인덱싱 (하위 호환성)
        self.factors_map = {f.factor_key: f for f in self.factors}
        self.factors_by_id = {f.factor_id: f for f in self.factors}
        
        # 현재 카테고리의 factor_id 목록
        category_factor_ids = {f.factor_id for f in self.factors}
        
        # Parse questions - 현재 카테고리의 factor_id에 해당하는 질문만 필터링
        all_questions = parse_questions(questions_df)
        self.questions = [q for q in all_questions if q.factor_id in category_factor_ids]
        
        logger.info(f"  - 전체 factors: {len(all_factors)}개 → 카테고리 '{self.category}' 필터링: {len(self.factors)}개")
        logger.info(f"  - 전체 questions: {len(all_questions)}개 → 카테고리 '{self.category}' 필터링: {len(self.questions)}개")

        # category slug 추출(빈 값이면 fallback)
        self.category_slug = category
        for f in self.factors:
            if getattr(f, "category", "").strip():
                self.category_slug = f.category.strip()
                break

    # ----------------------------- public -----------------------------

    def _update_factor_scores(self, user_message: str) -> List[str]:
        """사용자 메시지로 factor 점수 업데이트
        
        Args:
            user_message: 사용자 메시지
            
        Returns:
            매칭된 factor_key 리스트
        """
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
        
        return matched_factors
    
    def _check_stability(self, top_factors: List[Tuple[str, float]]) -> float:
        """수렴 안정성 체크 (Jaccard 유사도)
        
        Args:
            top_factors: 상위 factor 리스트
            
        Returns:
            Jaccard 유사도
        """
        cur_top3 = [k for k, _ in top_factors]
        sim = _jaccard(cur_top3, self.prev_top3) if self.prev_top3 else 0.0
        
        if sim >= settings.DIALOGUE_JACCARD_THRESHOLD:
            self.stability_hits += 1
        else:
            self.stability_hits = 1
        
        self.prev_top3 = cur_top3
        logger.debug(f"  - 안정성: sim={sim:.2f}, hits={self.stability_hits}")
        
        return sim
    
    def _should_provide_analysis(self) -> bool:
        """분석 제공 여부 판단
        
        Returns:
            분석 제공 여부
        """
        should_provide = (self.turn_count >= settings.DIALOGUE_MIN_ANALYSIS_TURNS)
        logger.info(f"  - 분석 체크: should_provide_analysis={should_provide} (turn={self.turn_count}, stability={self.stability_hits})")
        return should_provide
    
    def _generate_next_question(self, selected_factor: Optional[str], top_factors: List[Tuple[str, float]]) -> Tuple[str, Optional[str], Optional[str], Optional[List[str]]]:
        """다음 질문 생성
        
        Args:
            selected_factor: 선택된 factor (있으면 해당 factor의 여러 질문 반환)
            top_factors: 상위 factor 리스트
            
        Returns:
            (question_text, question_id, answer_type, choices)
        """
        if selected_factor:
            question_text, question_id, answer_type, choices = self._pick_multiple_questions(selected_factor, top_factors)
            logger.info(f"  - 선택된 factor '{selected_factor}'의 질문 {len(choices or [])}개 생성")
        else:
            question_text, question_id, answer_type, choices = self._pick_next_question(top_factors)
            logger.info(f"  - 다음 질문: {question_id or 'N/A'} ({answer_type or 'no_choice'})")
            logger.debug(f"    질문 텍스트: {question_text[:50]}...")
        
        return question_text, question_id, answer_type, choices

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

        # 1) 사용자 메시지로 factor 점수 업데이트
        self._update_factor_scores(user_message)

        # 2) 상위 요인 계산 (top3)
        top_factors = self._get_top_factors(top_k=3)
        logger.debug(f"  - 상위 3 factors: {[(k, round(s, 2)) for k, s in top_factors]}")

        # 3) 수렴 안정성 체크
        self._check_stability(top_factors)

        # 4) 분석 준비 여부 체크
        should_provide_analysis = self._should_provide_analysis()

        # 5) 다음 질문 생성
        question_text, question_id, answer_type, choices = self._generate_next_question(selected_factor, top_factors)

        # 히스토리: assistant
        self.dialogue_history.append({"role": "assistant", "message": question_text})

        # 6) 분석이 준비되었으면 LLM 컨텍스트 생성
        llm_context = None
        has_analysis = False
        if should_provide_analysis:
            logger.info(f"[분석 준비 완료] top factors: {[(k, round(s, 2)) for k, s in top_factors]}")
            llm_context = self._generate_analysis(top_factors)
            has_analysis = True

        return BotTurn(
            question_text=question_text,
            top_factors=top_factors,
            is_final=False,
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

    def _determine_focus_factors(self, top_factors: List[Tuple[str, float]]) -> List[str]:
        """집중 수렴 전략에 따라 포커스할 요인 결정
        
        - turn 1~threshold: top2까지 후보
        - turn threshold+1부터: top1에 더 집중
        """
        focus = 2 if self.turn_count <= settings.DIALOGUE_FOCUS_TURNS_THRESHOLD else 1
        focus_factors = [k for k, _ in top_factors[:focus]]
        logger.debug(f"  - focus_factors: {focus_factors} (turn={self.turn_count})")
        return focus_factors

    def _collect_question_candidates(
        self, 
        focus_factors: List[str]
    ) -> List[Tuple[int, str, str, str, Optional[List[str]]]]:
        """포커스 요인에 대한 질문 후보 수집
        
        Returns:
            List of (priority, question_text, question_id, answer_type, choices)
        """
        candidates: List[Tuple[int, str, str, str, Optional[List[str]]]] = []
        
        for factor_key in focus_factors:
            factor_obj = self.factors_map.get(factor_key)
            if not factor_obj:
                logger.debug(f"    - factor_key '{factor_key}' not in factors_map")
                continue
            
            logger.debug(f"    - factor '{factor_key}' (id={factor_obj.factor_id}) 질문 검색 중...")
            
            matched_count = 0
            for question in self.questions:
                if question.factor_id != factor_obj.factor_id:
                    continue
                
                matched_count += 1
                
                if question.question_text in self.asked_questions:
                    logger.debug(f"      - 질문 '{question.question_text[:30]}...' 이미 물어봄")
                    continue

                prio = question.question_id
                choices = None
                if question.choices and question.answer_type in ["single_choice", "multiple_choice"]:
                    choices = [c.strip() for c in question.choices.split("|") if c.strip()]
                
                candidates.append((prio, question.question_text, str(question.question_id), question.answer_type, choices))
                logger.debug(f"      ✓ 후보 추가: q_id={question.question_id}, '{question.question_text[:30]}...'")
            
            logger.debug(f"    - factor '{factor_key}' 매칭 질문: {matched_count}개")
        
        return candidates

    def _select_best_question(
        self, 
        candidates: List[Tuple[int, str, str, str, Optional[List[str]]]]
    ) -> Tuple[str, Optional[str], Optional[str], Optional[List[str]]]:
        """후보 중 최적 질문 선택 (우선순위 기반)
        
        Returns:
            (question_text, question_id, answer_type, choices)
        """
        if not candidates:
            logger.debug(f"  - 후보 질문 없음, fallback 사용 (asked_questions={len(self.asked_questions)}개)")
            return self._fallback_question()
        
        candidates.sort(key=lambda x: x[0])
        _, picked_text, picked_id, picked_type, picked_choices = candidates[0]
        self.asked_questions.add(picked_text)
        logger.debug(f"  - 선택된 질문: q_id={picked_id}, '{picked_text[:30]}...'")
        return picked_text, picked_id, picked_type, picked_choices

    def _pick_next_question(self, top_factors: List[Tuple[str, float]]) -> Tuple[str, Optional[str], Optional[str], Optional[List[str]]]:
        """다음 질문 선택
        
        Returns:
            (question_text, question_id, answer_type, choices)
        """
        if not self.questions:
            logger.debug(f"  - 질문 DB 없음, fallback 사용")
            return self._fallback_question()

        focus_factors = self._determine_focus_factors(top_factors)
        candidates = self._collect_question_candidates(focus_factors)
        return self._select_best_question(candidates)

    def _find_factor_by_name(
        self, 
        selected_factor: str, 
        top_factors: List[Tuple[str, float]]
    ) -> Optional[Any]:
        """selected_factor 문자열로 Factor 객체 찾기
        
        시도 순서:
        1) factor_key로 찾기
        2) display_name으로 찾기
        3) top_factors에서 partial match로 찾기
        """
        # 1) factor_key로 찾기
        factor_obj = self.factors_map.get(selected_factor)
        if factor_obj:
            return factor_obj
        
        # 2) display_name으로 찾기
        for f in self.factors:
            if getattr(f, 'display_name', None) == selected_factor:
                return f
        
        # 3) top_factors에서 찾기 (partial match)
        for factor_key, _ in top_factors:
            if factor_key == selected_factor or selected_factor in factor_key:
                return self.factors_map.get(factor_key)
        
        return None

    def _find_first_unasked_question(
        self, 
        factor_obj: Any
    ) -> Tuple[str, Optional[str], str, Optional[List[str]]]:
        """해당 factor의 첫 번째 미질문 찾기
        
        Returns:
            (question_text, question_id, answer_type, choices)
        """
        for question in self.questions:
            if question.factor_id == factor_obj.factor_id:
                if question.question_text not in self.asked_questions:
                    self.asked_questions.add(question.question_text)
                    
                    choices = None
                    if question.choices and question.answer_type in ["single_choice", "multiple_choice"]:
                        choices = [c.strip() for c in question.choices.split("|") if c.strip()]
                    
                    logger.info(f"  - factor '{factor_obj.factor_key}'의 첫 질문: q_id={question.question_id}, answer_type={question.answer_type}, choices={len(choices) if choices else 0}개")
                    
                    return question.question_text, str(question.question_id), question.answer_type or 'no_choice', choices
        
        logger.warning(f"  - factor '{factor_obj.factor_key}'의 질문이 없음, fallback 사용")
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
        
        factor_obj = self._find_factor_by_name(selected_factor, top_factors)
        if not factor_obj:
            logger.warning(f"  - factor '{selected_factor}' not found, fallback 사용")
            return self._fallback_question()
        
        logger.debug(f"    - factor 찾음: {factor_obj.factor_key} (id={factor_obj.factor_id})")
        return self._find_first_unasked_question(factor_obj)
    
    def _fallback_question(self) -> Tuple[str, Optional[str], Optional[str], Optional[List[str]]]:
        """카테고리별 기본 질문 반환
        
        Returns:
            (question_text, question_id, answer_type, choices)
        """
        # 현재 카테고리의 질문 가져오기
        defaults = CATEGORY_FALLBACK_QUESTIONS.get(self.category, DEFAULT_FALLBACK_QUESTIONS)
        
        # 아직 묻지 않은 질문 찾기
        for q in defaults:
            if q not in self.asked_questions:
                self.asked_questions.add(q)
                return q, None, None, None
        
        # 모든 기본 질문을 다 했으면 마지막 질문
        final_question = "추가로 고려하시는 부분이 있나요?"
        if final_question not in self.asked_questions:
            self.asked_questions.add(final_question)
        return final_question, None, None, None

    def _compute_review_scores(self):
        """리뷰 스코어 계산 (캐싱)"""
        if self.scored_df is None or self.factor_counts is None:
            with Timer(scoring_duration_seconds, {'category': self.category}):
                self.scored_df, self.factor_counts = compute_review_factor_scores(self.reviews_df, self.factors)
    
    def _retrieve_evidence(self, top_factors: List[Tuple[str, float]]) -> List[Dict]:
        """Evidence 리뷰 추출
        
        Args:
            top_factors: 상위 factor 리스트
            
        Returns:
            Evidence 리뷰 리스트
        """
        with Timer(retrieval_duration_seconds, {'category': self.category}):
            evidence = retrieve_evidence_reviews(
                self.scored_df,
                self.factors_map,
                [(k, s) for k, s in top_factors],
                per_factor_limit=(settings.EVIDENCE_PER_FACTOR_MIN, settings.EVIDENCE_PER_FACTOR_MAX),
                max_total_evidence=settings.EVIDENCE_MAX_TOTAL,
                quota_by_rank={
                    0: {"NEG": settings.EVIDENCE_RANK0_NEG, "MIX": settings.EVIDENCE_RANK0_MIX, "POS": settings.EVIDENCE_RANK0_POS},
                    1: {"NEG": settings.EVIDENCE_RANK1_NEG, "MIX": settings.EVIDENCE_RANK1_MIX, "POS": settings.EVIDENCE_RANK1_POS},
                    2: {"NEG": settings.EVIDENCE_RANK2_NEG, "MIX": settings.EVIDENCE_RANK2_MIX, "POS": settings.EVIDENCE_RANK2_POS},
                },
            )
        
        # 메트릭: evidence 수 기록
        total_evidence = len(evidence)
        evidence_count.labels(category=self.category).observe(total_evidence)
        
        return evidence
    
    def _build_calculation_info(self) -> Dict:
        """계산 정보 생성
        
        Returns:
            계산 정보 딕셔너리
        """
        return {
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
    
    def _replace_factor_keys_with_display_names(self, summary_text: str) -> str:
        """LLM 응답 JSON에서 factor_key를 display_name으로 교체
        
        Args:
            summary_text: LLM의 JSON 응답 문자열
            
        Returns:
            factor가 display_name으로 교체된 JSON 문자열
        """
        try:
            import json
            response_json = json.loads(summary_text)
            
            # key_findings의 factor를 display_name으로 교체
            if "key_findings" in response_json and isinstance(response_json["key_findings"], list):
                for finding in response_json["key_findings"]:
                    if "factor_key" in finding:
                        factor_key = finding["factor_key"]
                        factor_obj = self.factors_map.get(factor_key)
                        if factor_obj:
                            display_name = getattr(factor_obj, "display_name", factor_key) or factor_key
                            # factor 필드를 display_name으로 교체
                            finding["factor"] = display_name
            
            return json.dumps(response_json, ensure_ascii=False)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"[factor 교체 실패] {e} - 원본 응답 반환")
            return summary_text

    def _build_frontend_context(self, top_factors: List[Tuple[str, float]], evidence: List[Dict], 
                                 llm_summary: Any, calculation_info: Dict) -> Dict:
        """프론트엔드용 LLM 컨텍스트 구성
        
        Args:
            top_factors: 상위 factor 리스트
            evidence: Evidence 리뷰 리스트
            llm_summary: LLM 요약
                - 단일 전략: tuple[str, str] (요약, 응답 파일명)
                - 다중 전략: List[Dict] (전략별 요약, response_file 포함)
            calculation_info: 계산 정보
            
        Returns:
            프론트엔드용 컨텍스트 딕셔너리
        """
        safety_rules = [
            "가짜리뷰 여부를 단정하지 말 것",
            "근거 리뷰는 짧게 인용할 것",
            "의학/법률 조언 금지",
        ]
        
        context = {
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
        }
        
        # llm_summary가 리스트면 다중 전략, 튜플이면 단일 전략
        if isinstance(llm_summary, list):
            # 다중 전략: llm_summaries 배열로 반환 (각 summary의 factor 교체)
            processed_summaries = []
            for item in llm_summary:
                processed_item = item.copy()
                if "summary" in processed_item:
                    processed_item["summary"] = self._replace_factor_keys_with_display_names(processed_item["summary"])
                processed_summaries.append(processed_item)
            
            context["llm_summaries"] = processed_summaries
            context["llm_summary"] = processed_summaries[0]["summary"] if processed_summaries else ""  # 호환성
        elif isinstance(llm_summary, tuple):
            # 단일 전략: (요약, 파일명) 튜플 - factor 교체
            summary_text, response_file = llm_summary
            processed_summary = self._replace_factor_keys_with_display_names(summary_text)
            context["llm_summary"] = processed_summary
            context["response_file"] = response_file
        else:
            # 호환성 유지 (str만 전달된 경우) - factor 교체
            context["llm_summary"] = self._replace_factor_keys_with_display_names(llm_summary)
        
        return context

    def _generate_analysis(self, top_factors: List[Tuple[str, float]]) -> Dict:
        """분석 결과 생성 (대화 종료 없이)"""
        logger.info(f"[분석 생성] turn={self.turn_count}, top_factors={len(top_factors)}")
        
        # 1) 리뷰 스코어 계산
        self._compute_review_scores()

        # 2) Evidence 추출
        evidence = self._retrieve_evidence(top_factors)

        # 3) LLM 요약 생성
        llm_summary = self._generate_llm_summary(top_factors, evidence)

        # 4) 계산 정보 구성
        calculation_info = self._build_calculation_info()

        # 5) 프론트엔드용 컨텍스트 반환
        return self._build_frontend_context(top_factors, evidence, llm_summary, calculation_info)

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

    def _format_dialogue_history(self, dialogue_history: List[Dict]) -> str:
        """대화 히스토리를 텍스트로 포맷팅"""
        dialogue_text = ""
        for turn in dialogue_history:
            role = "사용자" if turn["role"] == "user" else "상담원"
            dialogue_text += f"{role}: {turn['message']}\n"
        return dialogue_text

    def _format_top_factors(self, top_factors: List[Dict]) -> str:
        """상위 요인을 번호가 매겨진 리스트로 포맷팅 (표시명 사용)"""
        factors_lines: List[str] = []
        for idx, factor in enumerate(top_factors, 1):
            factor_key = factor["factor_key"]
            score = float(factor.get("score") or 0.0)
            display_name = str(factor.get("display_name") or "").strip()
            if not display_name:
                factor_obj = self.factors_map.get(factor_key)
                display_name = (getattr(factor_obj, "display_name", "") or factor_key) if factor_obj else factor_key
            factors_lines.append(f"{idx}. {display_name} ({factor_key}) (점수: {score:.2f})")
        return "\n".join(factors_lines)

    def _format_evidence_reviews(self, evidence_reviews: List[Dict]) -> str:
        """증거 리뷰를 포맷팅 (label 포함 + review_id 강조)"""
        reviews_lines: List[str] = []
        for idx, review in enumerate(evidence_reviews, 1):
            rid = review.get("review_id")
            rating = review.get("rating", 0)
            label = review.get("label", "NEU")
            excerpt = (review.get("excerpt") or "").strip()
            fkey = review.get("factor") or review.get("factor_key") or ""
            reviews_lines.append(
                f"[{idx}] review_id={rid} | rating={rating} | label={label} | factor={fkey}\n{excerpt}"
            )
        return "\n\n".join(reviews_lines)

    def _format_safety_rules(self, safety_rules: List[str]) -> str:
        """안전 규칙을 불릿 포인트로 포맷팅"""
        return "\n".join(f"- {rule}" for rule in safety_rules)

    def _build_llm_prompt(self, llm_ctx: Dict) -> str:
        """LLM 프롬프트 생성 (v2 JSON 출력 스키마)"""
        dialogue_text = self._format_dialogue_history(llm_ctx.get("dialogue_history", []))
        factors_text = self._format_top_factors(llm_ctx.get("top_factors", []))
        reviews_text = self._format_evidence_reviews(llm_ctx.get("evidence_reviews", []))
        safety_text = self._format_safety_rules(llm_ctx.get("safety_rules", []))

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
    ) -> Any:
        """LLM을 사용하여 최종 분석 요약 생성
        
        Returns:
            단일 전략: str (요약 텍스트)
            다중 전략: List[Dict] (전략별 요약)
        """
        try:
            llm_context = self._prepare_llm_context(top_factors, evidence_reviews)
            self._save_llm_context(llm_context)
            return self._call_llm_generate_summary(llm_context, top_factors, evidence_reviews)
        except Exception as e:
            return self._fallback_summary(top_factors, e)

    def _get_category_display_name(self) -> str:
        """카테고리 슬러그를 한국어 표시명으로 변환"""
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
        return category_names.get(self.category, self.category)

    def _prepare_llm_context(
        self, 
        top_factors: List[Tuple[str, float]], 
        evidence_reviews: List[Dict]
    ) -> Dict:
        """LLM 호출을 위한 컨텍스트 딕셔너리 준비"""
        from datetime import datetime
        
        category_name = self._get_category_display_name()
        product_name = getattr(self, 'product_name', "이 제품")
        
        return {
            "top_factors": top_factors,
            "evidence_reviews": evidence_reviews,
            "total_turns": self.turn_count,
            "category_name": category_name,
            "product_name": product_name,
            "timestamp": datetime.now().isoformat()
        }

    def _save_llm_context(self, llm_context: Dict) -> None:
        """LLM 컨텍스트를 JSON 파일로 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path("out")
        out_dir.mkdir(exist_ok=True)
        
        context_file = out_dir / f"llm_context_{timestamp}.json"
        with open(context_file, "w", encoding="utf-8") as f:
            json.dump(llm_context, f, ensure_ascii=False, indent=2)
        logger.info(f"[LLM 컨텍스트 저장] {context_file}")

    def _call_llm_generate_summary(
        self, 
        llm_context: Dict,
        top_factors: List[Tuple[str, float]], 
        evidence_reviews: List[Dict]
    ) -> Any:
        """LLM 클라이언트를 호출하여 요약 생성 (메트릭 기록 포함)
        
        Returns:
            단일 전략: tuple[str, str] (요약 텍스트, 응답 파일명)
            다중 전략: List[Dict] (전략별 요약, response_file 포함)
        """
        llm_client = get_llm_client()
        provider = settings.LLM_PROVIDER
        
        # 설정에서 전략 목록 가져오기
        strategies = settings.get_prompt_strategies()
        
        # 단일 전략
        if len(strategies) == 1:
            logger.info(f"[LLM] 단일 전략 '{strategies[0]}' 사용")
            
            with Timer(llm_duration_seconds, {'provider': provider}):
                summary, response_file = llm_client.generate_summary(
                    top_factors=top_factors,
                    evidence_reviews=evidence_reviews,
                    total_turns=self.turn_count,
                    category_name=llm_context["category_name"],
                    product_name=llm_context["product_name"],
                    dialogue_history=self.dialogue_history
                )
            
            llm_calls_total.labels(provider=provider, status='success').inc()
            logger.info(f"[LLM 요약 생성 완료] {len(summary)}자, 파일={response_file}")
            return summary, response_file
        
        # 다중 전략
        else:
            logger.info(f"[LLM] 다중 전략 {strategies} 사용 ({len(strategies)}개)")
            
            with Timer(llm_duration_seconds, {'provider': provider}):
                summaries = llm_client.generate_summaries_with_strategies(
                    strategies=strategies,
                    top_factors=top_factors,
                    evidence_reviews=evidence_reviews,
                    total_turns=self.turn_count,
                    category_name=llm_context["category_name"],
                    product_name=llm_context["product_name"],
                    dialogue_history=self.dialogue_history
                )
            
            llm_calls_total.labels(provider=provider, status='success').inc()
            logger.info(f"[LLM 다중 요약 생성 완료] {len(summaries)}개 전략")
            return summaries

    def _fallback_summary(
        self, 
        top_factors: List[Tuple[str, float]], 
        error: Exception
    ) -> str:
        """LLM 호출 실패 시 폴백 요약 메시지 생성"""
        logger.error(f"[LLM 요약 생성 실패] {error}", exc_info=True)
        logger.error(f"[스택트레이스]\n{traceback.format_exc()}")
        
        # 메트릭: LLM 호출 에러
        try:
            provider = settings.LLM_PROVIDER
        except:
            provider = 'unknown'
        
        llm_calls_total.labels(provider=provider, status='error').inc()
        llm_calls_total.labels(provider=provider, status='fallback').inc()
        
        factors_text = ", ".join([key for key, _ in top_factors[:3]])
        return f"주요 후회 요인: {factors_text}. 구매 전 이 요인들을 꼭 확인하세요."