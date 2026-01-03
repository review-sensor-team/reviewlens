"""Chat API routes"""
from fastapi import APIRouter, HTTPException
from pathlib import Path

from backend.pipeline.dialogue import DialogueSession
from ..collector import SmartStoreCollector
from ..collector.factor_analyzer import FactorAnalyzer
from ..schemas.requests import ChatRequest, SessionStartRequest, CollectReviewsRequest, StartWithReviewsRequest
from ..schemas.responses import ChatResponse, SessionStartResponse, CollectReviewsResponse, Review, FactorMatch
from ..services.session_store import SessionStore

router = APIRouter()
session_store = SessionStore()


@router.post("/start", response_model=SessionStartResponse)
async def start_session(request: SessionStartRequest):
    """대화 세션 시작"""
    try:
        session_id = session_store.create_session(
            category=request.category,
            data_dir=Path("backend/data")
        )
        return SessionStartResponse(
            session_id=session_id,
            message="세션이 시작되었습니다. 무엇이 궁금하신가요?"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start-with-reviews", response_model=SessionStartResponse)
async def start_session_with_reviews(request: StartWithReviewsRequest):
    """리뷰 데이터와 함께 세션 시작"""
    try:
        # 리뷰 데이터를 세션에 저장
        session_store.store_reviews(request.session_id, request.reviews)
        
        return SessionStartResponse(
            session_id=request.session_id,
            message="리뷰 분석이 완료되었습니다. 궁금한 점을 물어보세요!"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """대화 메시지 전송"""
    session = session_store.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        bot_turn = session.step(request.message)
        # 주요 factor에 대한 관련 리뷰 조회
        related_reviews = {}
        if bot_turn.top_factors:
            # 상위 3개 factor에 대한 리뷰 정보
            for factor_key, score in bot_turn.top_factors[:3]:
                review_info = session_store.get_reviews_by_factor(
                    request.session_id, 
                    factor_key, 
                    limit=3
                )
                if review_info['count'] > 0:
                    related_reviews[factor_key] = review_info
        
        # 봇 메시지에 리뷰 정보 추가
        bot_message = bot_turn.question_text
        if related_reviews and not bot_turn.is_final:
            # 가장 관련성 높은 factor의 리뷰 정보 추가
            top_factor_key = list(related_reviews.keys())[0]
            top_factor_info = related_reviews[top_factor_key]
            
            bot_message += f"\n\n📝 관련 리뷰 {top_factor_info['count']}건 중 일부:\n"
            for i, example in enumerate(top_factor_info['examples'], 1):
                sentences = ' '.join(example['sentences'][:2])  # 최대 2문장
                bot_message += f"\n{i}. ⭐{example['rating']}점: {sentences}"
        
        return ChatResponse(
            session_id=request.session_id,
            bot_message=bot_message,
            is_final=bot_turn.is_final,
            top_factors=[{"factor_key": k, "score": s} for k, s in bot_turn.top_factors],
            llm_context=bot_turn.llm_context,
            related_reviews=related_reviews
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect-reviews", response_model=CollectReviewsResponse)
async def collect_reviews(request: CollectReviewsRequest):
    """스마트스토어 리뷰 수집"""
    try:
        # 리뷰 수집
        collector = SmartStoreCollector(
            product_url=request.product_url,
            headless=True
        )
        
        reviews = collector.collect_reviews(
            max_reviews=request.max_reviews,
            sort_by_low_rating=request.sort_by_low_rating
        )
        
        if not reviews:
            return CollectReviewsResponse(
                success=False,
                message="리뷰를 수집하지 못했습니다.",
                reviews=[],
                total_count=0
            )
        
        # backend 형식으로 변환
        converted_reviews = collector.convert_to_backend_format(reviews)
        
        # Factor 분석 추가 (기본 카테고리 사용)
        analyzer = FactorAnalyzer(category='appliance_heated_humidifier')
        
        # 각 리뷰에 factor 분석 결과 추가
        for review in converted_reviews:
            factor_matches = analyzer.analyze_review(review['text'])
            review['factor_matches'] = factor_matches
        
        # 리뷰 응답 생성
        review_responses = []
        for r in converted_reviews:
            factor_match_models = [
                FactorMatch(
                    factor_key=fm['factor_key'],
                    display_name=fm['display_name'],
                    sentences=fm['sentences'],
                    matched_terms=fm['matched_terms']
                )
                for fm in r.get('factor_matches', [])
            ]
            
            review_responses.append(Review(
                review_id=r['review_id'],
                rating=r['rating'],
                text=r['text'],
                created_at=r['created_at'],
                factor_matches=factor_match_models
            ))
        
        return CollectReviewsResponse(
            success=True,
            message=f"리뷰 {len(converted_reviews)}건을 수집했습니다.",
            reviews=review_responses,
            total_count=len(converted_reviews)
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
