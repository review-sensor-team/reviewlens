"""Review API Router - Clean Architecture Version (Phase 4)

리뷰 수집 및 분석 API
"""
import logging
import random
from typing import Optional
from pathlib import Path
import pandas as pd
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ...services.review_service import ReviewService
from ...core.settings import settings
from ...infra.observability.metrics import (
    dialogue_turns_total, 
    track_errors, 
    user_journey_stage_total,
    dialogue_completions_total
)
from ...adapters.persistence.reg.store import load_csvs, parse_factors
from ...usecases.dialogue.session import DialogueSession

logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(prefix="/api/v2/reviews", tags=["reviews"])

# Service 인스턴스
_review_service: Optional[ReviewService] = None

# 세션 캐시 (메모리)
_session_cache: dict = {}  # {session_id: {scored_df, factors, category, product_name}}

# 공통 상수 import
from ...usecases.dialogue.constants import CATEGORY_FALLBACK_QUESTIONS, DEFAULT_FALLBACK_QUESTIONS


def get_data_dir() -> Path:
    """데이터 디렉토리 경로 반환"""
    return Path(__file__).resolve().parent.parent.parent.parent / "data"


def get_review_service() -> ReviewService:
    """ReviewService 의존성"""
    global _review_service
    if _review_service is None:
        _review_service = ReviewService(data_dir=get_data_dir())
    return _review_service


# === Request/Response Models ===

class CollectReviewsRequest(BaseModel):
    """리뷰 수집 요청"""
    product_id: str
    vendor: str = "smartstore"
    max_reviews: int = 100


class CollectReviewsResponse(BaseModel):
    """리뷰 수집 응답"""
    product_id: str
    vendor: str
    review_count: int
    message: str


class AnalyzeReviewsRequest(BaseModel):
    """리뷰 분석 요청"""
    product_id: str
    category: str
    top_k: int = 3


class AnalyzeReviewsResponse(BaseModel):
    """리뷰 분석 응답"""
    product_id: str
    review_count: int
    factor_count: int
    top_factors: list[tuple[str, float]]


class AnswerQuestionRequest(BaseModel):
    """질문 답변 요청"""
    answer: str
    question_id: Optional[str] = None
    factor_key: Optional[str] = None


class RateResponseRequest(BaseModel):
    """LLM 응답 평가 요청"""
    response_file: str  # llm_response_default_20260118_123456.json
    rating: int  # 1-5 별점
    strategy: Optional[str] = None  # 다중 전략인 경우 어떤 전략인지
    feedback: Optional[str] = None  # 선택적 피드백


class RateResponseResponse(BaseModel):
    """LLM 응답 평가 응답"""
    success: bool
    message: str
    response_file: str
    rating: int


# === Helper Functions ===

def _check_convergence(session_data: dict, min_turns: int = 3) -> bool:
    """수렴 조건 체크
    
    Args:
        session_data: 세션 데이터
        min_turns: 최소 질문 답변 횟수
        
    Returns:
        bool: 수렴 여부
    """
    turn_count = len(session_data.get("question_history", []))
    fallback_count = sum(1 for q in session_data.get("question_history", []) if q.get("is_fallback"))
    
    is_converged = (turn_count >= min_turns) or (fallback_count >= 1)
    logger.info(f"수렴 체크: turn_count={turn_count}, fallback_count={fallback_count}, is_converged={is_converged}")
    
    return is_converged


def _get_current_factor_next_question(
    questions_df,
    current_factor_key: str,
    current_factor_id: int,
    asked_ids: set,
    asked_texts: set
) -> Optional[dict]:
    """현재 factor의 다음 질문 찾기
    
    Args:
        questions_df: 질문 DataFrame
        current_factor_key: 현재 factor key
        current_factor_id: 현재 factor ID
        asked_ids: 이미 물어본 질문 ID 집합
        asked_texts: 이미 물어본 질문 텍스트 집합
        
    Returns:
        dict: 다음 질문 정보 또는 None
    """
    # factor_id로 정확히 매칭되는 질문만 찾기
    all_questions = questions_df[questions_df['factor_id'] == current_factor_id]
    logger.info(f"Factor '{current_factor_key}' (factor_id={current_factor_id}) 전체 질문: {len(all_questions)}개")
    
    # 아직 묻지 않은 질문 필터링
    related_questions = all_questions[
        (~all_questions['question_id'].isin(asked_ids)) &
        (~all_questions['question_text'].isin(asked_texts))
    ]
    
    logger.info(f"아직 묻지 않은 질문: {len(related_questions)}개")
    
    if len(related_questions) > 0:
        next_q = related_questions.iloc[0]
        question = {
            "question_id": next_q['question_id'],
            "question_text": next_q['question_text'],
            "answer_type": next_q['answer_type'],
            "choices": next_q['choices'].split('|') if next_q.get('choices') else [],
            "next_factor_hint": next_q.get('next_factor_hint', ''),
            "factor_key": current_factor_key
        }
        logger.info(f"현재 factor '{current_factor_key}'의 다음 질문: question_id={next_q['question_id']}")
        return question
    
    return None


