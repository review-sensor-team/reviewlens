"""CSV Review Loader"""
import logging
from pathlib import Path
from typing import Optional
import pandas as pd

from .review_loader import ReviewLoader

logger = logging.getLogger(__name__)


class CSVReviewLoader(ReviewLoader):
    """CSV 파일에서 리뷰 로드"""
    
    def load_by_category(
        self,
        category: str,
        vendor: Optional[str] = None,
        latest: bool = True
    ) -> Optional[pd.DataFrame]:
        """카테고리로 리뷰 로드
        
        CSV는 파일명에 category가 직접 포함되지 않을 수 있어
        모든 파일을 검색하거나 메타데이터 필요
        """
        # CSV 파일 패턴: <vendor>_<product_id>_<timestamp>.csv
        pattern = f"{vendor}_*.csv" if vendor else "*.csv"
        files = list(self.review_dir.glob(pattern))
        
        if not files:
            logger.warning(f"CSV 리뷰 파일 없음: vendor={vendor}, category={category}")
            return None
        
        # CSV는 category 정보가 파일명에 없으므로
        # 파일 내용을 읽어서 확인하거나, 별도 메타데이터 필요
        # 일단 모든 파일 병합 후 필터링
        logger.warning(f"CSV 형식에서는 category 기반 검색이 제한적입니다: {category}")
        
        if latest:
            latest_file = max(files, key=lambda p: p.stat().st_mtime)
            df = pd.read_csv(latest_file)
            logger.info(f"CSV 리뷰 로드: {latest_file.name} ({len(df)}건)")
            return df
        else:
            dfs = [pd.read_csv(f) for f in files]
            df = pd.concat(dfs, ignore_index=True)
            logger.info(f"CSV 리뷰 로드: {len(files)}개 파일, 총 {len(df)}건")
            return df
    
    def load_by_product(
        self,
        product_id: str,
        vendor: Optional[str] = None,
        latest: bool = True
    ) -> Optional[pd.DataFrame]:
        """상품 ID로 리뷰 로드
        
        파일명 패턴: <vendor>_<product_id>_<timestamp>.csv
        """
        pattern = f"{vendor}_{product_id}_*.csv" if vendor else f"*_{product_id}_*.csv"
        files = list(self.review_dir.glob(pattern))
        
        if not files:
            logger.warning(f"CSV 리뷰 파일 없음: vendor={vendor}, product_id={product_id}")
            return None
        
        if latest:
            latest_file = max(files, key=lambda p: p.stat().st_mtime)
            df = pd.read_csv(latest_file)
            logger.info(f"CSV 리뷰 로드: {latest_file.name} ({len(df)}건)")
            return df
        else:
            dfs = [pd.read_csv(f) for f in files]
            df = pd.concat(dfs, ignore_index=True)
            logger.info(f"CSV 리뷰 로드: {len(files)}개 파일, 총 {len(df)}건")
            return df
