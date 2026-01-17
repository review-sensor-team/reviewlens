"""리뷰 서비스 - 리뷰 수집 및 분석 유스케이스 (Service Layer)"""
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import pandas as pd

logger = logging.getLogger("services.review")


class ReviewService:
    """리뷰 수집, 정규화, 분석 (Infrastructure 레이어 통합)"""
    
    def __init__(
        self,
        data_dir: str | Path,
        use_cache: bool = True,
        use_storage: bool = True
    ):
        """
        Args:
            data_dir: 데이터 디렉토리
            use_cache: 캐시 사용 여부
            use_storage: 저장소 사용 여부
        """
        self.data_dir = Path(data_dir)
        self.use_cache = use_cache
        self.use_storage = use_storage
        
        # Infrastructure 레이어 초기화 (lazy loading)
        self._collector = None
        self._cache = None
        self._storage = None
        self._review_loader = None  # Factory pattern으로 교체
    
    def _get_review_loader(self):
        """Review Loader 인스턴스 가져오기 (lazy loading with Factory)"""
        if self._review_loader is None:
            from ..infra.loaders import ReviewLoaderFactory
            from ..core.settings import settings
            self._review_loader = ReviewLoaderFactory.create_from_settings(
                settings=settings,
                data_dir=self.data_dir
            )
        return self._review_loader
    
    def _get_storage(self):
        """Storage 인스턴스 가져오기 (lazy loading) - Deprecated, use _get_review_loader instead"""
        if self._storage is None and self.use_storage:
            from ..infra.storage.csv_storage import CSVStorage
            from ..core.settings import settings
            self._storage = CSVStorage(
                data_dir=self.data_dir,
                file_format=settings.REVIEW_FILE_FORMAT
            )
        return self._storage
    
    def _get_cache(self):
        """Cache 인스턴스 가져오기 (lazy loading)"""
        if self._cache is None and self.use_cache:
            from ..infra.cache.review_cache import ReviewCache
            self._cache = ReviewCache(cache_dir=str(self.data_dir / "review"))
        return self._cache
    
    def get_available_products(self) -> List[Dict[str, Any]]:
        """사용 가능한 상품 목록 조회
        
        Factor CSV 파일(reg_factor_v4.csv)에서 상품 목록 추출
        
        Returns:
            상품 목록 [{ product_id, product_name, category, review_count }]
        """
        products = []
        factor_csv_path = self.data_dir / "factor" / "reg_factor_v4.csv"
        
        try:
            if factor_csv_path.exists():
                # Factor CSV 파일 로드
                df = pd.read_csv(factor_csv_path)
                
                # product_name, category, category_name으로 그룹화하여 고유 상품 목록 추출
                if 'product_name' in df.columns and 'category_name' in df.columns and 'category' in df.columns:
                    product_groups = df.groupby(['product_name', 'category', 'category_name']).agg({
                        'factor_id': 'count'  # factor 개수
                    }).reset_index()
                    
                    for idx, row in product_groups.iterrows():
                        product_name = row['product_name']
                        category = row['category']  # 영문 category (파일명에 사용)
                        category_name = row['category_name']  # 한글 category (표시용)
                        factor_count = row['factor_id']
                        
                        # product_id 생성 (상품명에서 공백 제거)
                        product_id = product_name.replace(' ', '_').replace('/', '_')
                        
                        # Storage에서 실제 리뷰 파일이 있는지 확인 (category 기반 매칭)
                        storage = self._get_storage()
                        review_count = 0
                        if storage:
                            review_files = storage.list_reviews()
                            for file_info in review_files:
                                vendor = file_info.get("vendor", "")
                                pid = file_info.get("product_id", "")
                                file_category = file_info.get("category", "")
                                
                                # category와 product_name으로 매칭
                                if category in file_category or category in pid:
                                    if product_name.lower() in pid.lower() or product_id.lower() in pid.lower():
                                        # 리뷰 파일이 있으면 카운트
                                        review_df = storage.load_reviews(vendor, pid, latest=True)
                                        if review_df is not None:
                                            review_count = len(review_df)
                                            break
                        
                        # 리뷰 파일이 없으면 factor 개수를 표시
                        if review_count == 0:
                            review_count = factor_count * 10  # factor당 평균 10개 리뷰로 추정
                        
                        products.append({
                            "product_id": product_id,
                            "product_name": product_name,
                            "category": category_name,  # 한글 카테고리 표시
                            "category_key": category,  # 영문 카테고리 (내부 사용)
                            "review_count": review_count,
                            "vendor": "smartstore"
                        })
                    
                    logger.info(f"Factor CSV에서 {len(products)}개 상품 로드")
        except Exception as e:
            logger.error(f"Factor CSV 로드 실패: {e}", exc_info=True)
        
        # 비어있으면 샘플 상품 추가
        if not products:
            logger.warning("Factor CSV에 상품 없음. 샘플 상품 추가")
            sample_review_file = self.data_dir / "review" / "review_sample.csv"
            if sample_review_file.exists():
                df = pd.read_csv(sample_review_file)
                products.append({
                    "product_id": "sample_001",
                    "product_name": "샘플 상품 (갤럭시 버즈)",
                    "category": "전자기기",
                    "category_key": "electronics",
                    "review_count": len(df),
                    "vendor": "sample"
                })
        
        logger.info(f"사용 가능한 상품: {len(products)}개")
        return products
        
    def collect_reviews(
        self,
        product_id: str,
        vendor: str = "smartstore",
        max_reviews: int = 100,
        product_url: Optional[str] = None,
        use_collector: bool = False
    ) -> Dict[str, Any]:
        """리뷰 수집 (Infrastructure 레이어 활용)
        
        Args:
            product_id: 제품 ID
            vendor: 판매처 (smartstore, coupang 등)
            max_reviews: 최대 수집 개수
            product_url: 제품 URL (collector 사용 시 필요)
            use_collector: 실제 크롤러 사용 여부
            
        Returns:
            수집 결과
        """
        logger.info(f"리뷰 수집 시작: {vendor}/{product_id} (max={max_reviews}, use_collector={use_collector})")
        
        # 1. Storage에서 기존 데이터 확인
        storage = self._get_storage()
        if storage and not use_collector:
            cached_df = storage.load_reviews(vendor=vendor, product_id=product_id)
            if cached_df is not None:
                logger.info(f"  - Storage에서 로드: {len(cached_df)}건")
                return {
                    "product_id": product_id,
                    "vendor": vendor,
                    "review_count": len(cached_df),
                    "reviews_df": cached_df,
                    "source": "storage"
                }
        
        # 2. Collector 사용 (실제 크롤링)
        if use_collector and product_url:
            try:
                if vendor == "smartstore":
                    from ..infra.collectors.smartstore import SmartStoreCollector
                    collector = SmartStoreCollector(product_url=product_url, headless=True)
                    reviews, _ = collector.collect_reviews(max_reviews=max_reviews)
                    
                    # DataFrame 변환
                    reviews_df = pd.DataFrame(reviews)
                    
                    # Storage에 저장
                    if storage:
                        storage.save_reviews(reviews_df, vendor, product_id, suffix="collected")
                    
                    logger.info(f"  - 크롤링 완료: {len(reviews_df)}건")
                    return {
                        "product_id": product_id,
                        "vendor": vendor,
                        "review_count": len(reviews_df),
                        "reviews_df": reviews_df,
                        "source": "collector"
                    }
                else:
                    logger.warning(f"지원하지 않는 vendor: {vendor}")
            except Exception as e:
                logger.error(f"크롤링 실패: {e}", exc_info=True)
        
        # 3. 샘플 데이터 로드 (fallback)
        reviews_df = self._load_sample_reviews()
        logger.info(f"  - 샘플 데이터 로드: {len(reviews_df)}건")
        
        return {
            "product_id": product_id,
            "vendor": vendor,
            "review_count": len(reviews_df),
            "reviews_df": reviews_df,
            "source": "sample"
        }
    
    def normalize_reviews(self, reviews_df: pd.DataFrame, vendor: str = "smartstore") -> pd.DataFrame:
        """리뷰 정규화 및 중복 제거
        
        Args:
            reviews_df: 원본 리뷰 데이터프레임
            vendor: 판매처 (기본값: smartstore)
            
        Returns:
            정규화된 리뷰 데이터프레임
        """
        from ..domain.review.normalize import normalize_review, dedupe_reviews
        
        logger.info(f"리뷰 정규화: {len(reviews_df)}건 (vendor={vendor})")
        
        # 1. 각 리뷰 정규화
        normalized = []
        for _, row in reviews_df.iterrows():
            norm_row = normalize_review(row, vendor=vendor)
            normalized.append(norm_row)
        
        df = pd.DataFrame(normalized)
        
        # 2. 중복 제거 (튜플 반환: df, total, removed)
        df, total, removed = dedupe_reviews(df)
        
        logger.info(f"  - 정규화 완료: {len(df)}건 (중복 제거: {removed}건)")
        
        return df
    
    def analyze_reviews(
        self,
        reviews_df: pd.DataFrame,
        factors: List[Any],
        top_k: int = 3,
        save_results: bool = False,
        category: str = "",
        product_id: str = ""
    ) -> Dict[str, Any]:
        """리뷰 분석 (factor scoring) + Storage 저장
        
        Args:
            reviews_df: 리뷰 데이터프레임
            factors: Factor 리스트
            top_k: 상위 factor 개수
            save_results: 결과 저장 여부
            category: 카테고리 (저장 시 사용)
            product_id: 제품 ID (저장 시 사용)
            
        Returns:
            분석 결과
        """
        from ..domain.review.scoring import compute_review_factor_scores
        
        logger.info(f"리뷰 분석: {len(reviews_df)}건, {len(factors)}개 factors")
        
        # 1. Factor scoring (튜플 반환: scored_df, factor_counts)
        scored_df, factor_counts = compute_review_factor_scores(reviews_df, factors)
        
        # 2. 전체 factor 점수 집계
        factor_scores = {}
        for factor in factors:
            col_name = f"score_{factor.factor_key}"
            if col_name in scored_df.columns:
                total_score = scored_df[col_name].sum()
                factor_scores[factor.factor_key] = total_score
        
        # 3. Top factors
        top_factors = sorted(
            factor_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        logger.info(f"  - Top {top_k} factors: {[k for k, _ in top_factors]}")
        
        # 4. Storage에 결과 저장 (옵션)
        if save_results and category and product_id:
            storage = self._get_storage()
            if storage:
                storage.save_factor_scores(scored_df, category, product_id)
                logger.info(f"  - 분석 결과 저장 완료")
        
        return {
            "scored_reviews_df": scored_df,
            "factor_scores": factor_scores,
            "factor_counts": factor_counts,
            "top_factors": top_factors,
            "review_count": len(scored_df)
        }
    
    def get_evidence_reviews(
        self,
        reviews_df: pd.DataFrame,
        factor_key: str,
        quota: int = 5
    ) -> List[Dict[str, Any]]:
        """특정 factor에 대한 증거 리뷰 추출
        
        Args:
            reviews_df: 점수가 계산된 리뷰 데이터프레임
            factor_key: Factor key
            quota: 최대 리뷰 개수
            
        Returns:
            증거 리뷰 리스트
        """
        from ..domain.review.retrieval import retrieve_evidence_reviews
        
        logger.info(f"증거 리뷰 추출: {factor_key} (quota={quota})")
        
        evidence = retrieve_evidence_reviews(
            reviews_df=reviews_df,
            factor_key=factor_key,
            quota_pos=quota // 2,
            quota_neg=quota // 2,
            quota_mix=quota // 4,
            quota_neu=quota // 4
        )
        
        logger.info(f"  - 추출 완료: {len(evidence)}건")
        
        return evidence
    
    def _load_sample_reviews(self) -> pd.DataFrame:
        """샘플 리뷰 로드 (임시)"""
        review_dir = self.data_dir / "review"
        
        # CSV 파일 찾기
        csv_files = list(review_dir.glob("*.csv"))
        if csv_files:
            logger.info(f"샘플 리뷰 로드: {csv_files[0].name}")
            return pd.read_csv(csv_files[0])
        
        # 없으면 빈 데이터프레임
        logger.warning("샘플 리뷰 없음, 빈 데이터프레임 반환")
        return pd.DataFrame(columns=["review_id", "content", "rating", "vendor"])
