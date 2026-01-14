"""Helper functions for routes_chat"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from collections import Counter

from ..schemas.responses import CollectReviewsResponse, Review, FactorMatch
from ..session.session_store import SessionStore
from backend.app.core.settings import settings

logger = logging.getLogger("api.chat")

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
    """URL, 페이지 제목, 리뷰 내용에서 카테고리 자동 감지"""
    search_text = url.lower()
    if page_title:
        search_text += " " + page_title.lower()
    
    if reviews:
        review_texts = " ".join([r.get('text', '')[:100] for r in reviews[:20]])
        search_text += " " + review_texts.lower()
    
    logger.debug(f"[카테고리 감지] search_text_length={len(search_text)}, has_reviews={bool(reviews)}")
    
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
    
    weak_keywords = {
        'electronics_coffee_machine': ['커피'],
        'electronics_earphone': ['이어폰', 'earphone'],
        'furniture_mattress': ['침대'],
    }
    
    for category, keywords in strong_keywords.items():
        if any(keyword in search_text for keyword in keywords):
            logger.info(f"[카테고리 감지 성공] '{category}' 감지됨 (high confidence)")
            return category, 'high'
    
    for category, keywords in weak_keywords.items():
        if any(keyword in search_text for keyword in keywords):
            logger.info(f"[카테고리 감지] '{category}' 추정됨 (low confidence)")
            return category, 'low'
    
    logger.warning(f"[카테고리 감지 실패] URL/제목/리뷰에서 카테고리를 찾을 수 없음")
    return None, 'failed'


def get_related_reviews(session_store: SessionStore, session_id: str, top_factors: List[Tuple[str, float]]) -> Dict[str, Dict]:
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


def check_cache(review_cache: Dict, session_store: SessionStore, session_configs: Dict, 
                cache_key: str, product_url: str) -> Optional[CollectReviewsResponse]:
    """캐시 확인 및 반환"""
    if cache_key not in review_cache:
        return None
    
    cached = review_cache[cache_key]
    cached_session_id = cached.get('session_id')
    
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
    
    logger.info(f"[캐시 히트 + 세션 만료] url={product_url}, 새 세션 생성")
    
    reviews_dict = [
        r.model_dump() if hasattr(r, 'model_dump') else (r if isinstance(r, dict) else r.__dict__)
        for r in cached['reviews']
    ]
    
    new_session_id = session_store.create_session(
        category=cached['category'],
        data_dir=Path("backend/data"),
        reviews=reviews_dict,
        product_name=cached['product_name']
    )
    
    cached['session_id'] = new_session_id
    logger.info(f"[새 세션 생성] session_id={new_session_id}")
    
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
    
    if ':' in page_title:
        product_name = page_title.split(':')[0].strip()
    else:
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
    factor_counter = Counter()
    
    for review in reviews:
        if review.factor_matches:
            for match in review.factor_matches:
                factor_counter[match.display_name] += 1
    
    top_5_factors = [factor for factor, count in factor_counter.most_common(5)]
    
    logger.info(f"[후회 팩터 집계] total_factors={len(factor_counter)}, top_5={top_5_factors}")
    return top_5_factors


def update_cache(review_cache: Dict, MAX_CACHE_SIZE: int, cache_key: str, session_id: str, 
                review_responses: List[Review], product_name: Optional[str], category: str, 
                confidence: str, suggested_factors: List[str]) -> None:
    """캐시 업데이트 (LRU 방식)"""
    if len(review_cache) >= MAX_CACHE_SIZE:
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
