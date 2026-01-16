"""Dialogue 타입 정의"""
from typing import Literal, TypedDict

TurnType = Literal["opening", "followup", "closing"]

class SessionMetadata(TypedDict, total=False):
    """세션 메타데이터"""
    category: str
    product_name: str
    vendor: str
    created_at: str
    updated_at: str