def _filter_unasked_questions(questions_df, asked_ids: set, asked_texts: set):
    """아직 묻지 않은 질문 필터링"""
    return questions_df[
        (~questions_df['question_id'].isin(asked_ids)) &
        (~questions_df['question_text'].isin(asked_texts))
    ]

def _build_question_dict(question_row, factor_key: str) -> dict:
    """질문 행에서 질문 딕셔너리 생성"""
    return {
        "question_id": question_row['question_id'],
        "question_text": question_row['question_text'],
        "answer_type": question_row['answer_type'],
        "choices": question_row['choices'].split('|') if question_row.get('choices') else [],
        "next_factor_hint": question_row.get('next_factor_hint', ''),
        "factor_key": factor_key
    }

def _get_next_factor_question(
    questions_df,
    next_factor_key: str,
    asked_ids: set,
    asked_texts: set
) -> Optional[dict]:
    """next_factor_hint로 다음 factor의 질문 찾기
    
    Args:
        questions_df: 질문 DataFrame
        next_factor_key: 다음 factor key
        asked_ids: 이미 물어본 질문 ID 집합
        asked_texts: 이미 물어본 질문 텍스트 집합
        
    Returns:
        dict: 다음 질문 정보 또는 None
    """
    next_factor_questions = questions_df[questions_df['factor_key'] == next_factor_key]
    
    if len(next_factor_questions) == 0:
        logger.info(f"CSV에서 next_factor_key '{next_factor_key}'를 찾을 수 없음")
        return None
    
    next_unasked = _filter_unasked_questions(next_factor_questions, asked_ids, asked_texts)
    next_factor_id = int(next_factor_questions.iloc[0]['factor_id'])
    logger.info(f"다음 factor '{next_factor_key}' (factor_id={next_factor_id}) 질문: {len(next_factor_questions)}개, 미질문: {len(next_unasked)}개")
    
    if len(next_unasked) > 0:
        next_q = next_unasked.iloc[0]
        question = _build_question_dict(next_q, next_factor_key)
        logger.info(f"다음 factor '{next_factor_key}'로 이동: question_id={next_q['question_id']}")
        return question
    
    logger.info(f"다음 factor '{next_factor_key}'의 질문도 모두 소진됨")
    return None


def _get_fallback_question(session_data: dict, current_factor_key: str) -> Optional[dict]:
    """Fallback 질문 선택
    
    Args:
        session_data: 세션 데이터
        current_factor_key: 현재 factor key
        
    Returns:
        dict: Fallback 질문 정보 또는 None
    """
    category = session_data.get("category", "")
    fallback_questions = CATEGORY_FALLBACK_QUESTIONS.get(category, DEFAULT_FALLBACK_QUESTIONS)
    
    # 이미 물어본 fallback 질문 추적
    if "asked_fallback_questions" not in session_data:
        session_data["asked_fallback_questions"] = []
    
    asked_fallbacks = set(session_data["asked_fallback_questions"])
    unasked_fallbacks = [q for q in fallback_questions if q not in asked_fallbacks]
    
    if unasked_fallbacks:
        fb_q = random.choice(unasked_fallbacks)
        question = {
            "question_id": None,
            "question_text": fb_q,
            "answer_type": "no_choice",
            "choices": [],
            "next_factor_hint": "",
            "factor_key": current_factor_key,
            "is_fallback": True
        }
        session_data["asked_fallback_questions"].append(fb_q)
        logger.info(f"Fallback 질문 랜덤 선택: {fb_q}")
        return question
    
    return None


def _find_next_question(session_data: dict, questions_df, current_factor_key: str, current_factor: any) -> Optional[dict]:
    """다음 질문 찾기 (전체 로직)
    
    Args:
        session_data: 세션 데이터
        questions_df: 질문 DataFrame
        current_factor_key: 현재 factor key
        current_factor: 현재 factor 객체
        
    Returns:
        dict: 다음 질문 정보 또는 None
    """
    asked_ids = {q["question_id"] for q in session_data["question_history"] if q.get("question_id")}
    asked_texts = {q["question_text"] for q in session_data["question_history"] if q.get("question_text")}
    
    # 1. 현재 factor의 다음 질문 확인
    next_question = _get_current_factor_next_question(
        questions_df, current_factor_key, current_factor.factor_id,
        asked_ids, asked_texts
    )
    
    if next_question:
        return next_question
    
    # 2. 현재 factor 소진 - next_factor_hint 확인
    logger.info(f"Factor '{current_factor_key}' 질문 소진 - next_factor_hint 확인")
    
    prev_question = session_data.get("current_question", {})
    next_factor_key = prev_question.get('next_factor_hint', '')
    logger.info(f"방금 답변한 질문의 next_factor_hint: '{next_factor_key}'")
    
    if next_factor_key:
        next_question = _get_next_factor_question(
            questions_df, next_factor_key,
            asked_ids, asked_texts
        )
        
        if next_question:
            return next_question
    
    # 3. fallback 질문 사용
    logger.info(f"다음 factor 없음 또는 질문 소진 - fallback 질문 사용")
    return _get_fallback_question(session_data, current_factor_key)


