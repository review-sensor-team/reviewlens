"""JSON Review Loader"""
import logging
import json
import re
from pathlib import Path
from typing import Optional
import pandas as pd

from .review_loader import ReviewLoader

logger = logging.getLogger("infra.loaders.json")


class JSONReviewLoader(ReviewLoader):
    """JSON 파일에서 리뷰 로드"""
    
    def load_by_category(
        self,
        category: str,
        vendor: Optional[str] = None,
        latest: bool = True
    ) -> Optional[pd.DataFrame]:
        """카테고리로 리뷰 로드
        
        파일명 패턴: reviews_<vendor>_<category_parts>_<product>_<timestamp>.json
        예: reviews_nespressokorea_electronics_coffee_machine_nespresso_20260103_111926.json
        """
        # 파일명에서 vendor와 timestamp를 제외한 중간 부분에서 category 찾기
        pattern_re = re.compile(r"reviews_(?P<vendor>[^_]+)_(?P<middle>.+)_(?P<timestamp>\d{8}_\d{6})\.json")
        
        matching_files = []
        for json_file in self.review_dir.glob("reviews_*.json"):
            match = pattern_re.match(json_file.name)
            if match:
                file_vendor = match.group('vendor')
                file_middle = match.group('middle')  # category + product가 섞인 부분
                
                # vendor와 category 매칭
                vendor_match = (vendor is None) or (file_vendor == vendor)
                category_match = category in file_middle  # middle 부분에서 category 찾기
                
                if vendor_match and category_match:
                    matching_files.append(json_file)
        
        if not matching_files:
            logger.warning(f"JSON 리뷰 파일 없음: vendor={vendor}, category={category}")
            return None
        
        if latest:
            # 최신 파일만
            latest_file = max(matching_files, key=lambda p: p.stat().st_mtime)
            with open(latest_file, 'r', encoding='utf-8') as f:
                reviews_data = json.load(f)
            df = pd.DataFrame(reviews_data)
            logger.info(f"JSON 리뷰 로드: {latest_file.name} ({len(df)}건)")
            return df
        else:
            # 모든 파일 병합
            all_reviews = []
            for json_file in matching_files:
                with open(json_file, 'r', encoding='utf-8') as f:
                    reviews_data = json.load(f)
                all_reviews.extend(reviews_data)
            df = pd.DataFrame(all_reviews)
            logger.info(f"JSON 리뷰 로드: {len(matching_files)}개 파일, 총 {len(df)}건")
            return df
    
    def load_by_product(
        self,
        product_id: str,
        vendor: Optional[str] = None,
        latest: bool = True
    ) -> Optional[pd.DataFrame]:
        """상품 ID로 리뷰 로드
        
        JSON 형식에서는 product_id가 파일명에 직접 포함되지 않을 수 있음
        대신 category 기반 검색 사용
        """
        # product_id를 category처럼 사용
        return self.load_by_category(category=product_id, vendor=vendor, latest=latest)
