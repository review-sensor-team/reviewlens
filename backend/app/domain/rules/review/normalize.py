#!/usr/bin/env python3
"""리뷰 데이터 정규화 (Domain Layer - Pure Python)"""
import hashlib
import re
from typing import Optional, Tuple

import pandas as pd


_REPEAT_RE = re.compile(r"(ㅋ|ㅎ|!|\?){3,}")  # ㅋㅋㅋㅋ, ㅎㅎㅎㅎ, !!!!!, ????


def normalize_text(text: Optional[str]) -> str:
    """텍스트 정규화: 소문자 변환, 특수문자 정리, 공백 정리, 반복문자 축약"""
    if text is None:
        return ""

    s = str(text).lower()

    # 단위/기호 보정(자주 등장하는 것만)
    s = s.replace("℃", "도").replace("ℓ", "l").replace("㎖", "ml").replace("㏈", "db").replace("dＢ", "db").replace("dB", "db")

    # 허용 문자 외 제거(한글/자모/영문/숫자/공백 + 일부 구두점/기호)
    s = re.sub(r"[^\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F\w\d\s\.,!\?\-\(\)\[\]:;'\"%&@/\\]+", " ", s)

    # 반복문자 축약: ㅋㅋㅋㅋ → ㅋㅋ, !!!!! → !!
    s = _REPEAT_RE.sub(lambda m: m.group(1) * 2, s)

    # 공백 정리
    s = re.sub(r"\s+", " ", s).strip()
    return s


def sha1_of_text(text: str) -> str:
    """텍스트의 SHA1 해시 생성"""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def dedupe_reviews(df: pd.DataFrame) -> Tuple[pd.DataFrame, int, int]:
    """리뷰 데이터프레임 중복 제거(exact)"""
    df = df.copy()
    df["_norm_text"] = df["text"].fillna("").map(normalize_text)
    df["_sha1"] = df["_norm_text"].map(sha1_of_text)

    total = len(df)
    df = df.drop_duplicates(subset=["_sha1"]).reset_index(drop=True)
    removed = total - len(df)
    return df, total, removed


def normalize_review(review: dict, vendor: str) -> dict:
    """
    벤더별로 다른 형식의 리뷰를 표준 형식으로 변환
    
    Args:
        review: 원본 리뷰 데이터
        vendor: 벤더 이름 (smartstore, coupang 등)
        
    Returns:
        정규화된 리뷰 데이터 (text, rating, date, author, verified)
    """
    normalized = {
        "review_id": "",  # 추가: review_id 필드
        "text": "",
        "rating": 0,
        "date": "",
        "author": "",
        "verified": False
    }
    
    if vendor == "smartstore":
        # JSON 파일 형식: review_id, rating, text, created_at
        # 레거시 CSV 형식: review_text, rating, created_date, reviewer_name
        normalized["review_id"] = review.get("review_id", review.get("id", ""))  # review_id 추출
        normalized["text"] = review.get("text", review.get("review_text", ""))
        normalized["rating"] = review.get("rating", 0)
        normalized["date"] = review.get("created_at", review.get("created_date", ""))
        normalized["author"] = review.get("author", review.get("reviewer_name", ""))
    elif vendor == "coupang":
        # TODO: Coupang 형식 처리
        pass
    
    return normalized


