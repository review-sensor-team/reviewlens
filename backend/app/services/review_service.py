"""리뷰 서비스 - 리뷰 수집 및 분석 유스케이스 (Service Layer)"""
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import pandas as pd

from ..infra.loaders import ReviewLoaderFactory
from ..infra.storage.csv_storage import CSVStorage
from ..infra.cache.review_cache import ReviewCache
from ..infra.collectors.smartstore import SmartStoreCollector
from ..domain.rules.review.normalize import normalize_review, dedupe_reviews
from ..domain.rules.review.scoring import compute_review_factor_scores
from ..domain.rules.review.retrieval import retrieve_evidence_reviews
from ..core.settings import settings

logger = logging.getLogger(__name__)


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
            self._review_loader = ReviewLoaderFactory.create_from_settings(
                settings=settings,
                data_dir=self.data_dir
            )
        return self._review_loader
    
    def _get_storage(self):
        """Storage 인스턴스 가져오기 (lazy loading) - Deprecated, use _get_review_loader instead"""
        if self._storage is None and self.use_storage:
            self._storage = CSVStorage(
                data_dir=self.data_dir,
                file_format=settings.REVIEW_FILE_FORMAT
            )
        return self._storage
    
    def _get_cache(self):
        """Cache 인스턴스 가져오기 (lazy loading)"""
        if self._cache is None and self.use_cache:
            self._cache = ReviewCache(cache_dir=str(self.data_dir / "review"))
        return self._cache
    
    def _load_factor_csv(self) -> Optional[pd.DataFrame]:
        """Factor CSV 로드 및 상품 그룹화"""
        factor_csv_path = self.data_dir / "factor" / "reg_factor_v4.csv"
        
        if not factor_csv_path.exists():
            return None
        
        try:
            df = pd.read_csv(factor_csv_path)
            required_cols = ['product_name', 'category', 'category_name']
            
            if all(col in df.columns for col in required_cols):
                return df.groupby(required_cols).agg({
                    'factor_id': 'count'
                }).reset_index()
            
            return None
        except Exception as e:
            logger.error(f"Factor CSV 로드 실패: {e}", exc_info=True)
            return None
    
    def _match_review_file(self, category: str, product_name: str, product_id: str) -> int:
        """리뷰 파일 매칭 및 카운트 반환"""
        storage = self._get_storage()
        if not storage:
            return 0
        
        review_files = storage.list_reviews()
        for file_info in review_files:
            pid = file_info.get("product_id", "")
            file_category = file_info.get("category", "")
            
            # category와 product_name으로 매칭
            category_match = category in file_category or category in pid
            name_match = product_name.lower() in pid.lower() or product_id.lower() in pid.lower()
            
            if category_match and name_match:
                vendor = file_info.get("vendor", "")
                review_df = storage.load_reviews(vendor, pid, latest=True)
                if review_df is not None:
                    return len(review_df)
        
        return 0
    
    def _create_product_info(self, row: pd.Series, review_count: int) -> Dict[str, Any]:
        """상품 정보 딕셔너리 생성"""
        product_name = row['product_name']
        category = row['category']
        category_name = row['category_name']
        factor_count = row['factor_id']
        
        product_id = product_name.replace(' ', '_').replace('/', '_')
        
        # 리뷰 파일이 없으면 factor 개수로 추정
        if review_count == 0:
            review_count = factor_count * 10
        
        return {
            "product_id": product_id,
            "product_name": product_name,
            "category": category_name,
            "category_key": category,
            "review_count": review_count,
            "vendor": "smartstore"
        }
    
    def _add_fallback_product(self) -> List[Dict[str, Any]]:
        """샘플 상품 추가 (폴백)"""
        logger.warning("Factor CSV에 상품 없음. 샘플 상품 추가")
        sample_review_file = self.data_dir / "review" / "review_sample.csv"
        
        if sample_review_file.exists():
            df = pd.read_csv(sample_review_file)
            return [{
                "product_id": "sample_001",
                "product_name": "샘플 상품 (갤럭시 버즈)",
                "category": "전자기기",
                "category_key": "electronics",
                "review_count": len(df),
                "vendor": "sample"
            }]
        
        return []
    
    def get_available_products(self) -> List[Dict[str, Any]]:
        """사용 가능한 상품 목록 조회
        
        Factor CSV 파일(reg_factor_v4.csv)에서 상품 목록 추출
        
        Returns:
            상품 목록 [{ product_id, product_name, category, review_count }]
        """
        products = []
        product_groups = self._load_factor_csv()
        
        if product_groups is not None:
            for idx, row in product_groups.iterrows():
                product_name = row['product_name']
                category = row['category']
                product_id = product_name.replace(' ', '_').replace('/', '_')
                
                review_count = self._match_review_file(category, product_name, product_id)
                products.append(self._create_product_info(row, review_count))
            
            logger.info(f"Factor CSV에서 {len(products)}개 상품 로드")
        
        # 비어있으면 샘플 상품 추가
        if not products:
            products = self._add_fallback_product()
        
        logger.info(f"사용 가능한 상품: {len(products)}개")
        return products
    
    def _load_from_storage(self, vendor: str, product_id: str) -> Optional[pd.DataFrame]:
        """저장소에서 리뷰 로드"""
        storage = self._get_storage()
        if not storage:
            return None
        
        cached_df = storage.load_reviews(vendor=vendor, product_id=product_id)
        if cached_df is not None:
            logger.info(f"  - Storage에서 로드: {len(cached_df)}건")
        return cached_df
    
    def _collect_from_crawler(self, vendor: str, product_id: str, product_url: str, max_reviews: int) -> Optional[pd.DataFrame]:
        """크롤러로 리뷰 수집"""
        try:
            if vendor == "smartstore":
                collector = SmartStoreCollector(product_url=product_url, headless=True)
                reviews, _ = collector.collect_reviews(max_reviews=max_reviews)
                
                reviews_df = pd.DataFrame(reviews)
                
                # Storage에 저장
                storage = self._get_storage()
                if storage:
                    storage.save_reviews(reviews_df, vendor, product_id, suffix="collected")
                
                logger.info(f"  - 크롤링 완료: {len(reviews_df)}건")
                return reviews_df
            else:
                logger.warning(f"지원하지 않는 vendor: {vendor}")
        except Exception as e:
            logger.error(f"크롤링 실패: {e}", exc_info=True)
        
        return None
    
    def _create_collect_result(self, product_id: str, vendor: str, reviews_df: pd.DataFrame, source: str) -> Dict[str, Any]:
        """리뷰 수집 결과 딕셔너리 생성"""
        return {
            "product_id": product_id,
            "vendor": vendor,
            "review_count": len(reviews_df),
            "reviews_df": reviews_df,
            "source": source
        }
    
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
        if not use_collector:
            cached_df = self._load_from_storage(vendor, product_id)
            if cached_df is not None:
                return self._create_collect_result(product_id, vendor, cached_df, "storage")
        
        # 2. Collector 사용 (실제 크롤링)
        if use_collector and product_url:
            collected_df = self._collect_from_crawler(vendor, product_id, product_url, max_reviews)
            if collected_df is not None:
                return self._create_collect_result(product_id, vendor, collected_df, "collector")
        
        # 3. 샘플 데이터 로드 (fallback)
        reviews_df = self._load_sample_reviews()
        logger.info(f"  - 샘플 데이터 로드: {len(reviews_df)}건")
        
        return self._create_collect_result(product_id, vendor, reviews_df, "sample")
    
    def normalize_reviews(self, reviews_df: pd.DataFrame, vendor: str = "smartstore") -> pd.DataFrame:
        """리뷰 정규화 및 중복 제거
        
        Args:
            reviews_df: 원본 리뷰 데이터프레임
            vendor: 판매처 (기본값: smartstore)
            
        Returns:
            정규화된 리뷰 데이터프레임
        """
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
    
    def _aggregate_factor_scores(self, scored_df: pd.DataFrame, factors: List[Any]) -> Dict[str, float]:
        """scored DataFrame에서 factor 점수 집계"""
        factor_scores = {}
        for factor in factors:
            col_name = f"score_{factor.factor_key}"
            if col_name in scored_df.columns:
                total_score = scored_df[col_name].sum()
                factor_scores[factor.factor_key] = total_score
        return factor_scores
    
    def _get_top_factors(self, factor_scores: Dict[str, float], top_k: int) -> List[tuple]:
        """상위 k개 factor 추출"""
        top_factors = sorted(
            factor_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        logger.info(f"  - Top {top_k} factors: {[k for k, _ in top_factors]}")
        return top_factors
    
    def _save_analysis_results(self, scored_df: pd.DataFrame, category: str, product_id: str) -> None:
        """분석 결과를 저장소에 저장"""
        storage = self._get_storage()
        if storage:
            storage.save_factor_scores(scored_df, category, product_id)
            logger.info(f"  - 분석 결과 저장 완료")
    
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
        logger.info(f"리뷰 분석: {len(reviews_df)}건, {len(factors)}개 factors")
        
        # 1. Factor scoring
        scored_df, factor_counts = compute_review_factor_scores(reviews_df, factors)
        
        # 2. 전체 factor 점수 집계
        factor_scores = self._aggregate_factor_scores(scored_df, factors)
        
        # 3. Top factors
        top_factors = self._get_top_factors(factor_scores, top_k)
        
        # 4. Storage에 결과 저장 (옵션)
        if save_results and category and product_id:
            self._save_analysis_results(scored_df, category, product_id)
        
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
