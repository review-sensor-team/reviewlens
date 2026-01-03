"""Session storage service"""
from pathlib import Path
from typing import Dict, Optional, List, Any
import uuid

from backend.pipeline.dialogue import DialogueSession


class SessionStore:
    """세션 저장소 (메모리 기반)"""
    
    def __init__(self):
        self._sessions: Dict[str, DialogueSession] = {}
        self._reviews: Dict[str, List[Dict[str, Any]]] = {}  # session_id -> reviews
    
    def create_session(self, category: str, data_dir: Path) -> str:
        """새 세션 생성"""
        session_id = str(uuid.uuid4())
        session = DialogueSession(category=category, data_dir=data_dir)
        self._sessions[session_id] = session
        return session_id
    
    def get_session(self, session_id: str) -> Optional[DialogueSession]:
        """세션 조회"""
        return self._sessions.get(session_id)
    
    def delete_session(self, session_id: str):
        """세션 삭제"""
        if session_id in self._sessions:
            del self._sessions[session_id]
        if session_id in self._reviews:
            del self._reviews[session_id]
    
    def store_reviews(self, session_id: str, reviews: List[Dict[str, Any]]):
        """세션에 분석된 리뷰 저장"""
        self._reviews[session_id] = reviews
    
    def get_reviews(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """세션의 리뷰 조회"""
        return self._reviews.get(session_id)
    
    def get_reviews_by_factor(self, session_id: str, factor_key: str, limit: int = 3) -> Dict[str, Any]:
        """
        특정 factor와 관련된 리뷰 반환
        
        Returns:
            {
                'factor_key': str,
                'count': int,
                'examples': [
                    {
                        'rating': int,
                        'sentences': [str],
                        'matched_terms': [str]
                    }
                ]
            }
        """
        reviews = self._reviews.get(session_id, [])
        related = []
        
        for review in reviews:
            for match in review.get('factor_matches', []):
                if match['factor_key'] == factor_key:
                    related.append({
                        'rating': review.get('rating'),
                        'sentences': match['sentences'],
                        'matched_terms': match['matched_terms'],
                        'weight': match.get('weight', 1.0)
                    })
                    break
        
        # weight와 rating으로 우선순위 정렬 (낮은 평점 우선, 높은 weight 우선)
        related.sort(key=lambda x: (x.get('rating', 5), -x.get('weight', 1.0)))
        
        return {
            'factor_key': factor_key,
            'count': len(related),
            'examples': related[:limit]
        }