# ============================================================================
# Helper Functions for get_factor_reviews
# ============================================================================

def _extract_matched_sentences(text: str, anchor_terms: list, max_length: int = 100) -> tuple[list, list]:
    """anchor_term이 포함된 문장 추출
    
    Args:
        text: 리뷰 텍스트
        anchor_terms: 매칭할 키워드 리스트
        max_length: 문장 최대 길이
        
    Returns:
        (matched_sentences, matched_terms) 튜플
    """
    sentences = text.split('.')
    matched_sentences = []
    matched_terms = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence) < 10:
            continue
            
        for term in anchor_terms:
            if term in sentence:
                # 키워드 앞뒤 적당히 자르기
                if len(sentence) > max_length:
                    term_pos = sentence.find(term)
                    start = max(0, term_pos - 30)
                    end = min(len(sentence), term_pos + len(term) + 50)
                    sentence = '...' + sentence[start:end] + '...'
                
                matched_sentences.append(sentence)
                if term not in matched_terms:
                    matched_terms.append(term)
                break
    
    return matched_sentences, matched_terms


def _build_review_samples(matched_df, target_factor, limit: int = 5) -> list:
    """매칭된 리뷰에서 샘플 추출 (중복 제거)
    
    Args:
        matched_df: 매칭된 리뷰 DataFrame
        target_factor: Factor 객체
        limit: 최대 리뷰 개수
        
    Returns:
        리뷰 샘플 리스트
    """
    reviews = []
    seen_texts = set()
    
    for _, row in matched_df.iterrows():
        text = row['text']
        
        # 중복 체크
        if text in seen_texts:
            continue
        
        # 키워드 매칭 문장 추출
        matched_sentences, matched_terms = _extract_matched_sentences(
            text, 
            target_factor.anchor_terms
        )
        
        # 매칭된 문장이 없으면 스킵
        if not matched_sentences:
            continue
        
        reviews.append({
            "rating": int(row.get('rating', 0)),
            "sentences": matched_sentences[:3],  # 최대 3문장
            "matched_terms": matched_terms
        })
        
        seen_texts.add(text)
        
        if len(reviews) >= limit:
            break
    
    return reviews


def _load_factor_questions(factor_key: str) -> list:
    """Factor에 해당하는 질문 로드
    
    Args:
        factor_key: Factor key
        
    Returns:
        질문 리스트
    """
    _, _, questions_df = load_csvs(get_data_dir())
    
    related_questions = questions_df[
        questions_df['factor_key'] == factor_key
    ].to_dict('records')
    
    return [{
        "question_id": q['question_id'],
        "question_text": q['question_text'],
        "answer_type": q['answer_type'],
        "choices": q['choices'].split('|') if q.get('choices') else [],
        "next_factor_hint": q.get('next_factor_hint', '')
    } for q in related_questions]


def _calculate_term_stats(reviews: list, anchor_terms: dict) -> dict:
    """매칭된 용어 통계 계산"""
    term_stats = {}
    for term in anchor_terms:
        count = sum(1 for r in reviews if term in r.get('matched_terms', []))
        if count > 0:
            term_stats[term] = count
    return term_stats

def _create_review_summary_message(factor_display_name: str, term_stats: dict) -> str:
    """리뷰 요약 메시지 생성"""
    term_summary = ", ".join([
        f"'{term}' {count}건" 
        for term, count in sorted(term_stats.items(), key=lambda x: -x[1])
    ])
    return f'"{factor_display_name}"과 관련된 리뷰를 {term_summary}을 찾았어요.'

def _add_to_dialogue_history(session_data: dict, user_message: str, assistant_message: str):
    """대화 히스토리에 메시지 추가"""
    if "dialogue_history" not in session_data:
        session_data["dialogue_history"] = []
    
    session_data["dialogue_history"].append({"role": "user", "message": user_message})
    session_data["dialogue_history"].append({"role": "assistant", "message": assistant_message})

