#!/usr/bin/env python3
"""Review Scoring: Factor scoring and classification (Domain Layer - Pure Python)"""
from __future__ import annotations

import logging
from typing import Dict, List, Tuple, Any

import pandas as pd

# Import from domain layer
from .normalize import normalize_text as normalize
from ..reg.store import Factor

logger = logging.getLogger("domain.review.scoring")


def score_text_against_factor(norm_text: str, factor: Factor) -> Tuple[float, List[str], bool]:
    """텍스트와 요인 간 점수 계산 (negation은 감점하지 않고 flag로만 처리)

    Returns:
        (score, reasons, has_negation)
    """
    score = 0.0
    reasons: List[str] = []

    anchor_hit = any(term in norm_text for term in factor.anchor_terms)
    if anchor_hit:
        score += 1.0
        reasons.append("anchor")

    context_hit = any(term in norm_text for term in factor.context_terms)
    if context_hit:
        score += 0.3
        reasons.append("context")

    neg_hit = any(term in norm_text for term in factor.negation_terms)
    if neg_hit:
        # ✅ 점수 감점 X, 메타 플래그만
        reasons.append("negation")

    return score, reasons, neg_hit


def _rating_multiplier_series(df: pd.DataFrame) -> pd.Series:
    """평점 기반 가중치(낮은 별점일수록 더 가중) - 벡터화"""
    if "rating" not in df.columns:
        return pd.Series([1.0] * len(df), index=df.index)

    r = pd.to_numeric(df["rating"], errors="coerce").fillna(3.0)
    r = r.clip(lower=1.0, upper=5.0)

    # 기존 로직 유지: 1점=1.8, 2점=1.6, 3점=1.4, 4점=1.2, 5점=1.0
    mult = 1.0 + (5.0 - r).clip(lower=0.0) * 0.2
    return mult.astype(float)


def compute_review_factor_scores(
    df: pd.DataFrame,
    factors: List[Factor],
    compute_top_per_review: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """모든 리뷰에 대해 각 요인별 점수 계산

    Args:
        df: 리뷰 데이터프레임
        factors: Factor 객체 리스트
        compute_top_per_review: 리뷰별 top_factors/top_factor_scores 계산 여부(성능 옵션)

    Returns:
        (scored_df, factor_counts)
    """
    logger.info(f"[Factor 점수 계산 시작] reviews={len(df)}, factors={len(factors)}")
    df = df.copy()
    df["_norm_text"] = df["text"].fillna("").map(normalize)

    rating_mult = _rating_multiplier_series(df)

    factor_counts: Dict[str, int] = {}

    # (선택) negation flag 컬럼들을 만들고 싶다면 여기서
    # df["_neg_flags"] = [[] for _ in range(len(df))]  # 필요 시

    for factor in factors:
        # 컬럼명: factor_id 우선, factor_key는 하위 호환
        col_id = f"score_f{factor.factor_id}"
        col_key = f"score_{factor.factor_key}"
        has_neg_col = f"has_neg_{factor.factor_key}"

        scores: List[float] = []
        neg_flags: List[bool] = []

        # ✅ iloc 반복 제거: norm text Series로 순회
        for norm in df["_norm_text"]:
            s, reasons, has_neg = score_text_against_factor(norm, factor)
            ws = (s * factor.weight)
            scores.append(ws)
            neg_flags.append(has_neg)

        score_series = pd.Series(scores, index=df.index) * rating_mult
        df[col_id] = score_series  # factor_id 기반 컬럼
        df[col_key] = score_series  # 하위 호환을 위한 factor_key 컬럼
        df[has_neg_col] = neg_flags  # ✅ negation은 별도 플래그로 남김

        factor_counts[factor.factor_key] = int((score_series > 0).sum())
    
    logger.info(f"[Factor 점수 계산 완료] factor_counts={sum(factor_counts.values())} 총 매칭")
    logger.debug(f"  - 상위 5 factors: {sorted(factor_counts.items(), key=lambda x: x[1], reverse=True)[:5]}")

    if compute_top_per_review:
        # ⚠️ 성능 이슈가 있으면 옵션으로 끄세요.
        score_cols = [f"score_f{f.factor_id}" for f in factors if f"score_f{f.factor_id}" in df.columns]
        factor_keys = [f.factor_key for f in factors if f"score_f{f.factor_id}" in df.columns]

        top_tags: List[List[str]] = []
        top_scores: List[List[Tuple[str, float]]] = []

        # ✅ iterrows 대신 values 기반 접근(조금 더 빠름)
        values = df[score_cols].values
        for row_vals in values:
            scored = list(zip(factor_keys, [float(v) if v else 0.0 for v in row_vals]))
            scored.sort(key=lambda x: x[1], reverse=True)
            topN = [k for k, v in scored[:3] if v > 0]
            top_tags.append(topN)
            top_scores.append(scored[:3])

        df["top_factors"] = top_tags
        df["top_factor_scores"] = top_scores

    return df, factor_counts


def select_top_factors_from_question(question: str, factors: List[Factor], top_k: int = 3) -> List[Tuple[str, float]]:
    """사용자 질문에서 관련 요인 추출 (MVP: anchor 기준)

    NOTE: context_terms까지 확장하면 훨씬 자연스럽게 factor가 잡힘.
    """
    logger.debug(f"[질문에서 Factor 추출] question={question[:50]}..., top_k={top_k}")
    nq = normalize(question)
    scored: List[Tuple[str, float]] = []

    for factor in factors:
        hit_anchor = any(term in nq for term in factor.anchor_terms)
        hit_context = any(term in nq for term in factor.context_terms)

        # ✅ anchor가 강하고, context는 약하게 보조
        base = 1.0 if hit_anchor else (0.3 if hit_context else 0.0)
        score = base * factor.weight
        scored.append((factor.factor_key, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = [(k, float(s)) for k, s in scored if s > 0][:top_k]

    if not top:
        logger.debug("  - 매칭 실패, weight 상위 factors 사용")
        # fallback: weight 상위
        scored2 = [(f.factor_key, float(f.weight)) for f in factors]
        scored2.sort(key=lambda x: x[1], reverse=True)
        top = scored2[:top_k]
    
    logger.debug(f"  - 결과: {[(k, round(s, 2)) for k, s in top]}")

    return top