"""URL Review Loader"""
import logging
from pathlib import Path
from typing import Optional
import pandas as pd

from .review_loader import ReviewLoader

logger = logging.getLogger(__name__)


class URLReviewLoader(ReviewLoader):
    """URL에서 리뷰 수집 후 로드"""
    
    def __init__(self, data_dir: str | Path):
        super().__init__(data_dir)
        self._collector = None
    
    def _get_collector(self):
        """Lazy loading for collector"""
        if self._collector is None:
            # TODO: Import actual collector
            # from ...collector.review_collector import ReviewCollector
            # self._collector = ReviewCollector()
            pass
        return self._collector
    
    def load_by_category(
        self,
        category: str,
        vendor: Optional[str] = None,
        latest: bool = True
    ) -> Optional[pd.DataFrame]:
        """카테고리로 리뷰 로드
        
        URL 모드에서는 category만으로 로드 불가
        URL이 필요함
        """
        logger.warning(f"URL 모드에서는 category만으로 로드할 수 없습니다: {category}")
        logger.info(f"URL을 제공하거나 load_by_url() 메서드를 사용하세요")
        return None
    
    def load_by_product(
        self,
        product_id: str,
        vendor: Optional[str] = None,
        latest: bool = True
    ) -> Optional[pd.DataFrame]:
        """상품 ID로 리뷰 로드
        
        URL 모드에서는 product_id만으로 로드 불가
        """
        logger.warning(f"URL 모드에서는 product_id만으로 로드할 수 없습니다: {product_id}")
        return None
    
    def load_by_url(
        self,
        url: str,
        max_reviews: int = 100
    ) -> Optional[pd.DataFrame]:
        """URL에서 리뷰 수집
        
        Args:
            url: 상품 URL
            max_reviews: 최대 수집 리뷰 수
            
        Returns:
            수집된 리뷰 DataFrame
        """
        collector = self._get_collector()
        if collector is None:
            logger.error("Collector가 초기화되지 않았습니다")
            return None
        
        try:
            # TODO: Implement actual collection
            # reviews_df = collector.collect(url, max_reviews=max_reviews)
            # logger.info(f"URL 리뷰 수집 완료: {url} ({len(reviews_df)}건)")
            # return reviews_df
            
            logger.warning("URL 수집 기능은 아직 구현되지 않았습니다")
            return None
        except Exception as e:
            logger.error(f"URL 리뷰 수집 실패: {e}", exc_info=True)
            return None
