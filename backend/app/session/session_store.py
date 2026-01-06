"""Session storage service"""
from pathlib import Path
from typing import Dict, Optional, List, Any
import uuid
import logging
import pandas as pd

from backend.dialogue.dialogue import DialogueSession

logger = logging.getLogger(__name__)


class SessionStore:
    """세션 저장소 (메모리 기반)"""
    
    def __init__(self):
        self._sessions: Dict[str, DialogueSession] = {}
        self._reviews: Dict[str, List[Dict[str, Any]]] = {}  # session_id -> reviews
    
    def create_session(self, category: str, data_dir: Path, reviews: Optional[List[Dict[str, Any]]] = None) -> str:
        """새 세션 생성"""
        session_id = str(uuid.uuid4())
        
        # 리뷰 데이터를 DataFrame으로 변환
        reviews_df = None
        if reviews:
            reviews_df = pd.DataFrame(reviews)
            self._reviews[session_id] = reviews
            logger.info(f"[SessionStore] 세션 생성 with {len(reviews)}개 리뷰")
        
        session = DialogueSession(category=category, data_dir=data_dir, reviews_df=reviews_df)
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
        특정 factor와 관련된 리뷰 반환 (품질 필터링 강화)
        
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
        logger.info(f"[get_reviews_by_factor] session_id={session_id}, factor_key={factor_key}, total_reviews={len(reviews)}")
        
        if reviews:
            first_review = reviews[0]
            logger.info(f"[첫 번째 리뷰] keys={list(first_review.keys())}, factor_matches_type={type(first_review.get('factor_matches'))}, factor_matches_len={len(first_review.get('factor_matches', []))}")
            if first_review.get('factor_matches'):
                logger.info(f"[첫 번째 match] {first_review['factor_matches'][0]}")
        
        related = []
        display_name = None
        seen_review_ids = set()  # 중복 방지
        
        # ✅ 의견/평가 키워드 (긍정 또는 부정 표현)
        opinion_keywords = [
            # 부정
            '별로', '실망', '아쉽', '문제', '불만', '후회', '안됨', '안되', '못', '느림', '약함', 
            '부족', '불편', '어렵', '힘들', '나쁨', '최악', '짜증', '화남', '실패', '고장',
            '없', '없는', '없어', '없다', '안', '소용없', '쓸모없',
            # 긍정
            '좋', '만족', '괜찮', '훌륭', '최고', '추천', '강력', '빠름', '편함', '쉬움', '완벽',
            '탁월', '우수', '뛰어', '감동', '대만족',
            # 평가 표현
            '네요', '어요', '습니다', 'ㅂ니다', '더라', '던데', '네', '음', 'ㅁ',
            '느껴', '같아', '듯', '보여', '생각', '나', '다', '결과'
        ]
        
        for review in reviews:
            review_id = review.get('review_id')
            
            for match in review.get('factor_matches', []):
                logger.info(f"  검사: match_key={match.get('factor_key')} vs target={factor_key}")
                if match['factor_key'] == factor_key:
                    # 이미 추가된 리뷰는 건너뛰기
                    if review_id in seen_review_ids:
                        logger.info(f"  ⏭️  중복 건너뛰기: review_id={review_id}")
                        break
                    
                    # ✅ 품질 검증: 문장이 실제 의견/평가를 포함하는지 확인
                    sentences = match.get('sentences', [])
                    if not sentences:
                        logger.info(f"  ⚠️  문장 없음, 건너뛰기")
                        break
                    
                    # 모든 문장을 합쳐서 검증
                    combined_text = ' '.join(sentences)
                    
                    # 1) 너무 짧은 문장 제외 (15자 미만)
                    if len(combined_text.strip()) < 15:
                        logger.info(f"  ⚠️  너무 짧은 문장({len(combined_text)}자), 건너뛰기: {combined_text[:30]}")
                        break
                    
                    # 2) 의견/평가 표현이 있는지 확인
                    has_opinion = any(keyword in combined_text for keyword in opinion_keywords)
                    
                    if not has_opinion:
                        logger.info(f"  ⚠️  의견 표현 없음, 건너뛰기: {combined_text[:50]}")
                        break
                    
                    # 3) matched_terms가 실제로 문장에 포함되어 있는지 재확인
                    matched_terms = match.get('matched_terms', [])
                    if matched_terms:
                        has_matched_term = any(term in combined_text for term in matched_terms)
                        if not has_matched_term:
                            logger.info(f"  ⚠️  매칭 키워드 미포함, 건너뛰기: terms={matched_terms}, text={combined_text[:50]}")
                            break
                    
                    # display_name 저장 (첫 매칭에서)
                    if not display_name:
                        display_name = match.get('display_name', factor_key)
                    
                    related.append({
                        'review_id': review_id,
                        'rating': review.get('rating'),
                        'sentences': sentences,
                        'matched_terms': matched_terms,
                        'weight': match.get('weight', 1.0)
                    })
                    seen_review_ids.add(review_id)
                    logger.info(f"  ✅ 품질 검증 통과! sentences={len(sentences)}개")
                    logger.info(f"    sentences 배열: {sentences}")
                    break
        
        logger.info(f"[매칭 결과] factor_key={factor_key}, matched_count={len(related)} (품질 필터링 후)")
        
        # weight와 rating으로 우선순위 정렬 (낮은 평점 우선, 높은 weight 우선)
        related.sort(key=lambda x: (x.get('rating', 5), -x.get('weight', 1.0)))
        
        return {
            'factor_key': factor_key,
            'display_name': display_name or factor_key,
            'count': len(related),
            'examples': related[:limit]
        }
