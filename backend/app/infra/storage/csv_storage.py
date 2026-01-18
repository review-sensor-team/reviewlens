"""CSV 저장소 - Infrastructure Layer"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)


class CSVStorage:
    """CSV/JSON 파일 기반 데이터 저장소"""
    
    def __init__(self, data_dir: str | Path, file_format: str = "json"):
        """
        Args:
            data_dir: 데이터 디렉토리 경로
            file_format: 리뷰 파일 형식 ("json" 또는 "csv")
        """
        self.data_dir = Path(data_dir)
        self.review_dir = self.data_dir / "review"
        self.factor_dir = self.data_dir / "factor"
        self.backup_dir = self.data_dir / "backup"
        self.file_format = file_format.lower()
        
        # 디렉토리 생성
        for directory in [self.review_dir, self.factor_dir, self.backup_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def save_reviews(
        self,
        reviews_df: pd.DataFrame,
        vendor: str,
        product_id: str,
        suffix: str = ""
    ) -> Path:
        """리뷰 데이터프레임을 CSV로 저장
        
        Args:
            reviews_df: 리뷰 데이터프레임
            vendor: 판매처 (smartstore, coupang 등)
            product_id: 제품 ID
            suffix: 파일명 접미사 (옵션)
            
        Returns:
            저장된 파일 경로
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{vendor}_{product_id}_{timestamp}"
        if suffix:
            filename += f"_{suffix}"
        filename += ".csv"
        
        filepath = self.review_dir / filename
        reviews_df.to_csv(filepath, index=False, encoding='utf-8')
        
        logger.info(f"리뷰 저장: {filepath} ({len(reviews_df)}건)")
        return filepath
    
    def load_reviews(
        self,
        vendor: str,
        product_id: str,
        latest: bool = True
    ) -> Optional[pd.DataFrame]:
        """CSV에서 리뷰 로드
        
        Args:
            vendor: 판매처
            product_id: 제품 ID
            latest: True면 최신 파일, False면 모든 파일
            
        Returns:
            리뷰 데이터프레임 (없으면 None)
        """
        pattern = f"{vendor}_{product_id}_*.csv"
        files = list(self.review_dir.glob(pattern))
        
        if not files:
            logger.warning(f"리뷰 파일 없음: {pattern}")
            return None
        
        if latest:
            # 최신 파일만
            latest_file = max(files, key=lambda p: p.stat().st_mtime)
            df = pd.read_csv(latest_file)
            logger.info(f"리뷰 로드: {latest_file.name} ({len(df)}건)")
            return df
        else:
            # 모든 파일 병합
            dfs = [pd.read_csv(f) for f in files]
            df = pd.concat(dfs, ignore_index=True)
            logger.info(f"리뷰 로드: {len(files)}개 파일, 총 {len(df)}건")
            return df
    
    def save_factor_scores(
        self,
        scores_df: pd.DataFrame,
        category: str,
        product_id: str
    ) -> Path:
        """Factor 점수 결과를 CSV로 저장
        
        Args:
            scores_df: Factor 점수 데이터프레임
            category: 카테고리
            product_id: 제품 ID
            
        Returns:
            저장된 파일 경로
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"factor_scores_{category}_{product_id}_{timestamp}.csv"
        filepath = self.factor_dir / filename
        
        scores_df.to_csv(filepath, index=False, encoding='utf-8')
        logger.info(f"Factor 점수 저장: {filepath}")
        return filepath
    
    def backup_file(self, source_path: Path) -> Path:
        """파일 백업
        
        Args:
            source_path: 원본 파일 경로
            
        Returns:
            백업 파일 경로
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{source_path.stem}_{timestamp}{source_path.suffix}"
        backup_path = self.backup_dir / backup_name
        
        import shutil
        shutil.copy2(source_path, backup_path)
        
        logger.info(f"백업 완료: {source_path.name} → {backup_path.name}")
        return backup_path
    
    def list_reviews(self, vendor: Optional[str] = None) -> List[Dict[str, Any]]:
        """저장된 리뷰 파일 목록 조회 (CSV + JSON)
        
        Args:
            vendor: 판매처 (None이면 전체)
            
        Returns:
            파일 정보 리스트 [{"path": Path, "vendor": str, "category": str, "product_id": str}]
        """
        import re
        
        # CSV와 JSON 파일 모두 검색
        csv_pattern = f"{vendor}_*.csv" if vendor else "*.csv"
        json_pattern = f"reviews_{vendor}_*.json" if vendor else "reviews_*.json"
        
        csv_files = list(self.review_dir.glob(csv_pattern))
        json_files = list(self.review_dir.glob(json_pattern))
        
        file_list = []
        
        # CSV 파일 처리
        for filepath in csv_files:
            stat = filepath.stat()
            file_list.append({
                "path": filepath,
                "name": filepath.name,
                "size": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime),
                "vendor": filepath.name.split("_")[0] if "_" in filepath.name else "unknown",
                "product_id": filepath.stem,
                "category": "",
                "format": "csv"
            })
        
        # JSON 파일 처리 (reviews_<vendor>_<category>_<timestamp>.json)
        json_pattern_re = re.compile(r"reviews_(?P<vendor>[^_]+)_(?P<category>.+)_(?P<timestamp>\d{8}_\d{6})\.json")
        for filepath in json_files:
            match = json_pattern_re.match(filepath.name)
            if match:
                stat = filepath.stat()
                file_vendor = match.group('vendor')
                file_category = match.group('category')
                
                file_list.append({
                    "path": filepath,
                    "name": filepath.name,
                    "size": stat.st_size,
                    "mtime": datetime.fromtimestamp(stat.st_mtime),
                    "vendor": file_vendor,
                    "product_id": file_category,  # category를 product_id로 사용
                    "category": file_category,
                    "format": "json"
                })
        
        # 최신순 정렬
        file_list.sort(key=lambda x: x["mtime"], reverse=True)
        
        logger.debug(f"리뷰 파일 목록: {len(file_list)}개 (CSV: {len(csv_files)}, JSON: {len(json_files)})")
        return file_list
    
    def load_reviews_json(
        self,
        vendor: str,
        category: str,
        latest: bool = True
    ) -> Optional[pd.DataFrame]:
        """JSON에서 리뷰 로드
        
        Args:
            vendor: 판매처
            category: 카테고리 (coffee_machine, desk 등)
            latest: True면 최신 파일, False면 모든 파일
            
        Returns:
            리뷰 데이터프레임 (없으면 None)
        """
        import re
        import json
        
        # JSON 파일 패턴: reviews_<vendor>_<category>_<timestamp>.json
        pattern_re = re.compile(r"reviews_(?P<vendor>[^_]+)_(?P<category>.+)_(?P<timestamp>\d{8}_\d{6})\.json")
        
        matching_files = []
        for json_file in self.review_dir.glob("reviews_*.json"):
            match = pattern_re.match(json_file.name)
            if match:
                file_vendor = match.group('vendor')
                file_category = match.group('category')
                
                # vendor와 category 매칭
                if file_vendor == vendor and category in file_category:
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
    
    def load_reviews_by_category(
        self,
        category: str,
        latest: bool = True
    ) -> Optional[pd.DataFrame]:
        """카테고리로 리뷰 로드 (파일 형식 자동 감지)
        
        Args:
            category: 카테고리 (coffee_machine, desk 등)
            latest: True면 최신 파일, False면 모든 파일
            
        Returns:
            리뷰 데이터프레임 (없으면 None)
        """
        # 파일 형식에 따라 적절한 로더 호출
        if self.file_format == "json":
            # JSON 형식: 모든 vendor에서 category 매칭 시도
            review_files = self.list_reviews()
            for file_info in review_files:
                if file_info.get("format") == "json":
                    file_category = file_info.get("category", "")
                    if category in file_category:
                        file_vendor = file_info.get("vendor", "")
                        return self.load_reviews_json(file_vendor, category, latest)
            return None
        else:
            # CSV 형식: 기존 load_reviews 사용
            # CSV는 vendor_product_id_timestamp.csv 형식이므로 category로 직접 매칭 어려움
            logger.warning(f"CSV 형식에서는 category로 직접 로드가 어렵습니다: {category}")
            return None
