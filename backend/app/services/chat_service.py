"""채팅 서비스 - 세션 및 대화 유스케이스 (Service Layer)"""
import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class ChatService:
    """대화 세션 관리 및 턴 처리"""
    
    def __init__(self, data_dir: str | Path):
        """
        Args:
            data_dir: Factor/Question CSV 데이터 디렉토리
        """
        self.data_dir = Path(data_dir)
        self.sessions: Dict[str, 'DialogueSessionState'] = {}
        
    def create_session(
        self, 
        session_id: str,
        category: str, 
        product_name: str,
        reviews_df = None
    ) -> Dict[str, Any]:
        """새 대화 세션 생성
        
        Args:
            session_id: 세션 ID
            category: 제품 카테고리
            product_name: 제품명
            reviews_df: 리뷰 데이터프레임 (옵션)
            
        Returns:
            세션 정보
        """
        from ..domain.reg.store import load_csvs, parse_factors, parse_questions
        
        logger.info(f"세션 생성: {session_id} (category={category}, product={product_name})")
        
        # Factor/Question 데이터 로드
        if reviews_df is not None:
            _, factors_df, questions_df = load_csvs(self.data_dir)
            reviews = reviews_df
        else:
            reviews, factors_df, questions_df = load_csvs(self.data_dir)
        
        # 파싱
        all_factors = parse_factors(factors_df)
        factors = [f for f in all_factors if f.category == category]
        questions = parse_questions(questions_df)
        
        # 세션 상태 저장
        session_state = DialogueSessionState(
            session_id=session_id,
            category=category,
            product_name=product_name,
            reviews_df=reviews,
            factors=factors,
            questions=questions,
        )
        self.sessions[session_id] = session_state
        
        logger.info(f"  - Factors: {len(factors)}개, Questions: {len(questions)}개, Reviews: {len(reviews)}건")
        
        return {
            "session_id": session_id,
            "category": category,
            "product_name": product_name,
            "factor_count": len(factors),
            "review_count": len(reviews)
        }
    
    def process_turn(
        self, 
        session_id: str, 
        user_message: str,
        selected_factor: Optional[str] = None
    ) -> Dict[str, Any]:
        """대화 턴 처리
        
        Args:
            session_id: 세션 ID
            user_message: 사용자 메시지
            selected_factor: 선택된 factor (옵션)
            
        Returns:
            봇 응답
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session not found: {session_id}")
        
        session = self.sessions[session_id]
        logger.info(f"턴 처리: {session_id}, 메시지: {user_message[:50]}...")
        
        # 턴 수 증가
        session.turn_count += 1
        
        # 1. 사용자 메시지에서 factor 점수 추출
        from ..domain.review.normalize import normalize_text
        norm_text = normalize_text(user_message)
        
        matched_factors = []
        for factor in session.factors:
            base_score = 0.0
            if any(term in norm_text for term in factor.anchor_terms):
                base_score += 1.0
            if any(term in norm_text for term in factor.context_terms):
                base_score += 0.3
            
            weighted_score = base_score * factor.weight
            if weighted_score > 0:
                current = session.cumulative_scores.get(factor.factor_key, 0.0)
                session.cumulative_scores[factor.factor_key] = current + weighted_score
                matched_factors.append(factor.factor_key)
        
        # 2. Top factors 계산
        top_factors = self._get_top_factors(session, top_k=3)
        
        # 3. 다음 질문 생성
        next_question = self._generate_next_question(session, top_factors, selected_factor)
        
        # 4. 분석 준비 여부 체크 (3턴 이상)
        should_analyze = session.turn_count >= 3
        analysis = None
        
        if should_analyze:
            analysis = self._generate_analysis(session, top_factors)
        
        return {
            "question": next_question,
            "top_factors": [(k, round(s, 2)) for k, s in top_factors],
            "turn_count": session.turn_count,
            "has_analysis": should_analyze,
            "analysis": analysis,
            "matched_factors": matched_factors
        }
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """세션 조회"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        return {
            "session_id": session_id,
            "category": session.category,
            "product_name": session.product_name,
            "turn_count": session.turn_count,
            "factor_count": len(session.factors)
        }
    
    def _get_top_factors(self, session: 'DialogueSessionState', top_k: int = 3) -> List[Tuple[str, float]]:
        """누적 점수 기준 상위 factors 반환"""
        if not session.cumulative_scores:
            return []
        
        sorted_factors = sorted(
            session.cumulative_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_factors[:top_k]
    
    def _generate_next_question(
        self, 
        session: 'DialogueSessionState',
        top_factors: List[Tuple[str, float]],
        selected_factor: Optional[str] = None
    ) -> str:
        """다음 질문 생성"""
        # 간단한 구현: 상위 factor에 대한 질문 선택
        if not top_factors:
            return f"{session.product_name}에 대해 어떤 점이 가장 중요하신가요?"
        
        # selected_factor가 있으면 해당 factor의 질문
        if selected_factor:
            for q in session.questions:
                if q.factor_key == selected_factor:
                    return q.question_text
        
        # 상위 factor의 질문
        top_factor_key = top_factors[0][0]
        for q in session.questions:
            if q.factor_key == top_factor_key:
                return q.question_text
        
        return f"{session.product_name}의 {top_factor_key}에 대해 더 자세히 알려주세요."
    
    def _generate_analysis(
        self,
        session: 'DialogueSessionState',
        top_factors: List[Tuple[str, float]]
    ) -> Optional[Dict[str, Any]]:
        """분석 결과 생성 (간단한 구현)"""
        if not top_factors:
            return None
        
        return {
            "top_factors": [
                {
                    "factor_key": k,
                    "score": round(s, 2),
                    "display_name": self._get_factor_display_name(session, k)
                }
                for k, s in top_factors
            ],
            "total_turns": session.turn_count,
            "ready_for_llm": True
        }
    
    def _get_factor_display_name(self, session: 'DialogueSessionState', factor_key: str) -> str:
        """Factor의 표시명 반환"""
        for factor in session.factors:
            if factor.factor_key == factor_key:
                return factor.display_name or factor_key
        return factor_key


class DialogueSessionState:
    """대화 세션 상태"""
    def __init__(
        self,
        session_id: str,
        category: str,
        product_name: str,
        reviews_df,
        factors: List,
        questions: List
    ):
        self.session_id = session_id
        self.category = category
        self.product_name = product_name
        self.reviews_df = reviews_df
        self.factors = factors
        self.questions = questions
        
        self.turn_count = 0
        self.cumulative_scores: Dict[str, float] = {}
        self.dialogue_history: List[Dict[str, str]] = []

