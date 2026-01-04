#!/usr/bin/env python3
"""REG Store: Load and parse regret factor definitions"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import pandas as pd

from .ingest import normalize


@dataclass
class Factor:
    """후회 요인 정의"""
    factor_id: int
    factor_key: str  # 하위 호환성을 위해 유지
    anchor_terms: List[str]
    context_terms: List[str]
    negation_terms: List[str]
    weight: float
    category: str = ""
    display_name: str = ""


def load_csvs(data_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """REG CSV 파일들 로드"""
    def find_file(root: Path, name: str) -> Path:
        matches = list(root.rglob(name))
        if not matches:
            raise FileNotFoundError(f"Required file not found under {root}: {name}")
        return matches[0]

    def find_any(root: Path, candidates: List[str]) -> Path:
        for name in candidates:
            matches = list(root.rglob(name))
            if matches:
                return matches[0]
        raise FileNotFoundError(f"None of candidate files found under {root}: {candidates}")

    # ✅ 현실 파일명 반영
    reviews_fp = find_any(
        data_dir,
        [
            "reviews_sample.csv",
            "reviews_final.csv",
            "review_sample.csv",
            "reviews.csv",
            "reviews_data.csv",
        ],
    )
    factors_fp = find_file(data_dir, "reg_factor.csv")
    questions_fp = find_file(data_dir, "reg_question.csv")

    reviews = pd.read_csv(reviews_fp)     # dtype 고정하지 않음(유연)
    factors = pd.read_csv(factors_fp, dtype=str).fillna("")
    questions = pd.read_csv(questions_fp, dtype=str).fillna("")

    # ✅ created_at은 선택 컬럼으로 유연화
    required = {"review_id", "rating", "text"}
    if not required.issubset(set(reviews.columns)):
        missing = required - set(reviews.columns)
        raise ValueError(f"reviews CSV missing columns: {missing}")

    if "created_at" not in reviews.columns:
        reviews["created_at"] = ""

    # 표준화: review_id는 문자열로
    reviews["review_id"] = reviews["review_id"].astype(str)

    return reviews, factors, questions


def parse_factors(df: pd.DataFrame) -> List[Factor]:
    """요인 정의 CSV를 Factor 객체 리스트로 변환"""
    factors: List[Factor] = []

    def safe_float(v: str, default: float = 1.0) -> float:
        try:
            s = str(v).strip()
            return float(s) if s else default
        except Exception:
            return default

    def split_terms(s: str) -> List[str]:
        # ✅ 구분자 유연화(| 권장, 그 외 보정)
        raw = str(s or "").strip()
        if not raw:
            return []
        raw = raw.replace(",", "|").replace(";", "|")
        parts = [p.strip() for p in raw.split("|") if p.strip()]
        # ✅ terms도 normalize해서 매칭 안정화
        return [normalize(p) for p in parts if normalize(p)]

    for _, row in df.iterrows():
        # factor_id는 필수
        factor_id = int(row.get("factor_id", 0))
        if factor_id <= 0:
            continue
        
        key = str(row.get("factor_key") or row.get("key") or "").strip()
        if not key:
            continue

        anchor = split_terms(row.get("anchor_terms", ""))
        context = split_terms(row.get("context_terms", ""))
        neg = split_terms(row.get("negation_terms", ""))

        weight = safe_float(row.get("weight", "1.0"), 1.0)
        category = str(row.get("category") or "").strip()
        display_name = str(row.get("display_name") or key).strip()

        factors.append(
            Factor(
                factor_id=factor_id,
                factor_key=key,
                anchor_terms=anchor,
                context_terms=context,
                negation_terms=neg,
                weight=weight,
                category=category,
                display_name=display_name,
            )
        )

    return factors