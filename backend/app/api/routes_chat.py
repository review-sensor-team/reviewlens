"""Chat API routes"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pathlib import Path

from backend.pipeline.dialogue import DialogueSession
from ..collector import SmartStoreCollector
from ..collector.factor_analyzer import FactorAnalyzer
from ..schemas.requests import ChatRequest, SessionStartRequest, CollectReviewsRequest
from ..schemas.responses import ChatResponse, SessionStartResponse, CollectReviewsResponse, Review, FactorMatch
from ..services.session_store import SessionStore

logger = logging.getLogger("api.chat")

router = APIRouter()
session_store = SessionStore()

# 리뷰 수집 캐시 (URL을 키로 사용)
review_cache: Dict[str, Dict] = {}
MAX_CACHE_SIZE = 10  # 최근 10개 URL만 캐시


def get_available_categories() -> List[Dict[str, str]]:
    """사용 가능한 카테고리 목록 반환"""
    return [
        {'key': 'appliance_induction', 'name': '인덕션'},
        {'key': 'electronics_coffee_machine', 'name': '커피머신'},
        {'key': 'electronics_earphone', 'name': '이어폰/에어팟'},
        {'key': 'furniture_chair', 'name': '의자'},
        {'key': 'furniture_desk', 'name': '책상/데스크'},
        {'key': 'furniture_mattress', 'name': '매트리스'},
        {'key': 'furniture_bookshelf', 'name': '책장'},
        {'key': 'appliance_heated_humidifier', 'name': '가습기'},
        {'key': 'appliance_bedding_cleaner', 'name': '침구청소기'},
        {'key': 'robot_cleaner', 'name': '로봇청소기'},
    ]


def detect_category(url: str, page_title: Optional[str] = None, reviews: Optional[List[Dict]] = None) -> Tuple[Optional[str], str]:
    """URL, 페이지 제목, 리뷰 내용에서 카테고리 자동 감지
    
    Args:
        url: 상품 URL
        page_title: 페이지 제목 (선택사항)
        reviews: 수집된 리뷰 리스트 (선택사항)
    
    Returns:
        (detected_category, confidence): 감지된 카테고리와 신뢰도 ('high' | 'low' | 'failed')
    """
    # URL과 제목을 모두 검색 대상으로
    search_text = url.lower()
    if page_title:
        search_text += " " + page_title.lower()
    
    # 리뷰 텍스트도 검색 대상에 추가 (상위 20개만)
    if reviews:
        review_texts = " ".join([r.get('text', '')[:100] for r in reviews[:20]])
        search_text += " " + review_texts.lower()
    
    logger.debug(f"[카테고리 감지] search_text_length={len(search_text)}, has_reviews={bool(reviews)}")
    
    # 카테고리별 키워드 매핑 (강한 키워드)
    strong_keywords = {
        'appliance_induction': ['인덕션', 'induction', '하이라이트'],
        'electronics_coffee_machine': ['커피머신', 'coffee-machine', 'espresso', '에스프레소'],
        'electronics_earphone': ['에어팟', 'airpod'],
        'furniture_chair': ['의자', 'chair', '체어'],
        'furniture_desk': ['책상', 'desk'],
        'furniture_mattress': ['매트리스', 'mattress'],
        'furniture_bookshelf': ['책장', 'bookshelf'],
        'appliance_heated_humidifier': ['가습기', 'humidifier'],
        'appliance_bedding_cleaner': ['침구청소기', 'bedding-cleaner'],
        'robot_cleaner': ['로봇청소기', 'robot-cleaner', '로보락'],
    }
    
    # 약한 키워드 (모호할 수 있음)
    weak_keywords = {
        'electronics_coffee_machine': ['커피'],
        'electronics_earphone': ['이어폰', 'earphone'],
        'furniture_mattress': ['침대'],
    }
    
    # 강한 키워드 매칭
    for category, keywords in strong_keywords.items():
        if any(keyword in search_text for keyword in keywords):
            logger.info(f"[카테고리 감지 성공] '{category}' 감지됨 (high confidence)")
            return category, 'high'
    
    # 약한 키워드 매칭
    for category, keywords in weak_keywords.items():
        if any(keyword in search_text for keyword in keywords):
            logger.info(f"[카테고리 감지] '{category}' 추정됨 (low confidence)")
            return category, 'low'
    
    logger.warning(f"[카테고리 감지 실패] URL/제목/리뷰에서 카테고리를 찾을 수 없음")
    return None, 'failed'


@router.post("/start", response_model=SessionStartResponse)
async def start_session(request: SessionStartRequest):
    """대화 세션 시작"""
    logger.info(f"[세션 시작] category={request.category}")
    try:
        session_id = session_store.create_session(
            category=request.category,
            data_dir=Path("backend/data")
        )
        logger.info(f"[세션 생성 성공] session_id={session_id}, category={request.category}")
        return SessionStartResponse(
            session_id=session_id,
            message="세션이 시작되었습니다. 무엇이 궁금하신가요?"
        )
    except Exception as e:
        logger.error(f"[세션 시작 실패] category={request.category}, error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))





@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """대화 메시지 전송"""
    logger.info(f"[메시지 수신] session_id={request.session_id}, message={request.message[:50]}...")
    
    session = session_store.get_session(request.session_id)
    if not session:
        logger.warning(f"[세션 없음] session_id={request.session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        bot_turn = session.step(request.message)
        logger.info(f"[대화 진행] session_id={request.session_id}, is_final={bot_turn.is_final}, top_factors={len(bot_turn.top_factors)}")
        logger.info(f"[top_factors 상세] {bot_turn.top_factors[:5]}")
        
        # 주요 factor에 대한 관련 리뷰 조회
        related_reviews = {}
        if bot_turn.top_factors:
            logger.info(f"[관련 리뷰 조회] top_factors={[f[0] for f in bot_turn.top_factors[:3]]}")
            # 상위 3개 factor에 대한 리뷰 정보
            for factor_key, score in bot_turn.top_factors[:3]:
                review_info = session_store.get_reviews_by_factor(
                    request.session_id, 
                    factor_key, 
                    limit=5  # 3~5건 보여주기
                )
                logger.info(f"  - {factor_key}: review_info={review_info}")
                if review_info['count'] > 0:
                    related_reviews[factor_key] = review_info
                    logger.info(f"  - {factor_key}: {review_info['count']}건 발견")
        else:
            logger.warning(f"[top_factors 없음] bot_turn.top_factors가 비어있음")
        
        # 봇 메시지 구성: 실제 리뷰 문장 먼저 + 다음 질문
        bot_message = ""
        question_only = None
        
        # ✨ 새로운 흐름: related_reviews는 별도로 전달, 메시지는 질문만
        if related_reviews and not bot_turn.is_final:
            logger.info(f"[관련 리뷰 표시] keys={list(related_reviews.keys())}")
            # 프론트엔드에서 related_reviews를 렌더링하므로 메시지는 질문만
            bot_message = bot_turn.question_text
            question_only = bot_turn.question_text
        else:
            # 관련 리뷰가 없거나 최종 메시지
            bot_message = bot_turn.question_text or ""
        
        logger.info(f"[메시지 응답] session_id={request.session_id}, bot_msg_len={len(bot_message) if bot_message else 0}, is_final={bot_turn.is_final}")
        logger.info(f"[related_reviews 상태] keys={list(related_reviews.keys()) if related_reviews else 'None'}")
        
        # choices가 리스트인 경우 파이프 구분 문자열로 변환
        choices_str = None
        if bot_turn.choices and isinstance(bot_turn.choices, list):
            choices_str = '|'.join(bot_turn.choices)
        elif bot_turn.choices:
            choices_str = bot_turn.choices
        
        response_data = ChatResponse(
            session_id=request.session_id,
            bot_message=bot_message,
            is_final=bot_turn.is_final,
            top_factors=[{"factor_key": k, "score": s} for k, s in bot_turn.top_factors],
            llm_context=bot_turn.llm_context,
            related_reviews=related_reviews,
            question_id=bot_turn.question_id,
            answer_type=bot_turn.answer_type,
            choices=choices_str
        )
        
        logger.info(f"[응답 데이터] related_reviews in response: {response_data.related_reviews is not None}")
        if response_data.related_reviews:
            for key, val in response_data.related_reviews.items():
                logger.info(f"  - {key}: count={val.get('count', 0)}")
        
        return response_data
    except Exception as e:
        logger.error(f"[메시지 처리 실패] session_id={request.session_id}, error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect-reviews", response_model=CollectReviewsResponse)
async def collect_reviews(request: CollectReviewsRequest):
    """스마트스토어 리뷰 수집 (메모리 캐시 지원)"""
    cache_key = f"{request.product_url}|{request.max_reviews}|{request.sort_by_low_rating}"
    
    # 캐시 확인
    if cache_key in review_cache:
        cached = review_cache[cache_key]
        cached_session_id = cached.get('session_id')
        
        # 세션이 여전히 유효한지 확인
        if cached_session_id and session_store.get_session(cached_session_id):
            logger.info(f"[캐시 히트 + 세션 유효] url={request.product_url}, session_id={cached_session_id}")
            return CollectReviewsResponse(
                success=True,
                session_id=cached_session_id,
                reviews=cached['reviews'],
                total_count=cached['total_count'],
                product_name=cached['product_name'],
                detected_category=cached['category'],
                category_confidence=cached['confidence'],
                available_categories=get_available_categories(),
                message=f"리뷰 {cached['total_count']}건을 불러왔습니다. (캐시)"
            )
        else:
            # 세션이 만료되었지만 리뷰 데이터는 재사용 가능
            logger.info(f"[캐시 히트 + 세션 만료] url={request.product_url}, 새 세션 생성")
            
            # 리뷰 데이터를 딕셔너리로 변환
            reviews_dict = []
            for r in cached['reviews']:
                if hasattr(r, 'model_dump'):  # Pydantic 모델인 경우
                    review_data = r.model_dump()
                else:  # 이미 딕셔너리인 경우
                    review_data = r if isinstance(r, dict) else r.__dict__
                reviews_dict.append(review_data)
            
            # 캐시된 리뷰로 새 세션 생성 (리뷰 포함)
            category = cached['category']
            new_session_id = session_store.create_session(
                category=category,
                data_dir=Path("backend/data"),
                reviews=reviews_dict
            )
            
            # 캐시 업데이트 (새 session_id로)
            cached['session_id'] = new_session_id
            
            logger.info(f"[새 세션 생성] session_id={new_session_id}")
            return CollectReviewsResponse(
                success=True,
                session_id=new_session_id,
                reviews=cached['reviews'],
                total_count=cached['total_count'],
                product_name=cached['product_name'],
                detected_category=cached['category'],
                category_confidence=cached['confidence'],
                available_categories=get_available_categories(),
                message=f"리뷰 {cached['total_count']}건을 불러왔습니다. (캐시)"
            )
    
    logger.info(f"[캐시 미스] 리뷰 수집 시작 - url={request.product_url}, max={request.max_reviews}")
    try:
        # 리뷰 수집
        collector = SmartStoreCollector(
            product_url=request.product_url,
            headless=True
        )
        logger.debug(f"[콜렉터 생성] headless=True")
        
        reviews, page_title = collector.collect_reviews(
            max_reviews=request.max_reviews,
            sort_by_low_rating=request.sort_by_low_rating
        )
        logger.info(f"[리뷰 수집 완료] count={len(reviews) if reviews else 0}")
        
        # 페이지 제목에서 상품명 추출
        product_name = None
        if page_title:
            logger.info(f"[페이지 제목] {page_title}")
            # "상품명 : 쿠쿠전자" 같은 형식에서 ':' 앞부분 추출
            if ':' in page_title:
                product_name = page_title.split(':')[0].strip()
            else:
                # ':' 없으면 전체를 상품명으로 (최대 50자)
                product_name = page_title[:50].strip()
            logger.info(f"[상품명 추출] {product_name}")
        else:
            logger.warning(f"[페이지 제목 없음]")
        
        if not reviews:
            logger.warning(f"[리뷰 수집 실패] url={request.product_url}")
            return CollectReviewsResponse(
                success=False,
                message="리뷰를 수집하지 못했습니다.",
                reviews=[],
                total_count=0
            )
        
        # backend 형식으로 변환
        converted_reviews = collector.convert_to_backend_format(reviews)
        logger.debug(f"[리뷰 변환 완료] count={len(converted_reviews)}")
        
        # 중복 제거 (review_id 기준)
        seen_ids = set()
        unique_reviews = []
        for review in converted_reviews:
            review_id = review['review_id']
            if review_id not in seen_ids:
                seen_ids.add(review_id)
                unique_reviews.append(review)
        
        if len(unique_reviews) < len(converted_reviews):
            logger.info(f"[중복 제거] {len(converted_reviews)}건 → {len(unique_reviews)}건")
        
        converted_reviews = unique_reviews
        
        # 카테고리 결정: 사용자 지정 > URL+제목+리뷰 감지
        category = request.category
        confidence = 'high'
        
        if not category:
            category, confidence = detect_category(request.product_url, page_title, converted_reviews)
            logger.info(f"[카테고리 감지 결과] category={category}, confidence={confidence}")
        else:
            logger.info(f"[카테고리 사용자 지정] category={category}")
        
        # 감지 실패 시 카테고리 목록 반환
        if confidence == 'failed':
            logger.warning(f"[카테고리 감지 실패] 사용자에게 선택 요청")
            return CollectReviewsResponse(
                success=True,
                message="카테고리를 선택해주세요.",
                reviews=[],
                total_count=len(converted_reviews),
                detected_category=None,
                category_confidence='failed',
                available_categories=get_available_categories()
            )
        
        # Factor 분석 추가
        analyzer = FactorAnalyzer(category=category)
        logger.debug(f"[Factor 분석 시작] category={category}")
        
        # 각 리뷰에 factor 분석 결과 추가
        for review in converted_reviews:
            factor_matches = analyzer.analyze_review(review['text'])
            review['factor_matches'] = factor_matches
        
        logger.info(f"[Factor 분석 완료] reviews={len(converted_reviews)}")
        
        # 리뷰 응답 생성
        review_responses = []
        for r in converted_reviews:
            factor_match_models = [
                FactorMatch(
                    factor_id=fm.get('factor_id'),
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
        
        # 세션 생성 시 리뷰 데이터 함께 전달
        # Pydantic 모델을 딕셔너리로 변환
        reviews_dict = []
        for r in converted_reviews:
            review_data = r.copy()
            # factor_matches는 이미 딕셔너리 리스트 형태
            reviews_dict.append(review_data)
        
        # 세션 생성 (리뷰 포함)
        session_id = session_store.create_session(
            category=category,
            data_dir=Path("backend/data"),
            reviews=reviews_dict
        )
        logger.info(f"[세션 생성] session_id={session_id}, category={category}, reviews={len(reviews_dict)}건")
        
        response = CollectReviewsResponse(
            success=True,
            message=f"리뷰 {len(review_responses)}건을 수집했습니다.",
            session_id=session_id,
            reviews=review_responses,
            total_count=len(review_responses),
            detected_category=category,
            category_confidence=confidence,
            available_categories=get_available_categories() if confidence in ['low', 'failed'] else None,
            product_name=product_name
        )
        
        # 성공한 경우 캐시에 저장
        if len(review_cache) >= MAX_CACHE_SIZE:
            # LRU: 가장 오래된 항목 제거
            oldest_key = min(review_cache.keys(), key=lambda k: review_cache[k]['timestamp'])
            del review_cache[oldest_key]
            logger.debug(f"[캐시 정리] 가장 오래된 항목 제거: {oldest_key}")
        
        review_cache[cache_key] = {
            'session_id': session_id,
            'reviews': review_responses,
            'total_count': len(review_responses),
            'product_name': product_name,
            'category': category,
            'confidence': confidence,
            'timestamp': datetime.now()
        }
        logger.info(f"[캐시 저장] cache_size={len(review_cache)}, url={request.product_url}")
        
        return response
        
    except Exception as e:
        logger.error(f"[리뷰 수집 실패] url={request.product_url}, error={str(e)}", exc_info=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