def _update_dialogue_with_factor_selection(session_id: str, target_factor, reviews: list, anchor_terms: dict, questions: list):
    """Factor 선택 시 대화 히스토리 업데이트
    
    Args:
        session_id: 세션 ID
        target_factor: Factor 객체
        reviews: 리뷰 샘플 리스트
        anchor_terms: anchor_term 카운트 딕셔너리
        questions: 질문 리스트
    """
    global _session_cache
    
    if session_id not in _session_cache:
        return
    
    session_data = _session_cache[session_id]
    
    # 매칭된 용어 통계 및 요약 메시지 생성
    term_stats = _calculate_term_stats(reviews, anchor_terms)
    review_summary = _create_review_summary_message(target_factor.display_name, term_stats)
    
    # 대화 히스토리 업데이트
    _add_to_dialogue_history(session_data, target_factor.display_name, review_summary)
    
    # 첫 번째 질문을 current_question에 저장
    if questions:
        session_data["current_question"] = questions[0]
        logger.info(f"current_question 저장: {questions[0].get('question_text', '')[:50]}")
    
    logger.info(f"대화 히스토리 업데이트: {target_factor.display_name} 선택")


# ============================================================================
# Helper Functions for analyze_product
# ============================================================================

def _load_product_info(product_name: str) -> tuple:
    """Factor CSV에서 상품 정보 로드
    
    Args:
        product_name: 상품명
        
    Returns:
        (category, category_name) 튜플
        
    Raises:
        HTTPException: 파일 없음 또는 상품 없음
    """
    factor_csv_path = get_data_dir() / "factor" / "reg_factor_v4.csv"
    if not factor_csv_path.exists():
        raise HTTPException(status_code=404, detail="Factor CSV 파일을 찾을 수 없습니다")
    
    df = pd.read_csv(factor_csv_path)
    
    product_rows = df[df['product_name'] == product_name]
    if product_rows.empty:
        raise HTTPException(status_code=404, detail=f"'{product_name}' 상품을 찾을 수 없습니다")
    
    return product_rows.iloc[0]['category'], product_rows.iloc[0]['category_name']


def _load_review_data(category: str, service: ReviewService):
    """리뷰 파일 로드 및 정규화
    
    Args:
        category: 카테고리
        service: ReviewService 인스턴스
        
    Returns:
        정규화된 리뷰 DataFrame
        
    Raises:
        HTTPException: 리뷰 파일 없음
    """

    # 📊 사용자 여정: 리뷰 수집 단계 진입
    user_journey_stage_total.labels(
        stage="review_collection",
        action="enter",
        category=category
    ).inc()

    loader = service._get_review_loader()
    review_df = None
    vendor = "smartstore"
    
    if loader:
        review_df = loader.load_by_category(category=category, latest=True)
        if review_df is not None:
            logger.info(f"리뷰 로드 성공: category={category} ({len(review_df)}건)")
    
    if review_df is None or len(review_df) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"카테고리 '{category}'의 리뷰 파일을 찾을 수 없습니다"
        )
    
    return service.normalize_reviews(review_df, vendor=vendor)


def _extract_suggested_factors(top_factors: list, factors: list) -> list:
    """Top factors에서 API 응답용 suggested factors 추출
    
    Args:
        top_factors: [(factor_key, score), ...] 리스트
        factors: Factor 객체 리스트
        
    Returns:
        Suggested factors 리스트 (dict)
    """
    factor_map = {f.factor_key: f for f in factors}
    return [
        {
            "factor_id": factor_map[factor_key].factor_id,
            "factor_key": factor_key,
            "display_name": factor_map[factor_key].display_name
        }
        for factor_key, score in top_factors
    ]

def _create_initial_dialogue(product_name: str, review_count: int, suggested_factors: list) -> list:
    """초기 대화 내역 생성
    
    Args:
        product_name: 상품명
        review_count: 리뷰 개수
        suggested_factors: Suggested factors 리스트
        
    Returns:
        초기 대화 내역 (role, message 포함)
    """
    factor_list_text = "\n".join([
        f"- {f['display_name']}"
        for f in suggested_factors
    ])
    
    analysis_message = f"{product_name} {review_count}건의 리뷰에서 후회 포인트를 분석했어요. 아래 항목 중 궁금한 걸 선택해주세요!"
    
    return [
        {
            "role": "assistant",
            "message": f"{analysis_message}\n{factor_list_text}"
        }
    ]

def _cache_session(session_id: str, session_cache_data: dict) -> None:
    """세션 데이터를 메모리 캐시에 저장
    
    Args:
        session_id: 세션 ID
        session_cache_data: 캐싱할 세션 데이터
    """
    global _session_cache
    _session_cache[session_id] = session_cache_data
    logger.info(f"상품 분석 완료: {session_cache_data['product_name']} - 세션 캐싱 완료")

