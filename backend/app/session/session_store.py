"""Session storage service"""
from pathlib import Path
from typing import Dict, Optional, List, Any
import uuid
import logging
import pandas as pd

from backend.app.domain.dialogue.session import DialogueSession
from backend.app.infra.persistence.session_repo import SessionPersistence

logger = logging.getLogger("backend.app.session.session_store")


class SessionStore:
    """세션 저장소 (메모리 + JSON 파일 영속화)"""
    
    def __init__(self, enable_persistence: bool = True, auto_restore: bool = False):
        self._sessions: Dict[str, DialogueSession] = {}
        self._reviews: Dict[str, List[Dict[str, Any]]] = {}  # session_id -> reviews
        self._metadata: Dict[str, Dict[str, Any]] = {}  # session_id -> metadata (product_url, product_name)
        
        # 영속화 기능
        self.enable_persistence = enable_persistence
        self.persistence = SessionPersistence() if enable_persistence else None
        
        # 서버 시작 시 기존 세션 복원 (startup 이벤트에서 수동으로 호출)
        if self.enable_persistence and auto_restore:
            self._restore_sessions()
    
    @staticmethod
    def _convert_term_for_display(term: str) -> str:
        """검색용 키워드를 사용자 친화적으로 변환
        
        예: '아프' -> '아픔', '무거운' -> '무거움', '길어' -> '김', '느려' -> '느림'
        """
        # 1음절 또는 너무 짧은 경우 그대로 반환
        if len(term) <= 1:
            return term
        
        # 어간 형태를 명사형으로 변환
        # 1. ㅡ 불규칙: "아프" -> "아픔"
        if term.endswith('프'):
            return term[:-1] + '픔'
        
        # 2. ㅡ 불규칙: "슬프" -> "슬픔"
        elif term.endswith(('운', '른')):
            # "무거운" -> "무거움", "느른" -> "느름"
            return term[:-1] + '움'
        
        # 3. 어/여 어미: "길어", "더워", "무거워" -> 명사형
        elif term.endswith('워'):
            # "무거워" -> "무거움"
            return term[:-1] + '움'
        elif term.endswith('어') and len(term) >= 3:
            # "길어" -> "김", "적어" -> "적음", "느려" -> "느림"
            # 마지막 모음이 '어'인 경우
            base = term[:-1]
            # 받침이 있는지 확인 (한글 유니코드 처리)
            if base:
                last_char = base[-1]
                if '가' <= last_char <= '힣':
                    # 한글인 경우: 받침 체크
                    code = ord(last_char) - 0xAC00
                    jongseong = code % 28
                    if jongseong > 0:
                        # 받침 있음: "적" + "어" -> "적음"
                        return base + '음'
                    else:
                        # 받침 없음: "길" + "어" -> "김"
                        return base + '음'
            return term[:-1] + '음'
        
        # 4. 거 어미: "뜨거", "무거" -> 명사형
        elif term.endswith('거') and len(term) >= 3:
            # "무거" -> "무거움", "뜨거" -> "뜨거움"
            return term + '움'
        
        # 5. 려/려 어미: "걸려", "눌려" -> 명사형
        elif term.endswith('려') and len(term) >= 3:
            # "걸려" -> "걸림"
            return term[:-1] + '림'
        
        # 6. 다 종결어미는 그대로
        elif term.endswith('다'):
            return term
        
        # 기본적으로 그대로 반환
        return term
    
    def _restore_sessions(self):
        """저장된 세션 복원"""
        try:
            if not self.persistence:
                logger.warning("[세션 복원] Persistence가 비활성화됨")
                return
            
            session_ids = self.persistence.list_sessions()
            logger.info(f"[세션 복원] {len(session_ids)}개 세션 발견")
            
            if len(session_ids) == 0:
                logger.info("[세션 복원] 복원할 세션 없음")
                return
            
            restored_count = 0
            for session_id in session_ids:
                try:
                    if self._restore_single_session(session_id):
                        restored_count += 1
                except Exception as e:
                    logger.error(f"[세션 복원 실패] {session_id}: {str(e)}", exc_info=True)
            
            logger.info(f"[세션 복원 완료] {restored_count}/{len(session_ids)}개 복원 성공")
        except Exception as e:
            logger.error(f"[세션 복원 전체 실패] {str(e)}", exc_info=True)
    
    def _restore_single_session(self, session_id: str) -> bool:
        """단일 세션 복원"""
        try:
            data = self.persistence.load_session(session_id)
            if not data:
                return False
            
            # DialogueSession 재생성
            reviews_df = data.get("reviews_df", pd.DataFrame())
            category = data.get("category", "unknown")
            product_name = data.get("product_name")
            
            # 세션 재생성
            session = DialogueSession(
                category=category,
                data_dir=Path("backend/data"),
                reviews_df=reviews_df,
                product_name=product_name
            )
            
            # Dialogue 상태 복원
            dialogue_state = data.get("dialogue_state", {})
            if dialogue_state:
                session.turn_count = dialogue_state.get("turn_count", 0)
                session.stability_hits = dialogue_state.get("stability_hits", 0)
                session.cumulative_scores = dialogue_state.get("cumulative_scores", {})
                session.prev_top3 = dialogue_state.get("prev_top3", [])
                session.dialogue_history = dialogue_state.get("dialogue_history", [])
            
            # 메모리에 저장
            self._sessions[session_id] = session
            
            # 리뷰 데이터 복원
            if not reviews_df.empty:
                self._reviews[session_id] = reviews_df.to_dict(orient="records")
            
            # 메타데이터 저장
            self._metadata[session_id] = {
                "product_url": data.get("product_url"),
                "product_name": data.get("product_name"),
                "category": category
            }
            
            logger.info(f"[세션 복원 성공] {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"[세션 복원 실패] {session_id}: {str(e)}", exc_info=True)
            return False
    
    def _save_session(self, session_id: str):
        """세션 데이터를 JSON 파일로 저장"""
        if not self.enable_persistence:
            return
        
        try:
            session = self._sessions.get(session_id)
            if not session:
                return
            
            metadata = self._metadata.get(session_id, {})
            reviews_df = pd.DataFrame(self._reviews.get(session_id, []))
            
            session_data = {
                "dialogue": session,
                "product_url": metadata.get("product_url"),
                "product_name": metadata.get("product_name"),
                "category": metadata.get("category"),
                "reviews_df": reviews_df
            }
            
            self.persistence.save_session(session_id, session_data)
        except Exception as e:
            logger.error(f"[세션 저장 실패] {session_id}: {str(e)}", exc_info=True)
    
    def create_session(self, category: str, data_dir: Path, reviews: Optional[List[Dict[str, Any]]] = None, product_name: Optional[str] = None, product_url: Optional[str] = None) -> str:
        """새 세션 생성"""
        session_id = str(uuid.uuid4())
        
        # 리뷰 데이터를 DataFrame으로 변환
        reviews_df = None
        if reviews:
            reviews_df = pd.DataFrame(reviews)
            self._reviews[session_id] = reviews
            logger.info(f"[SessionStore] 세션 생성 with {len(reviews)}개 리뷰, product_name={product_name}")
        
        session = DialogueSession(category=category, data_dir=data_dir, reviews_df=reviews_df, product_name=product_name)
        self._sessions[session_id] = session
        
        # 메타데이터 저장
        self._metadata[session_id] = {
            "product_url": product_url,
            "product_name": product_name,
            "category": category
        }
        
        # 파일로 저장
        self._save_session(session_id)
        
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
    
    def reset_dialogue(self, session_id: str):
        """대화만 초기화 (리뷰 데이터는 유지)"""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # 기존 데이터 백업
        reviews_df = session.reviews_df
        product_name = session.product_name
        category = session.category
        data_dir = Path("backend/data")  # DialogueSession의 기본 data_dir
        
        # 메타데이터 백업
        metadata = self._metadata.get(session_id, {})
        reviews = self._reviews.get(session_id, [])
        
        # 새 DialogueSession 생성 (대화 히스토리 초기화)
        new_session = DialogueSession(
            category=category,
            data_dir=data_dir,
            reviews_df=reviews_df,
            product_name=product_name
        )
        
        # 세션 교체
        self._sessions[session_id] = new_session
        
        # 리뷰와 메타데이터는 유지
        self._reviews[session_id] = reviews
        self._metadata[session_id] = metadata
        
        # 파일로 저장
        self._save_session(session_id)
        
        logger.info(f"[SessionStore] 세션 재분석 완료: {session_id}")
    
    def store_reviews(self, session_id: str, reviews: List[Dict[str, Any]]):
        """세션에 분석된 리뷰 저장"""
        self._reviews[session_id] = reviews
        # 파일로 저장
        self._save_session(session_id)
    
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
        
        # 각 anchor_term별 리뷰 수 계산 (표시명 변환 적용)
        term_counts = {}
        for item in related:
            for term in item.get('matched_terms', []):
                display_term = self._convert_term_for_display(term)
                term_counts[display_term] = term_counts.get(display_term, 0) + 1
        
        logger.info(f"[term별 카운트] {term_counts}")
        
        return {
            'factor_key': factor_key,
            'display_name': display_name or factor_key,
            'count': len(related),
            'term_counts': term_counts,  # 각 term별 리뷰 수
            'examples': related[:limit]
        }
