"""Review Loader Factory"""
import logging
from pathlib import Path
from typing import Optional, Union

from .review_loader import ReviewLoader
from .json_review_loader import JSONReviewLoader
from .csv_review_loader import CSVReviewLoader
from .url_review_loader import URLReviewLoader

logger = logging.getLogger(__name__)


class ReviewLoaderFactory:
    """리뷰 로더 팩토리
    
    설정에 따라 적절한 ReviewLoader 인스턴스 생성
    """
    
    @staticmethod
    def create(
        data_dir: Union[str, Path],
        source_mode: str = "json_file",
        file_format: str = "json"
    ) -> ReviewLoader:
        """리뷰 로더 생성
        
        Args:
            data_dir: 데이터 디렉토리
            source_mode: "json_file", "csv_file", "url"
            file_format: "json" 또는 "csv" (file 모드일 때만 사용)
            
        Returns:
            적절한 ReviewLoader 인스턴스
        """
        if source_mode == "url":
            logger.info("URL Review Loader 생성")
            return URLReviewLoader(data_dir=data_dir)
        
        elif source_mode in ["json_file", "csv_file", "file"]:
            # file_format에 따라 결정
            if file_format.lower() == "json":
                logger.info("JSON Review Loader 생성")
                return JSONReviewLoader(data_dir=data_dir)
            elif file_format.lower() == "csv":
                logger.info("CSV Review Loader 생성")
                return CSVReviewLoader(data_dir=data_dir)
            else:
                logger.warning(f"알 수 없는 file_format: {file_format}, JSON 사용")
                return JSONReviewLoader(data_dir=data_dir)
        
        else:
            logger.warning(f"알 수 없는 source_mode: {source_mode}, JSON 파일 사용")
            return JSONReviewLoader(data_dir=data_dir)
    
    @staticmethod
    def create_from_settings(settings, data_dir: Optional[Union[str, Path]] = None) -> ReviewLoader:
        """설정 파일에서 로더 생성
        
        Args:
            settings: Settings 인스턴스
            data_dir: 데이터 디렉토리 (선택적, 없으면 settings에서 가져옴)
            
        Returns:
            설정에 맞는 ReviewLoader 인스턴스
        """
        if data_dir is None:
            data_dir = settings.REVIEW_DIR
        
        return ReviewLoaderFactory.create(
            data_dir=data_dir,
            source_mode=settings.REVIEW_SOURCE_MODE,
            file_format=settings.REVIEW_FILE_FORMAT
        )
