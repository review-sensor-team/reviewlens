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

# 상수 (settings에서 가져옴)
TOP_FACTORS_LIMIT = settings.DIALOGUE_TOP_FACTORS_LIMIT
RELATED_REVIEWS_LIMIT = settings.API_RELATED_REVIEWS_LIMIT
MIN_FINALIZE_TURNS = settings.API_MIN_FINALIZE_TURNS
MIN_STABILITY_HITS = settings.API_MIN_STABILITY_HITS

# 카테고리 캐시 (앱 시작 시 한 번만 로드)
_CATEGORIES_CACHE = None
_CATEGORY_KEYWORDS_CACHE = None


def _load_categories_from_csv() -> Tuple[List[Dict[str, str]], Dict[str, List[str]]]:
    """CSV에서 카테고리와 키워드 정보 로드"""
    import csv
    
    # 최신 버전 factor 파일 찾기
    from backend.app.collector.factor_analyzer import find_latest_versioned_file
    factor_dir = Path("backend/data/factor")
    factor_file = find_latest_versioned_file(factor_dir, "reg_factor.csv")
    
    categories_map = {}  # category -> category_name
    keywords_map = {}    # category -> [keywords]
    
    with open(factor_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row or not row.get('category'):
                continue
            
            category = row.get('category', '').strip()
            category_name = row.get('category_name', '').strip()
            product_name = row.get('product_name', '').strip()
            
            if category and category_name:
                categories_map[category] = category_name
                
                # 키워드 수집 (category_name, product_name)
                if category not in keywords_map:
                    keywords_map[category] = set()
                keywords_map[category].add(category_name.lower())
                if product_name:
                    keywords_map[category].add(product_name.lower())
    
    # 리스트로 변환
    categories = [{'key': k, 'name': v} for k, v in categories_map.items()]
    keywords = {k: list(v) for k, v in keywords_map.items()}
    
    logger.info(f"[카테고리 로드] {len(categories)}개 카테고리, {sum(len(v) for v in keywords.values())}개 키워드")
    return categories, keywords


def get_available_categories() -> List[Dict[str, str]]:
    """사용 가능한 카테고리 목록 반환 (CSV에서 동적 로드)"""
    global _CATEGORIES_CACHE
    if _CATEGORIES_CACHE is None:
        _CATEGORIES_CACHE, _ = _load_categories_from_csv()
    return _CATEGORIES_CACHE


def detect_category(url: str, page_title: Optional[str] = None, reviews: Optional[List[Dict]] = None) -> Tuple[Optional[str], str]:
    """URL, 페이지 제목, 리뷰 내용에서 카테고리 자동 감지 (CSV 기반)"""
    global _CATEGORY_KEYWORDS_CACHE
    if _CATEGORY_KEYWORDS_CACHE is None:
        _, _CATEGORY_KEYWORDS_CACHE = _load_categories_from_csv()
    
    search_text = url.lower()
    if page_title:
        search_text += " " + page_title.lower()
    
    if reviews:
        review_texts = " ".join([r.get('text', '')[:100] for r in reviews[:20]])
        search_text += " " + review_texts.lower()
    
    logger.debug(f"[카테고리 감지] search_text_length={len(search_text)}, has_reviews={bool(reviews)}")
    
    # CSV에서 로드한 키워드로 매칭
    for category, keywords in _CATEGORY_KEYWORDS_CACHE.items():
        if any(keyword in search_text for keyword in keywords):
            logger.info(f"[카테고리 감지 성공] '{category}' 감지됨 (키워드: {keywords})")
            return category, 'high'
    
    logger.warning(f"[카테고리 감지 실패] URL/제목/리뷰에서 카테고리를 찾을 수 없음")
    return None, 'failed'


def find_factor_key_by_display_name(session_store: SessionStore, session_id: str, display_name: str) -> Optional[str]:
    """display_name으로 factor_key 찾기"""
    reviews = session_store.get_reviews(session_id)
    if not reviews:
        return None
    
    # 모든 리뷰의 factor_matches를 검사하여 display_name과 일치하는 factor_key 찾기
    for review in reviews:
        for match in review.get('factor_matches', []):
            if match.get('display_name') == display_name:
                factor_key = match.get('factor_key')
                logger.info(f"[display_name 매칭] '{display_name}' -> '{factor_key}'")
                return factor_key
    
    logger.warning(f"[display_name 매칭 실패] '{display_name}'에 해당하는 factor_key를 찾을 수 없음")
    return None


def get_related_reviews(session_store: SessionStore, session_id: str, top_factors: List[Tuple[str, float]]) -> Dict[str, Dict]:
    """상위 factor에 대한 관련 리뷰 조회"""
    related_reviews = {}
    
    if not top_factors:
        logger.warning(f"[top_factors 없음] bot_turn.top_factors가 비어있음")
        return related_reviews
    
    logger.info(f"[관련 리뷰 조회] top_factors={[f[0] for f in top_factors[:TOP_FACTORS_LIMIT]]}")
    
    for factor_key, score in top_factors[:TOP_FACTORS_LIMIT]:
        # factor_key가 실제 key인지 display_name인지 확인
        actual_factor_key = factor_key
        
        # display_name일 수 있으므로 변환 시도
        if '/' in factor_key or ' ' in factor_key or any(ord(c) > 127 for c in factor_key):
            # 한글이 포함되어 있거나 슬래시가 있으면 display_name일 가능성이 높음
            converted_key = find_factor_key_by_display_name(session_store, session_id, factor_key)
            if converted_key:
                actual_factor_key = converted_key
                logger.info(f"  - factor_key 변환: '{factor_key}' -> '{actual_factor_key}'")
        
        review_info = session_store.get_reviews_by_factor(
            session_id, 
            actual_factor_key, 
            limit=RELATED_REVIEWS_LIMIT  # 설정값 사용 (5건)
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


def check_cache(review_cache: Dict, session_store: SessionStore, 
                cache_key: str, product_url: str) -> Optional[CollectReviewsResponse]:
    """캐시 확인 및 반환"""
    logger.debug(f"[캐시 확인] cache_key={cache_key}, 캐시 크기={len(review_cache)}")
    
    if cache_key not in review_cache:
        logger.info(f"[캐시 미스] url={product_url}")
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
        product_name=cached['product_name'],
        product_url=product_url
    )
    
    cached['session_id'] = new_session_id
    logger.info(f"[캐시 복원] 새 세션 생성 완료: {new_session_id}")
    
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