def _create_session_data(session_id: str, product_name: str, category: str, category_name: str, 
                         normalized_df, analysis: dict, factors: list) -> dict:
    """세션 데이터 생성 및 캐싱
    
    Args:
        session_id: 세션 ID
        product_name: 상품명
        category: 카테고리
        category_name: 카테고리 표시명
        normalized_df: 정규화된 리뷰 DataFrame
        analysis: 분석 결과
        factors: Factor 리스트
        
    Returns:
        API 응답용 딕셔너리
    """
    suggested_factors = _extract_suggested_factors(analysis["top_factors"], factors)
    initial_dialogue = _create_initial_dialogue(product_name, len(normalized_df), suggested_factors)
    
    session_cache_data = {
        "scored_df": analysis["scored_reviews_df"],
        "normalized_df": normalized_df,
        "factors": factors,
        "top_factors": analysis["top_factors"],
        "category": category,
        "product_name": product_name,
        "dialogue_history": initial_dialogue
    }
    
    _cache_session(session_id, session_cache_data)
    
    return {
        "session_id": session_id,
        "suggested_factors": suggested_factors,
        "product_name": product_name,
        "total_count": len(normalized_df),
        "category": category,
        "category_name": category_name
    }


# === API Endpoints ===

@router.post("/collect", response_model=CollectReviewsResponse)
@track_errors(error_type='api_error', component='collect_reviews')
async def collect_reviews(
    request: CollectReviewsRequest,
    review_service: ReviewService = Depends(get_review_service)
):
    """리뷰 수집
    
    Service 레이어의 collect_reviews()를 호출하여 리뷰를 수집합니다.
    """
    logger.info(f"리뷰 수집 요청: product={request.product_id}, vendor={request.vendor}")
    
    try:
        # Service 레이어 호출
        result = review_service.collect_reviews(
            product_id=request.product_id,
            vendor=request.vendor,
            max_reviews=request.max_reviews
        )
        
        logger.info(f"리뷰 수집 완료: {result['review_count']}건")
        
        return CollectReviewsResponse(
            product_id=result["product_id"],
            vendor=result["vendor"],
            review_count=result["review_count"],
            message=f"{result['review_count']}건의 리뷰를 수집했습니다."
        )
    except Exception as e:
        logger.error(f"리뷰 수집 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"리뷰 수집 실패: {str(e)}")


@router.post("/analyze", response_model=AnalyzeReviewsResponse)
@track_errors(error_type='api_error', component='analyze_reviews')
async def analyze_reviews(
    request: AnalyzeReviewsRequest,
    review_service: ReviewService = Depends(get_review_service)
):
    """리뷰 분석
    
    Service 레이어를 호출하여 리뷰를 분석하고 top factors를 반환합니다.
    """
    logger.info(f"리뷰 분석 요청: product={request.product_id}, category={request.category}")
    
    try:
        # 1. 리뷰 수집
        collect_result = review_service.collect_reviews(
            product_id=request.product_id,
            vendor="smartstore"
        )
        reviews_df = collect_result["reviews_df"]
        
        # 2. 정규화
        normalized_df = review_service.normalize_reviews(reviews_df, vendor="smartstore")
        
        # 3. Factors 로드
        data_dir = get_data_dir()
        _, factors_df, _ = load_csvs(data_dir)
        all_factors = parse_factors(factors_df)
        factors = [f for f in all_factors if f.category == request.category]
        
        # 4. 분석
        analysis = review_service.analyze_reviews(
            reviews_df=normalized_df,
            factors=factors,
            top_k=request.top_k
        )
        
        logger.info(f"리뷰 분석 완료: {len(analysis['top_factors'])}개 top factors")
        
        return AnalyzeReviewsResponse(
            product_id=request.product_id,
            review_count=analysis["review_count"],
            factor_count=len(analysis["factor_scores"]),
            top_factors=analysis["top_factors"]
        )
    except Exception as e:
        logger.error(f"리뷰 분석 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"리뷰 분석 실패: {str(e)}")


@router.get("/products")
async def get_available_products(
    service: ReviewService = Depends(get_review_service)
):
    # 📊 사용자 여정: 상품 선택 단계 진입
    user_journey_stage_total.labels(
        stage="product_selection",
        action="enter",
        category="unknown"
    ).inc()

    """사용 가능한 상품 목록 조회
    
    USE_PRODUCT_SELECTION=True일 때 사용
    
    Returns:
        { products: [{ product_id, product_name, category, review_count }] }
    """
    try:
        logger.info("상품 목록 조회 요청")
        products = service.get_available_products()
        
        return {
            "success": True,
            "count": len(products),
            "products": products
        }
    except Exception as e:
        logger.error(f"상품 목록 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"상품 목록 조회 실패: {str(e)}")


@router.get("/config")
async def get_app_config():
    """앱 설정 조회
    
    Returns:
        - use_product_selection: 상품 선택 모드 사용 여부
        - mode: 'product_selection' 또는 'url_input'
        - strategy_names: 전략 이름 한글 매핑
    """
    return {
        "success": True,
        "use_product_selection": settings.USE_PRODUCT_SELECTION,
        "mode": "product_selection" if settings.USE_PRODUCT_SELECTION else "url_input",
        "strategy_names": settings.STRATEGY_KOREAN_NAMES
    }


@router.post("/analyze-product")
@track_errors(error_type='api_error', component='analyze_product')
async def analyze_product(
    product_name: str,
    service: ReviewService = Depends(get_review_service)
):
    """상품명으로 리뷰 분석 시작
    
    Factor CSV에서 상품을 찾고, 해당 상품의 리뷰 파일을 로드하여 분석합니다.
    
    Args:
        product_name: 상품명 (예: "네스프레소 버츄오플러스")
        
    Returns:
        {
            "session_id": str,
            "suggested_factors": List[str],
            "product_name": str,
            "total_count": int,
            "category": str,
            "category_name": str
        }
    """
    try:
        logger.info(f"상품 분석 요청: {product_name}")
        
        # 1. 상품 정보 로드 (helper 함수)
        category, category_name = _load_product_info(product_name)
        
        # 2. 리뷰 데이터 로드 및 정규화 (helper 함수)
        normalized_df = _load_review_data(category, service)
        
        # 3. Factor 로드 (해당 카테고리만)
        _, factors_df, _ = load_csvs(get_data_dir())
        all_factors = parse_factors(factors_df)
        factors = [f for f in all_factors if f.category == category]
        
        if not factors:
            raise HTTPException(
                status_code=404,
                detail=f"'{category_name}' 카테고리의 Factor를 찾을 수 없습니다"
            )
        
        # 4. 리뷰 분석
        analysis = service.analyze_reviews(
            reviews_df=normalized_df,
            factors=factors,
            top_k=5,
            save_results=False,
            category=category,
            product_id=product_name
        )
        
        # 📊 사용자 여정: 리뷰 수집 완료 & 대화 시작 진입
        user_journey_stage_total.labels(
            stage="review_collection",
            action="complete",
            category=category
        ).inc()
        user_journey_stage_total.labels(
            stage="dialogue_start",
            action="enter",
            category=category
        ).inc()
        
        # 5. 세션 데이터 생성 및 캐싱 (helper 함수)
        session_id = f"session-{category}-{hash(product_name) % 100000}"
        return _create_session_data(
            session_id, product_name, category, category_name,
            normalized_df, analysis, factors
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"상품 분석 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"상품 분석 중 오류가 발생했습니다: {str(e)}")


@router.get("/factor-reviews/{session_id}/{factor_key}")
@track_errors(error_type='api_error', component='get_factor_reviews')
async def get_factor_reviews(
    session_id: str,
    factor_key: str,
    limit: int = 5,
    service: ReviewService = Depends(get_review_service)
):
    """Factor별 관련 리뷰 및 질문 조회
    
    Args:
        session_id: 세션 ID (analyze-product 응답에서 받은 값)
        factor_key: Factor key (예: noise_loud, crema_quality)
        limit: 리뷰 개수 (기본값: 5)
        
    Returns:
        {
            "factor_key": str,
            "display_name": str,
            "total_count": int,
            "anchor_terms": dict,  # {term: count}
            "reviews": [...],
            "questions": [...]
        }
    """
    try:
        logger.info(f"Factor 리뷰 조회: session_id={session_id}, factor_key={factor_key}, limit={limit}")
        
        # 1. 세션 데이터 검증
        global _session_cache
        if session_id not in _session_cache:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        session_data = _session_cache[session_id]
        scored_df = session_data.get("scored_df")
        factors = session_data.get("factors")
        
        if scored_df is None or factors is None:
            raise HTTPException(status_code=500, detail="세션 데이터가 손상되었습니다")
        
        # 2. Factor 찾기
        target_factor = next((f for f in factors if f.factor_key == factor_key), None)
        if not target_factor:
            raise HTTPException(status_code=404, detail=f"Factor '{factor_key}'를 찾을 수 없습니다")
        
        # 3. 매칭된 리뷰 필터링
        score_col = f"score_{factor_key}"
        if score_col not in scored_df.columns:
            raise HTTPException(status_code=404, detail=f"Score 컬럼 '{score_col}'을 찾을 수 없습니다")
        
        matched_df = scored_df[scored_df[score_col] > 0].copy()
        matched_df = matched_df.sort_values(score_col, ascending=False)
        logger.info(f"매칭된 리뷰: {len(matched_df)}건")
        
        # 4. anchor_term별 카운트
        anchor_terms = {}
        for term in target_factor.anchor_terms:
            count = matched_df['text'].str.contains(term, case=False, na=False).sum()
            if count > 0:
                anchor_terms[term] = int(count)
        
        # 5. 리뷰 샘플 생성 (helper 함수 사용)
        reviews = _build_review_samples(matched_df, target_factor, limit)
        
        # 6. 질문 로드 (helper 함수 사용)
        questions = _load_factor_questions(factor_key)
        
        logger.info(f"리뷰 조회 완료: {len(reviews)}건, 질문 {len(questions)}개")
        
        # 7. 대화 히스토리 업데이트 (helper 함수 사용)
        _update_dialogue_with_factor_selection(session_id, target_factor, reviews, anchor_terms, questions)
        
        return {
            "factor_key": factor_key,
            "display_name": target_factor.display_name,
            "total_count": len(matched_df),
            "anchor_terms": anchor_terms,
            "reviews": reviews,
            "questions": questions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Factor 리뷰 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"리뷰 조회 중 오류가 발생했습니다: {str(e)}")


@router.post("/answer-question/{session_id}")
@track_errors(error_type='api_error', component='answer_question')
async def answer_question(
    session_id: str,
    request: AnswerQuestionRequest,
    service: ReviewService = Depends(get_review_service)
):
    """질문에 답변하고 다음 질문 또는 분석 결과 조회
    
    Args:
        session_id: 세션 ID
        request: 질문 답변 요청 (answer, question_id, factor_key)
        answer: 사용자 답변
        question_id: 질문 ID (선택)
        factor_key: 현재 factor_key (선택)
        
    Returns:
        {
            "next_question": {
                "question_id": str,
                "question_text": str,
                "answer_type": str,
                "choices": [str],
                "next_factor_hint": str
            },
            "is_converged": bool,  # 수렴 조건 달성 여부
            "analysis": {...}  # is_converged=true일 때만 제공
        }
    """
    try:
        print(f"[DEBUG] 질문 답변 처리: session_id={session_id}, answer={request.answer}, question_id={request.question_id}, factor_key={request.factor_key}")
        logger.info(f"질문 답변 처리: session_id={session_id}, answer={request.answer}, question_id={request.question_id}, factor_key={request.factor_key}")
        
        # 1. 세션 캐시에서 데이터 가져오기
        global _session_cache
        if session_id not in _session_cache:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        session_data = _session_cache[session_id]
        
        # 2. 질문 히스토리 추가 (세션에 저장)
        if "question_history" not in session_data:
            session_data["question_history"] = []
        
        # 이전 질문 정보 가져오기 (세션에 저장된 current_question 사용)
        prev_question = session_data.get("current_question", {})
        question_text = prev_question.get("question_text", "")
        
        session_data["question_history"].append({
            "question_id": request.question_id,
            "question_text": question_text,  # 질문 텍스트도 저장
            "answer": request.answer,
            "factor_key": request.factor_key
        })
        
        # dialogue_history에도 추가
        if "dialogue_history" not in session_data:
            session_data["dialogue_history"] = []
        
        session_data["dialogue_history"].append({"role": "assistant", "message": question_text})
        session_data["dialogue_history"].append({"role": "user", "message": request.answer})
        
        turn_count = len(session_data["question_history"])
        logger.info(f"질문 히스토리: {turn_count}턴, 대화 히스토리: {len(session_data['dialogue_history'])}개")
        
        # 메트릭 기록: 대화 턴 증가
        category = session_data.get("category", "unknown")
        dialogue_turns_total.labels(category=category).inc()
        
        # 📊 사용자 여정: 대화 진행 중
        user_journey_stage_total.labels(
            stage="dialogue_active",
            action="enter",
            category=category
        ).inc()
        
        # 3. 수렴 조건 체크
        is_converged = _check_convergence(session_data, min_turns=3)
        
        # 4. 수렴되지 않았으면 다음 질문 로드
        if not is_converged:
            _, _, questions_df = load_csvs(get_data_dir())
            
            # factor_key 결정
            current_factor_key = request.factor_key or (session_data.get("factors", [])[0].factor_key if session_data.get("factors") else None)
            if not current_factor_key:
                raise HTTPException(status_code=400, detail="factor_key를 찾을 수 없습니다")
            
            # 세션의 factor 중에서 현재 factor_key에 해당하는 factor 찾기
            current_factor = next((f for f in session_data.get("factors", []) if f.factor_key == current_factor_key), None)
            if not current_factor:
                raise HTTPException(status_code=400, detail=f"세션에 factor_key '{current_factor_key}'가 없습니다")
            
            # 다음 질문 찾기 (helper 함수 사용)
            next_question = _find_next_question(session_data, questions_df, current_factor_key, current_factor)
            
            if next_question:
                # 세션에 현재 질문 저장
                session_data["current_question"] = next_question
                
                logger.info(f"다음 질문: {next_question.get('question_id', 'fallback')}")
                
                return {
                    "next_question": next_question,
                    "related_reviews": [],
                    "review_message": "",
                    "is_converged": False,
                    "turn_count": turn_count
                }
            else:
                # 더 이상 질문이 없으면 수렴으로 간주
                logger.info(f"더 이상 질문이 없음 - 수렴 처리")
                is_converged = True
        
        # 5. 수렴되었으면 분석 결과 생성 (LLM 호출)
        if is_converged:
            logger.info(f"수렴 조건 달성 - LLM 분석 시작")
            
            # DialogueSession 생성 (dialogue_history 전달)
            normalized_df = session_data.get("normalized_df")
            if normalized_df is None:
                # 기존 세션 호환성: scored_df 사용 (fallback)
                logger.warning("normalized_df가 세션에 없음 - scored_df 사용 (기존 세션 호환)")
                normalized_df = session_data.get("scored_df")
            
            dialogue_session = DialogueSession(
                category=session_data.get("category"),
                data_dir=get_data_dir(),
                reviews_df=normalized_df,  # 원본 normalized_df 전달 (LLM 분석용)
                product_name=session_data.get("product_name", "이 제품")
            )
            
            # 세션의 dialogue_history 복원 (초기 안내 + 키워드 선택 + 질문-답변 모두 포함)
            dialogue_session.dialogue_history = session_data.get("dialogue_history", [])
            
            dialogue_session.turn_count = len(session_data.get("question_history", []))
            # (세션에 저장된 top_factors 사용)
            top_factors = session_data.get("top_factors", [])[:3]  # (factor_key, score) 튜플 리스트
            
            # LLM 분석 생성
            llm_context = dialogue_session._generate_analysis(top_factors)
            
            logger.info(f"LLM 분석 완료 - llm_summary 길이: {len(llm_context.get('llm_summary', ''))}")
            
            # 📊 사용자 여정: 대화 완료
            user_journey_stage_total.labels(
                stage="dialogue_complete",
                action="complete",
                category=category
            ).inc()
            
            # 📊 대화 세션 완료 메트릭
            dialogue_completions_total.labels(category=category).inc()
            
            return {
                "next_question": None,
                "is_converged": True,
                "turn_count": turn_count,
                "analysis": llm_context  # LLM 분석 결과 전체 반환
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"질문 답변 처리 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"질문 답변 처리 중 오류가 발생했습니다: {str(e)}")


@router.post("/rate-response", response_model=RateResponseResponse)
def rate_llm_response(
    request: RateResponseRequest
) -> RateResponseResponse:
    """LLM 응답 평가
    
    사용자가 LLM 응답에 대해 별점(1-5)을 매기면,
    해당 응답 파일에 평가 정보를 추가합니다.
    
    Args:
        request: 평가 요청
            - response_file: 응답 파일명
            - rating: 1-5 별점
            - strategy: (옵션) 전략 이름
            - feedback: (옵션) 텍스트 피드백
    
    Returns:
        평가 결과
    """
    try:
        import json
        from datetime import datetime
        
        # 파일 경로 구성
        out_dir = Path("out")
        response_path = out_dir / request.response_file
        
        if not response_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"응답 파일을 찾을 수 없습니다: {request.response_file}"
            )
        
        # 별점 범위 검증
        if not (1 <= request.rating <= 5):
            raise HTTPException(
                status_code=400,
                detail="별점은 1-5 사이여야 합니다"
            )
        
        # 기존 파일 읽기
        with open(response_path, 'r', encoding='utf-8') as f:
            response_data = json.load(f)
        
        # 평가 정보 추가
        if "_user_rating" not in response_data:
            response_data["_user_rating"] = {}
        
        rating_data = {
            "rating": request.rating,
            "rated_at": datetime.now().isoformat(),
        }
        
        if request.strategy:
            rating_data["strategy"] = request.strategy
        
        if request.feedback:
            rating_data["feedback"] = request.feedback
        
        # 전략별로 평가 저장 (다중 전략 지원)
        if request.strategy:
            response_data["_user_rating"][request.strategy] = rating_data
        else:
            response_data["_user_rating"]["default"] = rating_data
        
        # 파일 업데이트
        with open(response_path, 'w', encoding='utf-8') as f:
            json.dump(response_data, f, ensure_ascii=False, indent=2)
        
        logger.info(
            f"[평가 저장] 파일={request.response_file}, "
            f"전략={request.strategy or 'default'}, 별점={request.rating}"
        )
        
        return RateResponseResponse(
            success=True,
            message="평가가 저장되었습니다",
            response_file=request.response_file,
            rating=request.rating
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"평가 저장 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"평가 저장 중 오류가 발생했습니다: {str(e)}"
        )
