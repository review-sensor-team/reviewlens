#!/usr/bin/env python3
"""Evidence retrieval: Extract relevant review excerpts (Domain Layer - Pure Python)"""
from __future__ import annotations

import logging
import math
import re
from typing import Dict, List, Tuple, Any, Optional

import pandas as pd

# Import from domain layer
from .normalize import normalize_text as normalize
from ..reg.store import Factor

logger = logging.getLogger(__name__)


_SENT_SPLIT_RE = re.compile(r"(?<=[\.!?。！？])\s+|\n+")


def _safe_float(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        f = float(v)
        if isinstance(f, float) and math.isnan(f):
            return default
        return f
    except Exception:
        return default


def _safe_int(v: Any, default: int = 0) -> int:
    if v is None:
        return default
    try:
        return int(float(v))  # "5.0" 대응
    except Exception:
        return default


def extract_relevant_sentences(full_text: str, factor_obj: Factor, max_len: int = 160) -> str:
    """factor(anchor/context)에 걸리는 문장만 뽑아 발췌."""
    if not full_text:
        return ""

    sents = _SENT_SPLIT_RE.split(full_text)
    selected: List[str] = []

    for s_raw in sents:
        s_raw = (s_raw or "").strip()
        if not s_raw:
            continue
        s_norm = normalize(s_raw)

        if any(t in s_norm for t in factor_obj.anchor_terms) or any(t in s_norm for t in factor_obj.context_terms):
            selected.append(s_raw)

    if selected:
        joined = " ".join(selected)
        return joined[:max_len]

    # fallback: 첫 문장 or 원문 일부
    for s_raw in sents:
        s_raw = (s_raw or "").strip()
        if s_raw:
            return s_raw[:max_len]

    return full_text[:max_len]


# ------------------------- Labeling helpers -------------------------

_POS_CUES = [
    "괜찮", "좋", "만족", "추천", "문제없", "이상없", "잘됨", "잘되",
    "조용", "무소음", "안시끄", "소음없", "냄새없", "연기없", "불편없", "안불편",
    "간편", "편하", "쉬움", "빠르", "튼튼", "견고", "안전", "깨끗",
]
_NEG_CUES = [
    "불만", "별로", "실망", "후회", "비추", "문제", "고장", "as", "a/s", "환불",
    "시끄", "소음", "냄새", "연기", "뜨거", "화상", "위험", "누수", "샘", "물샘",
    "번거", "귀찮", "청소", "관리", "곰팡", "세척", "부식", "녹", "때",
    "약함", "부족", "미흡", "안됨", "안되", "끊김", "오류",
]
_SWITCH_CUES = ["근데", "하지만", "다만", "그러나", "반면", "대신", "오히려", "그런데"]


def _find_any(hay: str, needles: List[str]) -> bool:
    return any(n in hay for n in needles)


def classify_text_label(full_text: str, factor_obj: Factor, window: int = 30) -> str:
    """
    factor 관련 텍스트에서 POS/NEG/MIX/NEU 라벨 추정.
    - anchor/context 매칭 지점을 중심으로 주변 문맥(window chars)만 평가
    - negation_terms는 감점이 아니라 '우려 해소' 힌트로 활용
    """
    if not full_text:
        return "NEU"

    nt = normalize(full_text)

    terms = factor_obj.anchor_terms or factor_obj.context_terms
    hit_idxs = []
    for t in terms:
        i = nt.find(t)
        if i != -1:
            hit_idxs.append(i)

    if not hit_idxs:
        has_pos = _find_any(nt, _POS_CUES)
        has_neg = _find_any(nt, _NEG_CUES)
        if has_pos and has_neg:
            return "MIX"
        if has_neg:
            return "NEG"
        if has_pos:
            return "POS"
        if any(t in nt for t in factor_obj.negation_terms):
            return "POS"
        return "NEU"

    i0 = min(hit_idxs)
    lo = max(0, i0 - window)
    hi = min(len(nt), i0 + window)
    ctx = nt[lo:hi]

    has_pos = _find_any(ctx, _POS_CUES)
    has_neg = _find_any(ctx, _NEG_CUES)
    has_switch = _find_any(nt, _SWITCH_CUES)
    has_negation = any(t in ctx for t in factor_obj.negation_terms)

    if has_pos and has_neg:
        return "MIX"
    if has_neg:
        return "MIX" if has_negation or has_switch else "NEG"
    if has_pos:
        return "POS"
    if has_negation:
        return "POS"
    return "NEU"


# ------------------------- Quota selection -------------------------

def _default_quota_for_rank(rank: int) -> Dict[str, int]:
    """
    rank: 0=top1, 1=top2, 2=top3...
    반환: 라벨별 목표 개수(NEG/MIX/POS 중심)
    """
    if rank == 0:
        return {"NEG": 3, "MIX": 2, "POS": 1}  # 총 6
    return {"NEG": 2, "MIX": 2, "POS": 1}      # 총 5


def _pick_by_quota(
    candidates: List[Dict],
    quota: Dict[str, int],
    seen_ids: set,
    max_total_pick: int,
) -> List[Dict]:
    """
    candidates: score 내림차순으로 정렬된 후보 dict 리스트
    quota: {"NEG":2,"MIX":2,"POS":1} 등
    seen_ids: 전역 중복 방지
    max_total_pick: 이 factor에서 뽑을 최대치(보충 포함)
    """
    picked: List[Dict] = []
    counts = {k: 0 for k in ["NEG", "MIX", "POS", "NEU"]}

    def can_take(label: str) -> bool:
        if label in quota:
            return counts[label] < quota[label]
        return False

    # 1) quota 우선 채우기
    for c in candidates:
        if len(picked) >= max_total_pick:
            break
        rid = c.get("review_id")
        if not rid or rid in seen_ids:
            continue
        label = c.get("label", "NEU")
        if can_take(label):
            picked.append(c)
            counts[label] += 1
            seen_ids.add(rid)

    # 2) quota 미달분 보충(NEU 포함): 점수 높은 순으로 채움
    #    - 남는 슬롯은 MIX/NEG/POS/NEU 가리지 않고 채우되 중복 방지
    if len(picked) < max_total_pick:
        for c in candidates:
            if len(picked) >= max_total_pick:
                break
            rid = c.get("review_id")
            if not rid or rid in seen_ids:
                continue
            picked.append(c)
            counts[c.get("label", "NEU")] = counts.get(c.get("label", "NEU"), 0) + 1
            seen_ids.add(rid)

    return picked


def retrieve_evidence_reviews(
    df: pd.DataFrame,
    factors_map: Dict[str, Factor],
    top_factors: List[Tuple[str, float]],
    per_factor_limit: Tuple[int, int] = (5, 8),
    max_total_evidence: int = 15,
    quota_by_rank: Optional[Dict[int, Dict[str, int]]] = None,
) -> List[Dict]:
    """
    상위 요인별 증거 리뷰 추출(라벨 quota 적용)

    Args:
        df: score_XXX 컬럼이 있는 df
        factors_map: factor_key -> Factor
        top_factors: (factor_key, score) 리스트
        per_factor_limit: (min,max) (현재는 max를 후보/보충 상한으로 사용)
        max_total_evidence: 전체 evidence 상한
        quota_by_rank: {0:{...},1:{...}} 형태로 rank별 quota override 가능

    Returns:
        evidence dict list
    """
    evidence: List[Dict] = []
    seen_ids: set = set()

    _, max_n = per_factor_limit
    quota_by_rank = quota_by_rank or {}

    for rank, (factor_key, _) in enumerate(top_factors):
        if len(evidence) >= max_total_evidence:
            logger.debug(f"  - 최대 evidence 수 도달 ({max_total_evidence}), 중단")
            break

        col = f"score_{factor_key}"
        if col not in df.columns:
            logger.warning(f"  - factor '{factor_key}' 컴럼 없음, 스킵")
            continue
        if factor_key not in factors_map:
            logger.warning(f"  - factor '{factor_key}' factors_map에 없음, 스킵")
            continue

        f = factors_map[factor_key]
        logger.debug(f"  - [{rank}] {factor_key} 추출 중...")

        # rank별 quota
        quota = quota_by_rank.get(rank) or _default_quota_for_rank(rank)
        target_n = sum(quota.values())

        # 이 factor에서 뽑을 최대치:
        # - target_n 이상(보충 포함)
        # - 전체 컷에 걸리면 더 줄 수 있음
        max_pick_here = min(max_n, target_n)
        remaining_total = max_total_evidence - len(evidence)
        max_pick_here = min(max_pick_here, remaining_total)

        # 후보 풀: 중복/0점 필터로 빠지는 것 감안해 넉넉히
        try:
            subset = df.nlargest(max_pick_here * 10, col)
        except Exception:
            subset = df.sort_values(col, ascending=False).head(max_pick_here * 10)

        candidates: List[Dict] = []
        for _, row in subset.iterrows():
            rid = str(row["review_id"]) if "review_id" in row.index else None
            if not rid:
                continue

            score = _safe_float(row.get(col), 0.0)
            if score <= 0:
                continue

            norm = (row.get("_norm_text") or "")
            reasons: List[str] = []

            has_anchor = any(t in norm for t in f.anchor_terms)
            if has_anchor:
                reasons.append(f"{factor_key}+anchor")
            if any(t in norm for t in f.context_terms):
                reasons.append(f"{factor_key}+context")
            if any(t in norm for t in f.negation_terms):
                reasons.append(f"{factor_key}+negation")

            # ✅ anchor_terms가 없는 리뷰는 증거로 부적합 (context만으로는 부족)
            if not has_anchor:
                continue

            text = (row.get("text") or "")
            excerpt = extract_relevant_sentences(text, f, max_len=160)
            label = classify_text_label(text, f, window=30)

            candidates.append(
                {
                    "review_id": rid,
                    "rating": _safe_int(row.get("rating"), 0),
                    "excerpt": excerpt,
                    "reason": reasons,
                    "factor": factor_key,
                    "score": score,
                    "label": label,
                }
            )

        # score 높은 순 정렬
        candidates.sort(key=lambda x: float(x.get("score") or 0.0), reverse=True)

        # quota 기반 선택
        picked = _pick_by_quota(
            candidates=candidates,
            quota=quota,
            seen_ids=seen_ids,
            max_total_pick=max_pick_here,
        )

        evidence.extend(picked)

    return evidence