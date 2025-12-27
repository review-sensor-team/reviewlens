#!/usr/bin/env python3
"""ReviewLens CLI: Backward compatibility wrapper for regret_bot"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .pipeline.reg_store import load_csvs, parse_factors, Factor
from .pipeline.ingest import dedupe_reviews
from .pipeline.sensor import compute_review_factor_scores, select_top_factors_from_question
from .pipeline.retrieval import retrieve_evidence_reviews
from .pipeline.prompt_builder import write_llm_context, write_debug_report


def pick_next_questions(
    questions_df: pd.DataFrame,
    top_factors: List[Tuple[str, float]],
    n: int = 2
) -> List[str]:
    """상위 요인에 대한 질문 선택"""
    qs: List[Tuple[int, str]] = []
    for factor_key, _ in top_factors:
        matches = questions_df[
            questions_df.apply(lambda r: str(r.get("factor_key") or "") == factor_key, axis=1)
        ]
        if matches is None or len(matches) == 0:
            continue

        def prio_val(r):
            try:
                return int(r.get("priority") or 999)
            except Exception:
                return 999

        sorted_q = sorted(matches.to_dict(orient="records"), key=prio_val)
        for rec in sorted_q:
            qs.append((prio_val(rec), str(rec.get("question") or "")))

    qs_sorted = sorted(qs, key=lambda x: x[0])
    picked = [q for _, q in qs_sorted][:n]
    return picked


def main():
    """Main CLI entry point"""
    data_dir = Path("backend/data")
    out_dir = Path("out")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    reviews_df, factors_df, questions_df = load_csvs(data_dir)
    print(f"Loaded {len(reviews_df)} reviews, {len(factors_df)} factors, {len(questions_df)} questions")
    
    # Deduplicate
    deduped_df, total, removed = dedupe_reviews(reviews_df)
    print(f"Deduplication: {total} → {len(deduped_df)} (removed {removed})")
    
    # Parse factors
    factors = parse_factors(factors_df)
    factors_map = {f.factor_key: f for f in factors}
    print(f"Parsed {len(factors)} factors")
    
    # Score reviews
    scored_df, factor_counts = compute_review_factor_scores(deduped_df, factors)
    print(f"Computed factor scores for {len(scored_df)} reviews")
    
    # Simulate user question
    question = "소음이 너무 심해요. 이웃소음 때문에 환불하고 싶어요."
    top_factors = select_top_factors_from_question(question, factors, top_k=3)
    print(f"Top factors for question: {top_factors}")
    
    # Retrieve evidence
    evidence = retrieve_evidence_reviews(scored_df, factors_map, top_factors, per_factor_limit=(5, 8))
    print(f"Selected {len(evidence)} evidence reviews")
    
    # Pick next questions
    next_qs = pick_next_questions(questions_df, top_factors, n=2)
    print(f"Next questions: {next_qs}")
    
    # Write outputs
    llm_fp = write_llm_context(out_dir, "hotel_sample", question, top_factors, evidence, next_qs)
    debug_fp = write_debug_report(out_dir, total, removed, factor_counts, evidence)
    
    print(f"\n✅ Pipeline completed successfully!")
    print(f"  - LLM context: {llm_fp}")
    print(f"  - Debug report: {debug_fp}")


if __name__ == "__main__":
    main()
