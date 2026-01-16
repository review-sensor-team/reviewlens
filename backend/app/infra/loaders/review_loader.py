"""Review Loader - Abstract Base Class"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import pandas as pd


class ReviewLoader(ABC):
    """리뷰 로더 인터페이스
    
    모든 리뷰 로더는 이 인터페이스를 구현해야 함
    - CSV 파일에서 로드
    - JSON 파일에서 로드
    - URL에서 수집
    """
    
    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.review_dir = self.data_dir / "review"
        self.review_dir.mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    def load_by_category(
        self,
        category: str,
        vendor: Optional[str] = None,
        latest: bool = True
    ) -> Optional[pd.DataFrame]:
        """카테고리로 리뷰 로드
        
        Args:
            category: 카테고리 (coffee_machine, desk 등)
            vendor: 판매처 (optional)
            latest: 최신 파일만 로드할지 여부
            
        Returns:
            리뷰 DataFrame (없으면 None)
        """
        pass
    
    @abstractmethod
    def load_by_product(
        self,
        product_id: str,
        vendor: Optional[str] = None,
        latest: bool = True
    ) -> Optional[pd.DataFrame]:
        """상품 ID로 리뷰 로드
        
        Args:
            product_id: 상품 ID
            vendor: 판매처 (optional)
            latest: 최신 파일만 로드할지 여부
            
        Returns:
            리뷰 DataFrame (없으면 None)
        """
        pass
