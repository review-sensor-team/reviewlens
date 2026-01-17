"""리뷰 캐시 관리"""
import logging
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ReviewCache:
    """파일 기반 리뷰 캐시"""
    
    def __init__(self, cache_dir: str = "backend/data/review"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    async def save(
        self, 
        vendor: str, 
        product_id: str, 
        reviews: List[Dict[str, Any]]
    ):
        """리뷰 캐시 저장"""
        filename = f"{vendor}_{product_id}_{datetime.now().strftime('%Y%m%d')}.json"
        filepath = self.cache_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(reviews, f, ensure_ascii=False, indent=2)
        
        logger.info(f"리뷰 캐시 저장: {filepath}")
    
    async def load(self, vendor: str, product_id: str) -> List[Dict[str, Any]]:
        """리뷰 캐시 로드"""
        # 최신 파일 찾기
        pattern = f"{vendor}_{product_id}_*.json"
        files = list(self.cache_dir.glob(pattern))
        
        if not files:
            return []
        
        latest_file = max(files, key=lambda p: p.stat().st_mtime)
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            reviews = json.load(f)
        
        logger.info(f"리뷰 캐시 로드: {latest_file} ({len(reviews)}개)")
        return reviews
