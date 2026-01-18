#!/usr/bin/env python3
"""REG Store: Load and parse regret factor definitions (Domain Layer - Pure Python)"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import pandas as pd

# 정규화 함수는 domain/rules/review/normalize.py에서 import
from ....domain.rules.review.normalize import normalize_text as normalize


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


@dataclass
class Question:
    """질문 정의"""
    question_id: int
    factor_id: int
    factor_key: str
    question_text: str
    answer_type: str  # 'no_choice' | 'single_choice'
    choices: str
    next_factor_hint: str


def load_csvs(data_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """REG CSV 파일들 로드 (버전 자동 감지)"""
    
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
    
    def find_latest_versioned_file(root: Path, base_pattern: str) -> Path:
        """
        버전 번호가 포함된 파일 중 최신 버전을 찾음
        예: reg_factor_v4.csv, reg_factor_v3.csv -> reg_factor_v4.csv 선택
        """
        # 패턴에서 확장자 분리
        if base_pattern.endswith('.csv'):
            base_name = base_pattern[:-4]  # .csv 제거
            extension = '.csv'
        else:
            base_name = base_pattern
            extension = ''
        
        # 버전 없는 파일과 버전 있는 파일 모두 찾기
        pattern = f"{base_name}*.csv" if extension else f"{base_name}*"
        all_matches = list(root.rglob(pattern))
        
        if not all_matches:
            raise FileNotFoundError(f"No files found matching pattern: {pattern}")
        
        # 버전 정보 추출 및 정렬
        versioned_files = []
        base_file = None
        
        # 버전 패턴: _v숫자 형태
        version_pattern = re.compile(rf'{re.escape(base_name)}_v(\d+)\.csv$')
        
        for file_path in all_matches:
            filename = file_path.name
            
            # 정확히 base_pattern과 일치하는 파일 (버전 없음)
            if filename == base_pattern:
                base_file = file_path
                continue
            
            # 버전 번호 추출
            match = version_pattern.search(filename)
            if match:
                version_num = int(match.group(1))
                versioned_files.append((version_num, file_path))
        
        # 버전 있는 파일이 있으면 가장 높은 버전 선택
        if versioned_files:
            versioned_files.sort(key=lambda x: x[0], reverse=True)
            latest = versioned_files[0][1]
            print(f"📌 Loading latest version: {latest.name}")
            return latest
        
        # 버전 없는 기본 파일이 있으면 그것 사용
        if base_file:
            print(f"📌 Loading base file: {base_file.name}")
            return base_file
        
        # 아무것도 없으면 에러
        raise FileNotFoundError(f"No valid files found for pattern: {base_pattern}")

    # ✅ 리뷰 파일 (기존 로직 유지)
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
    
    # ✅ Factor와 Question은 버전 체크하여 최신 파일 로드
    factors_fp = find_latest_versioned_file(data_dir, "reg_factor.csv")
    questions_fp = find_latest_versioned_file(data_dir, "reg_question.csv")

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


def parse_questions(df: pd.DataFrame) -> List[Question]:
    """질문 정의 CSV를 Question 객체 리스트로 변환"""
    questions: List[Question] = []

    def safe_int(v: str, default: int = 0) -> int:
        try:
            s = str(v).strip()
            return int(s) if s else default
        except Exception:
            return default

    for _, row in df.iterrows():
        # question_id는 필수
        question_id = safe_int(row.get("question_id", 0))
        if question_id <= 0:
            continue
        
        # factor_id는 필수
        factor_id = safe_int(row.get("factor_id", 0))
        if factor_id <= 0:
            continue
        
        # question_text는 필수
        question_text = str(row.get("question_text") or "").strip()
        if not question_text:
            continue

        factor_key = str(row.get("factor_key") or "").strip()
        answer_type = str(row.get("answer_type") or "no_choice").strip()
        choices = str(row.get("choices") or "").strip()
        next_factor_hint = str(row.get("next_factor_hint") or "").strip()

        questions.append(
            Question(
                question_id=question_id,
                factor_id=factor_id,
                factor_key=factor_key,
                question_text=question_text,
                answer_type=answer_type,
                choices=choices,
                next_factor_hint=next_factor_hint,
            )
        )

    return questions