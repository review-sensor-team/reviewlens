"""Review API Router - Clean Architecture Version (Phase 4)

리뷰 수집 및 분석 API
"""
import logging
import random
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ...services.review_service import ReviewService
from ...core.settings import settings

logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(prefix="/api/v2/reviews", tags=["reviews"])

# Service 인스턴스
_review_service: Optional[ReviewService] = None

# 세션 캐시 (메모리)
_session_cache: dict = {}  # {session_id: {scored_df, factors, category, product_name}}


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


# === API Endpoints ===

@router.post("/collect", response_model=CollectReviewsResponse)
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
async def analyze_reviews(
    request: AnalyzeReviewsRequest,
    review_service: ReviewService = Depends(get_review_service)
):
    """리뷰 분석
    
    Service 레이어를 호출하여 리뷰를 분석하고 top factors를 반환합니다.
    """
    logger.info(f"리뷰 분석 요청: product={request.product_id}, category={request.category}")
    
    try:
        from ...domain.reg.store import load_csvs, parse_factors
        
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
    """
    return {
        "success": True,
        "use_product_selection": settings.USE_PRODUCT_SELECTION,
        "mode": "product_selection" if settings.USE_PRODUCT_SELECTION else "url_input"
    }


@router.post("/analyze-product")
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
            "category": str
        }
    """
    try:
        logger.info(f"상품 분석 요청: {product_name}")
        
        # 1. Factor CSV에서 상품 정보 찾기
        factor_csv_path = get_data_dir() / "factor" / "reg_factor_v4.csv"
        if not factor_csv_path.exists():
            raise HTTPException(status_code=404, detail="Factor CSV 파일을 찾을 수 없습니다")
        
        import pandas as pd
        df = pd.read_csv(factor_csv_path)
        
        # 상품명으로 필터링
        product_rows = df[df['product_name'] == product_name]
        if product_rows.empty:
            raise HTTPException(status_code=404, detail=f"'{product_name}' 상품을 찾을 수 없습니다")
        
        # 첫 번째 매칭 상품 정보 추출
        category = product_rows.iloc[0]['category']
        category_name = product_rows.iloc[0]['category_name']
        
        # 2. 리뷰 파일 찾기 (Factory Pattern - 통합 인터페이스)
        loader = service._get_review_loader()
        review_df = None
        vendor = "smartstore"
        
        if loader:
            # category 기반으로 리뷰 로드 (CSV/JSON/URL 자동 처리)
            review_df = loader.load_by_category(category=category, latest=True)
            
            if review_df is not None:
                logger.info(f"리뷰 로드 성공: category={category} ({len(review_df)}건)")
        
        if review_df is None or len(review_df) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"'{product_name}' 상품의 리뷰 파일을 찾을 수 없습니다"
            )
        
        # 3. 리뷰 정규화
        normalized_df = service.normalize_reviews(review_df, vendor=vendor)
        
        # 4. Factor 로드 (해당 카테고리만)
        from ...domain.reg.store import load_csvs, parse_factors
        _, factors_df, _ = load_csvs(get_data_dir())
        all_factors = parse_factors(factors_df)
        factors = [f for f in all_factors if f.category == category]
        
        if not factors:
            raise HTTPException(
                status_code=404,
                detail=f"'{category_name}' 카테고리의 Factor를 찾을 수 없습니다"
            )
        
        # 5. 리뷰 분석
        analysis = service.analyze_reviews(
            reviews_df=normalized_df,
            factors=factors,
            top_k=5,
            save_results=False,
            category=category,
            product_id=product_name
        )
        
        # 6. Top factors 추출 (객체 배열로 반환)
        factor_map = {f.factor_key: f for f in factors}
        suggested_factors = [
            {
                "factor_id": factor_map[factor_key].factor_id,
                "factor_key": factor_key,
                "display_name": factor_map[factor_key].display_name
            }
            for factor_key, score in analysis["top_factors"]
        ]
        
        # 7. 세션 ID 생성 및 캐싱
        session_id = f"session-{category}-{hash(product_name) % 100000}"
        
        # 초기 대화 내역 생성 (분석 안내 + 키워드 리스트)
        factor_list_text = "\n".join([
            f"- {f['display_name']}"
            for f in suggested_factors
        ])
        
        # 분석 안내 메시지 생성
        review_count = len(normalized_df)
        analysis_message = f"{product_name} {review_count}건의 리뷰에서 후회 포인트를 분석했어요. 아래 항목 중 궁금한 걸 선택해주세요!"
        
        initial_dialogue = [
            {
                "role": "assistant",
                "message": f"{analysis_message}\n{factor_list_text}"
            }
        ]
        
        # 세션 데이터 캠싱 (factor-reviews API에서 사용)
        global _session_cache
        _session_cache[session_id] = {
            "scored_df": analysis["scored_reviews_df"],
            "normalized_df": normalized_df,  # 원본 리뷰 DataFrame (LLM 분석용)
            "factors": factors,
            "top_factors": analysis["top_factors"],  # (factor_key, score) 튜플 리스트
            "category": category,
            "product_name": product_name,
            "dialogue_history": initial_dialogue  # 초기 대화 내역
        }
        
        logger.info(f"상품 분석 완료: {product_name} - {len(suggested_factors)}개 후회 포인트 (세션 캐싱 완료)")
        
        return {
            "session_id": session_id,
            "suggested_factors": suggested_factors,
            "product_name": product_name,
            "total_count": len(normalized_df),
            "category": category,
            "category_name": category_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"상품 분석 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"상품 분석 중 오류가 발생했습니다: {str(e)}")


@router.get("/factor-reviews/{session_id}/{factor_key}")
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
            "reviews": [
                {
                    "rating": int,
                    "sentences": [str],
                    "matched_terms": [str]
                }
            ],
            "questions": [
                {
                    "question_id": str,
                    "question_text": str,
                    "answer_type": str,
                    "choices": [str],
                    "next_factor_hint": str
                }
            ]
        }
    """
    try:
        logger.info(f"Factor 리뷰 조회: session_id={session_id}, factor_key={factor_key}, limit={limit}")
        
        # 1. 세션 캐시에서 데이터 가져오기
        global _session_cache
        if session_id not in _session_cache:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        session_data = _session_cache[session_id]
        scored_df = session_data.get("scored_df")
        factors = session_data.get("factors")
        
        if scored_df is None or factors is None:
            raise HTTPException(status_code=500, detail="세션 데이터가 손상되었습니다")
        
        # 2. Factor 정보 찾기
        target_factor = next((f for f in factors if f.factor_key == factor_key), None)
        if not target_factor:
            raise HTTPException(status_code=404, detail=f"Factor '{factor_key}'를 찾을 수 없습니다")
        
        # 3. Factor 매칭된 리뷰 필터링
        score_col = f"score_{factor_key}"
        if score_col not in scored_df.columns:
            raise HTTPException(status_code=404, detail=f"Score 컬럼 '{score_col}'을 찾을 수 없습니다")
        
        # 점수가 0보다 큰 리뷰만 필터링
        matched_df = scored_df[scored_df[score_col] > 0].copy()
        matched_df = matched_df.sort_values(score_col, ascending=False)
        
        logger.info(f"매칭된 리뷰: {len(matched_df)}건")
        
        # 4. anchor_term별 카운트 집계
        anchor_terms = {}
        for term in target_factor.anchor_terms:
            count = matched_df['text'].str.contains(term, case=False, na=False).sum()
            if count > 0:
                anchor_terms[term] = int(count)
        
        # 5. 리뷰 샘플 추출 (limit개) - 중복 제거 및 키워드 문장 추출
        reviews = []
        seen_texts = set()  # 중복 방지
        
        for _, row in matched_df.iterrows():
            text = row['text']
            
            # 중복 체크 (같은 텍스트는 한 번만)
            if text in seen_texts:
                continue
            
            # anchor_term이 포함된 문장만 추출
            sentences = text.split('.')
            matched_sentences = []
            matched_terms_in_review = []
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence or len(sentence) < 10:
                    continue
                    
                for term in target_factor.anchor_terms:
                    if term in sentence:
                        # 키워드 앞뒤 적당히 자르기 (최대 100자)
                        if len(sentence) > 100:
                            term_pos = sentence.find(term)
                            start = max(0, term_pos - 30)
                            end = min(len(sentence), term_pos + len(term) + 50)
                            sentence = '...' + sentence[start:end] + '...'
                        
                        matched_sentences.append(sentence)
                        if term not in matched_terms_in_review:
                            matched_terms_in_review.append(term)
                        break
            
            # 매칭된 문장이 없으면 스킵
            if not matched_sentences:
                continue
            
            reviews.append({
                "rating": int(row.get('rating', 0)),
                "sentences": matched_sentences[:3],  # 최대 3문장
                "matched_terms": matched_terms_in_review
            })
            
            seen_texts.add(text)
            
            # limit 도달 시 종료
            if len(reviews) >= limit:
                break
        
        # 6. 관련 질문 로드
        from ...domain.reg.store import load_csvs
        _, _, questions_df = load_csvs(get_data_dir())
        
        related_questions = questions_df[
            questions_df['factor_key'] == factor_key
        ].to_dict('records')
        
        questions = [{
            "question_id": q['question_id'],
            "question_text": q['question_text'],
            "answer_type": q['answer_type'],
            "choices": q['choices'].split('|') if q.get('choices') else [],
            "next_factor_hint": q.get('next_factor_hint', '')
        } for q in related_questions]
        
        logger.info(f"리뷰 조회 완료: {len(reviews)}건, 질문 {len(questions)}개")
        
        # dialogue_history에 키워드 선택 및 리뷰 요약 추가
        if session_id in _session_cache:
            # 매칭된 용어 통계 생성
            term_stats = {}
            for term in anchor_terms:
                count = sum(1 for r in reviews if term in r.get('matched_terms', []))
                if count > 0:
                    term_stats[term] = count
            
            # 리뷰 요약 메시지 생성
            term_summary = ", ".join([f"'{term}' {count}건" for term, count in sorted(term_stats.items(), key=lambda x: -x[1])])
            review_summary = f'"{target_factor.display_name}"과 관련된 리뷰를 {term_summary}을 찾았어요.'
            
            # 세션 dialogue_history 업데이트
            if "dialogue_history" not in _session_cache[session_id]:
                _session_cache[session_id]["dialogue_history"] = []
            
            _session_cache[session_id]["dialogue_history"].append({"role": "user", "message": target_factor.display_name})
            _session_cache[session_id]["dialogue_history"].append({"role": "assistant", "message": review_summary})
            
            # 첫 번째 질문을 current_question에 저장 (프론트엔드에서 표시할 질문)
            if questions:
                _session_cache[session_id]["current_question"] = questions[0]
                logger.info(f"current_question 저장: {questions[0].get('question_text', '')[:50]}")
            
            logger.info(f"대화 히스토리 업데이트: {target_factor.display_name} 선택")
        
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
        
        # 3. 수렴 조건 체크
        # - MIN_TURNS 이상 or
        # - Fallback 질문을 1회 이상 답변한 경우
        from ...core.settings import settings
        MIN_TURNS = 3  # 최소 질문 답변 횟수
        
        # Fallback 질문 답변 횟수 확인
        fallback_count = sum(1 for q in session_data["question_history"] if q.get("is_fallback"))
        
        is_converged = (turn_count >= MIN_TURNS) or (fallback_count >= 1)
        
        logger.info(f"수렴 체크: turn_count={turn_count}, fallback_count={fallback_count}, is_converged={is_converged}")
        
        # 4. 수렴되지 않았으면 다음 질문 로드
        if not is_converged:
            # question CSV에서 다음 질문 찾기
            from ...domain.reg.store import load_csvs
            _, _, questions_df = load_csvs(get_data_dir())
            
            # 현재 factor_key와 관련된 질문 중 아직 묻지 않은 질문 찾기
            asked_ids = {q["question_id"] for q in session_data["question_history"] if q.get("question_id")}
            asked_texts = {q["question_text"] for q in session_data["question_history"] if q.get("question_text")}
            print(f"[DEBUG] Asked question IDs: {asked_ids}")
            print(f"[DEBUG] Asked question texts: {asked_texts}")
            logger.info(f"Asked question IDs: {asked_ids}")
            
            # factor_key 결정
            current_factor_key = request.factor_key or (session_data.get("factors", [])[0].factor_key if session_data.get("factors") else None)
            if not current_factor_key:
                raise HTTPException(status_code=400, detail="factor_key를 찾을 수 없습니다")
            
            # 세션의 factor 중에서 현재 factor_key에 해당하는 factor 찾기
            current_factor = next((f for f in session_data.get("factors", []) if f.factor_key == current_factor_key), None)
            if not current_factor:
                raise HTTPException(status_code=400, detail=f"세션에 factor_key '{current_factor_key}'가 없습니다")
            
            # factor_id로 정확히 매칭되는 질문만 찾기 (카테고리 혼동 방지)
            all_questions = questions_df[questions_df['factor_id'] == current_factor.factor_id]
            print(f"[DEBUG] Factor '{current_factor_key}' (factor_id={current_factor.factor_id}) 전체 질문: {len(all_questions)}개")
            logger.info(f"Factor '{current_factor_key}' (factor_id={current_factor.factor_id}) 전체 질문: {len(all_questions)}개")
            
            # 아직 묻지 않은 질문 필터링 (ID와 텍스트 둘 다 체크 - 중복 텍스트 방지)
            related_questions = all_questions[
                (~all_questions['question_id'].isin(asked_ids)) &
                (~all_questions['question_text'].isin(asked_texts))
            ]
            print(f"[DEBUG] 아직 묻지 않은 질문: {len(related_questions)}개")
            print(f"[DEBUG] All question IDs in factor: {all_questions['question_id'].tolist()}")
            print(f"[DEBUG] Related (unasked) question IDs: {related_questions['question_id'].tolist()}")
            logger.info(f"아직 묻지 않은 질문: {len(related_questions)}개")
            logger.info(f"All question IDs in factor: {all_questions['question_id'].tolist()}")
            logger.info(f"Related (unasked) question IDs: {related_questions['question_id'].tolist()}")
            
            next_question = None
            
            if len(related_questions) == 0:
                # 해당 factor의 질문이 모두 소진되면 next_factor_hint를 참고하여 다음 factor로 이동
                logger.info(f"Factor '{current_factor_key}' 질문 소진 - next_factor_hint 확인")
                
                # 마지막 질문의 next_factor_hint 가져오기
                last_question = all_questions.iloc[-1] if len(all_questions) > 0 else None
                next_factor_key = last_question.get('next_factor_hint', '') if last_question is not None else ''
                
                logger.info(f"next_factor_hint: '{next_factor_key}'")
                
                # next_factor_hint가 있으면 해당 factor의 질문 찾기
                if next_factor_key:
                    # 세션의 factors에서 next_factor_key에 해당하는 factor 찾기
                    next_factor = next((f for f in session_data.get("factors", []) if f.factor_key == next_factor_key), None)
                    
                    if next_factor:
                        # 다음 factor의 질문 중 아직 묻지 않은 질문 찾기
                        next_factor_questions = questions_df[questions_df['factor_id'] == next_factor.factor_id]
                        next_unasked = next_factor_questions[
                            (~next_factor_questions['question_id'].isin(asked_ids)) &
                            (~next_factor_questions['question_text'].isin(asked_texts))
                        ]
                        
                        logger.info(f"다음 factor '{next_factor_key}' (factor_id={next_factor.factor_id}) 질문: {len(next_factor_questions)}개, 미질문: {len(next_unasked)}개")
                        
                        if len(next_unasked) > 0:
                            # 다음 factor의 첫 번째 질문 선택
                            next_q = next_unasked.iloc[0]
                            next_question = {
                                "question_id": next_q['question_id'],
                                "question_text": next_q['question_text'],
                                "answer_type": next_q['answer_type'],
                                "choices": next_q['choices'].split('|') if next_q.get('choices') else [],
                                "next_factor_hint": next_q.get('next_factor_hint', ''),
                                "factor_key": next_factor_key
                            }
                            logger.info(f"다음 factor '{next_factor_key}'로 이동: question_id={next_q['question_id']}")
                
                # next_factor_hint가 없거나 다음 factor에도 질문이 없으면 fallback 질문 사용
                if next_question is None:
                    logger.info(f"다음 factor 없음 또는 질문 소진 - fallback 질문 사용")
                    
                    # 카테고리별 fallback 질문
                category = session_data.get("category", "")
                category_questions = {
                    'mattress': [
                        "평소 어떤 자세로 주로 주무시나요? (옆으로/바로/엎드려)",
                        "현재 사용 중인 매트리스에서 가장 불편한 점이 무엇인가요?",
                        "매트리스 구매 시 가장 중요하게 생각하는 요소는 무엇인가요? (지지력/푹신함/통풍/내구성 등)"
                    ],
                    'chair': [
                        "하루에 몇 시간 정도 앉아서 작업하시나요?",
                        "현재 의자에서 가장 불편한 부위는 어디인가요? (허리/목/엉덩이/팔걸이 등)",
                        "의자 구매 시 가장 중요하게 생각하는 요소는 무엇인가요? (쿠션/등받이/높이조절/내구성 등)"
                    ],
                    'bedding_robot': [
                        "주로 어떤 종류의 침구류를 청소하실 예정인가요? (이불/베개/매트리스 등)",
                        "알레르기나 천식이 있으신가요?",
                        "청소 주기는 얼마나 자주 하실 계획인가요?"
                    ],
                    'bedding_cleaner': [
                        "주로 어떤 종류의 침구류를 청소하실 예정인가요? (이불/베개/매트리스 등)",
                        "알레르기나 천식이 있으신가요?",
                        "침구청소기 구매 시 가장 중요한 요소는 무엇인가요? (흡입력/무게/소음/UV 등)"
                    ],
                    'bookshelf': [
                        "어느 위치에 설치 예정이신가요? (거실/방/서재 등)",
                        "주로 어떤 물건을 보관하실 예정인가요? (책/소품/서류 등)",
                        "책장 구매 시 가장 중요한 요소는 무엇인가요? (수납력/디자인/안정성/조립 편의성 등)"
                    ],
                    'coffee_machine': [
                        "하루에 커피를 몇 잔 정도 드시나요?",
                        "어떤 종류의 커피를 선호하시나요? (에스프레소/아메리카노/라떼 등)",
                        "커피머신 구매 시 가장 중요한 요소는 무엇인가요? (맛/편의성/세척/소음 등)"
                    ],
                    'desk': [
                        "주로 어떤 작업을 하실 예정인가요? (컴퓨터 작업/공부/그림 등)",
                        "책상을 놓을 공간의 크기는 어느 정도인가요?",
                        "책상 구매 시 가장 중요한 요소는 무엇인가요? (크기/수납/높이조절/내구성 등)"
                    ],
                    'earbuds': [
                        "주로 어떤 상황에서 사용하실 예정인가요? (출퇴근/운동/업무 등)",
                        "귀 모양이 특이하거나 이어폰이 잘 빠지는 편인가요?",
                        "이어폰 구매 시 가장 중요한 요소는 무엇인가요? (음질/착용감/배터리/노이즈캔슬링 등)"
                    ],
                    'humidifier': [
                        "사용하실 공간의 크기는 어느 정도인가요?",
                        "소음에 민감하신 편인가요? (수면 중 사용 여부)",
                        "가습기 구매 시 가장 중요한 요소는 무엇인가요? (가습량/소음/세척편의성/디자인 등)"
                    ],
                    'induction': [
                        "주로 어떤 요리를 하시나요? (볶음/찌개/구이 등)",
                        "인덕션 사용 경험이 있으신가요?",
                        "인덕션 구매 시 가장 중요한 요소는 무엇인가요? (화력/소음/세척/안전성 등)"
                    ]
                }
                
                # 기본 fallback 질문
                default_fallbacks = [
                    "이 제품을 주로 어떤 상황에서 사용하실 예정인가요?",
                    "비슷한 제품을 사용하면서 불편했던 점이 있다면 무엇인가요?",
                    "제품 구매 시 가장 중요하게 생각하는 요소는 무엇인가요?"
                ]
                
                fallback_questions = category_questions.get(category, default_fallbacks)
                
                # 이미 물어본 fallback 질문 추적 (세션에 저장된 리스트 사용)
                if "asked_fallback_questions" not in session_data:
                    session_data["asked_fallback_questions"] = []
                
                asked_fallbacks = set(session_data["asked_fallback_questions"])
                
                # 아직 묻지 않은 fallback 질문 찾기
                unasked_fallbacks = [q for q in fallback_questions if q not in asked_fallbacks]
                
                if unasked_fallbacks:
                    # 랜덤하게 선택
                    fb_q = random.choice(unasked_fallbacks)
                    next_question = {
                        "question_id": None,  # fallback은 ID 없음
                        "question_text": fb_q,
                        "answer_type": "no_choice",
                        "choices": [],
                        "next_factor_hint": "",
                        "factor_key": current_factor_key,
                        "is_fallback": True  # fallback 표시
                    }
                    # 세션에 fallback 질문 기록
                    session_data["asked_fallback_questions"].append(fb_q)
                    logger.info(f"Fallback 질문 랜덤 선택: {fb_q}")
            
            if next_question is None and len(related_questions) > 0:
                # 현재 factor의 다음 질문 선택
                next_q = related_questions.iloc[0]
                
                next_question = {
                    "question_id": next_q['question_id'],
                    "question_text": next_q['question_text'],
                    "answer_type": next_q['answer_type'],
                    "choices": next_q['choices'].split('|') if next_q.get('choices') else [],
                    "next_factor_hint": next_q.get('next_factor_hint', ''),
                    "factor_key": current_factor_key
                }
                logger.info(f"현재 factor '{current_factor_key}'의 다음 질문: question_id={next_q['question_id']}")
            
            if next_question:
                # 세션에 현재 질문 저장 (다음 답변 시 히스토리에 추가하기 위해)
                session_data["current_question"] = next_question
                
                # 다음 질문 반환 (리뷰는 반환하지 않음)
                print(f"[DEBUG] 응답할 다음 질문: ID={next_question.get('question_id', 'fallback')}, Text={next_question.get('question_text', '')[:50]}")
                logger.info(f"다음 질문: {next_question.get('question_id', 'fallback')}")
                
                return {
                    "next_question": next_question,
                    "related_reviews": [],  # 빈 배열
                    "review_message": "",  # 빈 문자열
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
            
            from backend.app.domain.dialogue.session import DialogueSession
            from backend.app.domain.reg.store import load_csvs
            
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
