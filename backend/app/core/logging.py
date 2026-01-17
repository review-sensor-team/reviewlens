"""중앙집중식 로깅 설정"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logging():
    """로깅 시스템 초기화"""
    
    # 로그 디렉토리 생성
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 로그 포맷 설정
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s [%(name)s:%(funcName)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # 기존 핸들러 제거
    root_logger.handlers.clear()
    
    # 1. 콘솔 핸들러 (INFO 이상)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # 2. 전체 로그 파일 (DEBUG 이상)
    app_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    app_handler.setLevel(logging.DEBUG)
    app_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(app_handler)
    
    # 3. 에러 로그 파일 (ERROR 이상)
    error_handler = RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # 4. API 로그 파일
    api_logger = logging.getLogger("api")
    api_handler = RotatingFileHandler(
        log_dir / "api.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    api_handler.setLevel(logging.INFO)
    api_handler.setFormatter(detailed_formatter)
    api_logger.addHandler(api_handler)
    api_logger.setLevel(logging.INFO)
    api_logger.propagate = False  # 루트 로거로 전파 방지
    
    # 5. 파이프라인 로그 파일
    pipeline_logger = logging.getLogger("pipeline")
    pipeline_handler = RotatingFileHandler(
        log_dir / "pipeline.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    pipeline_handler.setLevel(logging.DEBUG)
    pipeline_handler.setFormatter(detailed_formatter)
    pipeline_logger.addHandler(pipeline_handler)
    pipeline_logger.setLevel(logging.DEBUG)
    pipeline_logger.propagate = True  # 루트 로거로도 전파
    
    # 6. 수집기 로그 파일
    collector_logger = logging.getLogger("collector")
    collector_handler = RotatingFileHandler(
        log_dir / "collector.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    collector_handler.setLevel(logging.DEBUG)
    collector_handler.setFormatter(detailed_formatter)
    collector_logger.addHandler(collector_handler)
    collector_logger.setLevel(logging.DEBUG)
    collector_logger.propagate = True
    
    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    
    logging.info("=" * 80)
    logging.info("ReviewLens 로깅 시스템 초기화 완료")
    logging.info(f"로그 디렉토리: {log_dir.absolute()}")
    logging.info("=" * 80)


def get_logger(name: str) -> logging.Logger:
    """특정 모듈용 로거 반환"""
    return logging.getLogger(name)
