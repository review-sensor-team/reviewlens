#!/usr/bin/env python3
"""Prompt Builder: Generate LLM context JSON"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

from .reg_store import Factor  # ✅ Factor 정의(표시명, 키 매핑용)


def _clip(s: str, n: int = 220) -> str:
    s = (s or "").strip()
    return s[:n]


def write_llm_context(
    out_dir: Path,
    category_slug: str,
    user_question: str,
    top_factors: List[Tuple[str, float]],
    evidence_reviews: List[Dict],
    next_questions: List[str],
    *,
    run_id: str | None = None,
    include_debug_fields: bool = True,
    # ✅ NEW: factor 표시명 매핑을 넣으면 top_factors에 display_name 포함 가능
    factors_map: Optional[Dict[str, Factor]] = None,
    schema_version: str = "v2",
) -> Path:
    """LLM 컨텍스트 JSON 파일 생성"""

    out_dir.mkdir(parents=True, exist_ok=True)

    # ✅ 실행 단위 식별자(덮어쓰기 방지/재현성)
    if run_id is None:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ✅ evidence를 토큰 효율적으로 정리
    ev: List[Dict[str, Any]] = []
    for e in evidence_reviews:
        item: Dict[str, Any] = {
            "review_id": e.get("review_id"),
            "rating": e.get("rating", 0),
            "excerpt": _clip(e.get("excerpt", ""), 220),
            "reason": e.get("reason", []),
            "label": e.get("label", "NEU"),  # POS/NEG/MIX/NEU
            # ✅ factor_key를 명시(프롬프트에서 evidence_ids 연결 용)
            "factor_key": e.get("factor"),
        }
        if include_debug_fields:
            item["score"] = float(e.get("score") or 0.0)
        ev.append(item)

    # ✅ top_factors에 display_name 같이 제공(LLM이 key 대신 사용자 친화 라벨로 출력하도록 유도)
    tf: List[Dict[str, Any]] = []
    for k, s in top_factors:
        display_name = k
        if factors_map and k in factors_map:
            dn = getattr(factors_map[k], "display_name", "") or ""
            display_name = dn.strip() or k
        tf.append({"factor_key": k, "display_name": display_name, "score": float(s)})

    ctx: Dict[str, Any] = {
        "meta": {
            "run_id": run_id,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "version": schema_version,
        },
        "category_slug": category_slug,
        "user_question": user_question,
        "top_factors": tf,
        "evidence_reviews": ev,
        "next_questions_to_ask": next_questions,
        "safety_rules": [
            "라벨(label)은 참고용 힌트이며, 최종 판단은 excerpt 내용에 근거할 것",
            "근거 리뷰는 짧게 인용할 것",
            "의학/법률 조언 금지",
        ],
        # ✅ LLM 출력 스키마(테스트/평가/프론트 연동용)
        "output_schema_hint": {
            "must_include_evidence_ids": True,
            "final_recommendation_enum": ["구매", "보류", "대안 탐색"],
        },
    }

    fp = out_dir / f"llm_context_{run_id}.json"
    with fp.open("w", encoding="utf-8") as f:
        json.dump(ctx, f, ensure_ascii=False, indent=2)

    # ✅ 최신 파일을 고정 이름으로도 복사(편의)
    latest = out_dir / "llm_context.json"
    with latest.open("w", encoding="utf-8") as f:
        json.dump(ctx, f, ensure_ascii=False, indent=2)

    return fp


def write_debug_report(
    out_dir: Path,
    input_count: int,
    removed: int,
    factor_counts: Dict[str, int],
    evidence_reviews: List[Dict],
    *,
    top_k: int = 10,
) -> Path:
    """디버그 리포트 생성"""
    out_dir.mkdir(parents=True, exist_ok=True)
    fp = out_dir / "debug_report.md"

    lines: List[str] = []
    lines.append("# Debug Report")
    lines.append("")
    lines.append(f"- Input reviews: {input_count}")
    lines.append(f"- Exact-dedup removed: {removed}")
    lines.append("")

    lines.append("## Top factors by hit count")
    sorted_f = sorted(factor_counts.items(), key=lambda x: x[1], reverse=True)[:top_k]
    for k, c in sorted_f:
        lines.append(f"- `{k}`: {c} reviews")
    lines.append("")

    lines.append("## Evidence reviews selected")
    for e in evidence_reviews:
        rid = e.get("review_id")
        rating = e.get("rating", 0)
        factor = e.get("factor") or e.get("factor_key")
        score = e.get("score")
        label = e.get("label", "NEU")
        excerpt = _clip(e.get("excerpt", ""), 160)
        reasons = ", ".join(e.get("reason", [])[:4])

        lines.append(f"- **{rid}** | rating={rating} | factor={factor} | score={score} | label={label}")
        if reasons:
            lines.append(f"  - reasons: {reasons}")
        if excerpt:
            lines.append(f"  - excerpt: {excerpt}")

    with fp.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return fp