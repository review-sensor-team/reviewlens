"""Chat API routes"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.dialogue.dialogue import DialogueSession
from backend.dialogue.llm_client import LLMClient
from backend.app.core.settings import settings
from ..collector import SmartStoreCollector
from ..schemas.requests import ChatRequest, SessionStartRequest, CollectReviewsRequest
from ..schemas.responses import ChatResponse, SessionStartResponse, CollectReviewsResponse, Review, FactorMatch
from ..session.session_store import SessionStore

logger = logging.getLogger("api.chat")

router = APIRouter()
session_store = SessionStore()


# 리뷰 수집 캐시 (URL을 키로 사용)
review_cache: Dict[str, Dict] = {}
MAX_CACHE_SIZE = 10

# LLM 설정 저장용 딕셔너리
session_configs: Dict[str, Any] = {}

# 상수
TOP_FACTORS_LIMIT = 3
RELATED_REVIEWS_LIMIT = 5
MIN_FINALIZE_TURNS = 3
MIN_STABILITY_HITS = 2


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


def get_related_reviews(session_id: str, top_factors: List[Tuple[str, float]]) -> Dict[str, Dict]:
    """상위 factor에 대한 관련 리뷰 조회"""
    related_reviews = {}
    
    if not top_factors:
        logger.warning(f"[top_factors 없음] bot_turn.top_factors가 비어있음")
        return related_reviews
    
    logger.info(f"[관련 리뷰 조회] top_factors={[f[0] for f in top_factors[:TOP_FACTORS_LIMIT]]}")
    
    for factor_key, score in top_factors[:TOP_FACTORS_LIMIT]:
        review_info = session_store.get_reviews_by_factor(
            session_id, 
            factor_key, 
            limit=RELATED_REVIEWS_LIMIT
        )
        logger.info(f"  - {factor_key}: review_info={review_info}")
        
        if review_info['count'] > 0:
            related_reviews[factor_key] = review_info
            logger.info(f"  - {factor_key}: {review_info['count']}건 발견")
    
    return related_reviews


def format_bot_message(bot_turn, related_reviews: Dict) -> str:
    """봇 메시지 포맷팅"""
    if related_reviews and not bot_turn.is_final:
        logger.info(f"[관련 리뷰 표시] keys={list(related_reviews.keys())}")
        return bot_turn.question_text
    else:
        return bot_turn.question_text or ""


def get_stability_info(turn_count: int, stability_hits: int) -> Optional[str]:
    """분석 안정성 정보 반환"""
    if turn_count < MIN_FINALIZE_TURNS:
        return None
    
    if stability_hits >= 3:
        return "요인 분석이 충분히 수렴했습니다. 분석을 완료하시겠어요?"
    elif stability_hits >= MIN_STABILITY_HITS:
        return "분석 준비가 거의 완료되었습니다."
    else:
        return "조금 더 대화하면 더 정확한 분석이 가능합니다."


def format_choices(choices) -> Optional[str]:
    """choices를 문자열로 변환"""
    if not choices:
        return None
    
    if isinstance(choices, list):
        return '|'.join(choices)
    return choices


def check_cache(cache_key: str, product_url: str) -> Optional[CollectReviewsResponse]:
    """캐시 확인 및 반환"""
    if cache_key not in review_cache:
        return None
    
    cached = review_cache[cache_key]
    cached_session_id = cached.get('session_id')
    
    # 세션이 유효한 경우
    if cached_session_id and session_store.get_session(cached_session_id):
        logger.info(f"[캐시 히트 + 세션 유효] url={product_url}, session_id={cached_session_id}")
        return CollectReviewsResponse(
            success=True,
            session_id=cached_session_id,
            reviews=cached['reviews'],
            total_count=cached['total_count'],
            product_name=cached['product_name'],
            detected_category=cached['category'],
            category_confidence=cached['confidence'],
            available_categories=get_available_categories(),
            suggested_factors=cached.get('suggested_factors', []),
            message=f"리뷰 {cached['total_count']}건을 불러왔습니다. (캐시)"
        )
    
    # 세션이 만료된 경우 - 새 세션 생성
    logger.info(f"[캐시 히트 + 세션 만료] url={product_url}, 새 세션 생성")
    
    # 리뷰 데이터를 딕셔너리로 변환
    reviews_dict = [
        r.model_dump() if hasattr(r, 'model_dump') else (r if isinstance(r, dict) else r.__dict__)
        for r in cached['reviews']
    ]
    
    # 캐시된 리뷰로 새 세션 생성
    new_session_id = session_store.create_session(
        category=cached['category'],
        data_dir=Path("backend/data"),
        reviews=reviews_dict,
        product_name=cached['product_name']
    )
    
    # 캐시 업데이트
    cached['session_id'] = new_session_id
    logger.info(f"[새 세션 생성] session_id={new_session_id}")
    
    # LLM 설정 저장 (캐시 복원 시)
    provider = settings.LLM_PROVIDER
    session_configs[new_session_id] = {
        "provider": provider,
        "model_name": settings.get_model_name(provider),
        "api_key": settings.get_api_key(provider)
    }
    
    return CollectReviewsResponse(
        success=True,
        session_id=new_session_id,
        reviews=cached['reviews'],
        total_count=cached['total_count'],
        product_name=cached['product_name'],
        detected_category=cached['category'],
        category_confidence=cached['confidence'],
        available_categories=get_available_categories(),
        suggested_factors=cached.get('suggested_factors', []),
        message=f"리뷰 {cached['total_count']}건을 불러왔습니다. (캐시)"
    )


def extract_product_name(page_title: Optional[str]) -> Optional[str]:
    """페이지 제목에서 상품명 추출"""
    if not page_title:
        logger.warning(f"[페이지 제목 없음]")
        return None
    
    logger.info(f"[페이지 제목] {page_title}")
    
    # "상품명 : 쿠쿠전자" 같은 형식에서 ':' 앞부분 추출
    if ':' in page_title:
        product_name = page_title.split(':')[0].strip()
    else:
        # ':' 없으면 전체를 상품명으로 (최대 50자)
        product_name = page_title[:50].strip()
    
    logger.info(f"[상품명 추출] {product_name}")
    return product_name


def determine_category(request_category: Optional[str], product_url: str, page_title: Optional[str], 
                      reviews: Optional[List[Dict]] = None) -> Tuple[Optional[str], str]:
    """카테고리 결정 (사용자 지정 > URL+제목+리뷰 감지)"""
    if request_category:
        logger.info(f"[카테고리 사용자 지정] category={request_category}")
        return request_category, 'high'
    
    category, confidence = detect_category(product_url, page_title, reviews)
    logger.info(f"[카테고리 감지 결과] category={category}, confidence={confidence}")
    return category, confidence


def create_review_responses(reviews_with_factors: List[Dict]) -> List[Review]:
    """리뷰 응답 모델 리스트 생성 (Factor 분석 결과 포함)"""
    review_responses = []
    
    for r in reviews_with_factors:
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
    
    return review_responses


def aggregate_factors(reviews: List[Review]) -> List[str]:
    """리뷰에서 후회 팩터 집계하여 상위 5개 반환"""
    from collections import Counter
    
    factor_counter = Counter()
    
    for review in reviews:
        if review.factor_matches:
            for match in review.factor_matches:
                factor_counter[match.display_name] += 1
    
    # 가장 많이 언급된 상위 5개 팩터 추출
    top_5_factors = [factor for factor, count in factor_counter.most_common(5)]
    
    logger.info(f"[후회 팩터 집계] total_factors={len(factor_counter)}, top_5={top_5_factors}")
    return top_5_factors


def update_cache(cache_key: str, session_id: str, review_responses: List[Review], 
                product_name: Optional[str], category: str, confidence: str, 
                suggested_factors: List[str]) -> None:
    """캐시 업데이트 (LRU 방식)"""
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
        'suggested_factors': suggested_factors,
        'timestamp': datetime.now()
    }
    logger.info(f"[캐시 저장] cache_size={len(review_cache)}")


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

        #feature/api LLMClient
        api_key = settings.get_api_key(request.provider)
        if not api_key:
            raise HTTPException(status_code=400, detail=f"{request.provider} API Key가 설정되지 않았습니다.")
        
        session_configs[session_id] = { 
            "provider": request.provider,
            "model_name": request.model_name,
            "api_key": api_key
        }

        return SessionStartResponse(
            session_id=session_id,
            #feature/api 초기 메시지에 LLM 정보 포함
            message=f"세션이 시작되었습니다. 무엇이 궁금하신가요? LLM 정보: ({request.provider}/{request.model_name})"
        )
    except Exception as e:
        logger.error(f"[세션 시작 실패] category={request.category}, error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))





@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """대화 메시지 전송"""
    logger.info(f"[메시지 수신] session_id={request.session_id}, message={request.message[:50]}..., request_finalize={request.request_finalize}")
    
    # 세션 확인
    session = session_store.get_session(request.session_id)
    if not session:
        logger.warning(f"[세션 없음] session_id={request.session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    
    # LLMClient 설정 확인
    config = session_configs.get(request.session_id)
    if not config:
        raise HTTPException(status_code=404, detail="LLM 설정이 만료되었습니다. /start를 다시 해주세요.")
    
    try:
        # 대화 진행 또는 종료
        if request.request_finalize:
            logger.info(f"[사용자 요청 종료] session_id={request.session_id}")
            bot_turn = session.finalize_now()
        else:
            bot_turn = session.step(request.message)
        
        logger.info(f"[대화 진행] session_id={request.session_id}, is_final={bot_turn.is_final}, top_factors={len(bot_turn.top_factors)}")
        logger.info(f"[top_factors 상세] {bot_turn.top_factors[:5]}")
        
        # 관련 리뷰 조회
        related_reviews = get_related_reviews(request.session_id, bot_turn.top_factors)
        
        # 봇 메시지 구성
        bot_message = format_bot_message(bot_turn, related_reviews)
        logger.info(f"[메시지 응답] session_id={request.session_id}, bot_msg_len={len(bot_message) if bot_message else 0}, is_final={bot_turn.is_final}")
        logger.info(f"[related_reviews 상태] keys={list(related_reviews.keys()) if related_reviews else 'None'}")
        
        # 응답 데이터 구성
        response_data = ChatResponse(
            session_id=request.session_id,
            bot_message=bot_message,
            is_final=bot_turn.is_final,
            has_analysis=bot_turn.has_analysis,
            top_factors=[{"factor_key": k, "score": s} for k, s in bot_turn.top_factors],
            llm_context=bot_turn.llm_context,
            related_reviews=related_reviews,
            question_id=bot_turn.question_id,
            answer_type=bot_turn.answer_type,
            choices=format_choices(bot_turn.choices),
            can_finalize=session.turn_count >= MIN_FINALIZE_TURNS and session.stability_hits >= MIN_STABILITY_HITS,
            turn_count=session.turn_count,
            stability_info=get_stability_info(session.turn_count, session.stability_hits)
        )
        
        logger.info(f"[응답 데이터] related_reviews in response: {response_data.related_reviews is not None}")
        if response_data.related_reviews:
            for key, val in response_data.related_reviews.items():
                logger.info(f"  - {key}: count={val.get('count', 0)}")
        
        return response_data
        
    except Exception as e:
        logger.error(f"[메시지 처리 실패] session_id={request.session_id}, error={str(e)}", exc_info=True)
        import traceback
        logger.error(f"[스택트레이스]\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect-reviews", response_model=CollectReviewsResponse)
async def collect_reviews(request: CollectReviewsRequest):
    """스마트스토어 리뷰 수집 (메모리 캐시 지원)"""
    cache_key = f"{request.product_url}|{request.max_reviews}|{request.sort_by_low_rating}"
    
    # 캐시 확인
    cached_response = check_cache(cache_key, request.product_url)
    if cached_response:
        return cached_response
    
    logger.info(f"[캐시 미스] 리뷰 수집 시작 - url={request.product_url}, max={request.max_reviews}")
    
    try:
        collector = SmartStoreCollector(product_url=request.product_url, headless=True)
        
        # 카테고리 결정을 위한 사전 수집 (메타데이터만)
        reviews_preview, page_title = collector.collect_reviews(
            max_reviews=min(20, request.max_reviews),
            sort_by_low_rating=request.sort_by_low_rating
        )
        
        # 상품명 추출
        product_name = extract_product_name(page_title)
        
        # 카테고리 결정
        preview_converted = collector.convert_to_backend_format(reviews_preview) if reviews_preview else []
        category, confidence = determine_category(
            request.category, request.product_url, page_title, preview_converted
        )
        
        # 카테고리 감지 실패 시 사용자 선택 요청
        if confidence == 'failed':
            logger.warning(f"[카테고리 감지 실패] 사용자에게 선택 요청")
            return CollectReviewsResponse(
                success=True,
                message="카테고리를 선택해주세요.",
                reviews=[],
                total_count=0,
                detected_category=None,
                category_confidence='failed',
                available_categories=get_available_categories()
            )
        
        # 리뷰 수집 및 Factor 분석 (전체 파이프라인 - collector가 담당)
        logger.info(f"[전체 수집 시작] category={category}")
        result = collector.collect_and_analyze(
            category=category,
            max_reviews=request.max_reviews,
            sort_by_low_rating=request.sort_by_low_rating
        )
        
        # 리뷰 수집 실패 처리
        if result['total_count'] == 0:
            logger.warning(f"[리뷰 수집 실패] url={request.product_url}")
            return CollectReviewsResponse(
                success=False,
                message="리뷰를 수집하지 못했습니다.",
                reviews=[],
                total_count=0
            )
        
        # Review 응답 모델 생성
        review_responses = create_review_responses(result['reviews'])
        
        # 후회 팩터 집계 (상위 5개)
        suggested_factors = aggregate_factors(review_responses)
        
        # 세션 생성
        session_id = session_store.create_session(
            category=category,
            data_dir=Path("backend/data"),
            reviews=result['reviews'],
            product_name=product_name
        )
        logger.info(f"[세션 생성] session_id={session_id}, category={category}, reviews={result['total_count']}건")
        
        # LLM 설정 저장 (.env의 LLM_PROVIDER 사용)
        provider = settings.LLM_PROVIDER
        session_configs[session_id] = {
            "provider": provider,
            "model_name": settings.get_model_name(provider),
            "api_key": settings.get_api_key(provider)
        }
        logger.info(f"[LLM 설정 저장] session_id={session_id}, provider={provider}")
        
        # 응답 생성
        response = CollectReviewsResponse(
            success=True,
            message=f"리뷰 {len(review_responses)}건을 수집했습니다.",
            session_id=session_id,
            reviews=review_responses,
            total_count=len(review_responses),
            detected_category=category,
            category_confidence=confidence,
            available_categories=get_available_categories() if confidence in ['low', 'failed'] else None,
            product_name=product_name,
            suggested_factors=suggested_factors
        )
        
        # 캐시 업데이트
        update_cache(cache_key, session_id, review_responses, product_name, category, confidence, suggested_factors)
        
        return response
        
    except Exception as e:
        logger.error(f"[리뷰 수집 실패] url={request.product_url}, error={str(e)}", exc_info=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
