"""Settings 기반 데이터 소스 사용 예시

.env 파일에서 설정을 읽어서 자동으로 데이터 소스 생성
"""
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def example_settings_based():
    """Settings 기반 자동 설정 (권장)"""
    print("\n" + "="*80)
    print("Settings 기반 데이터 소스 사용")
    print("="*80)
    
    # Settings에서 현재 설정 확인
    from backend.app.core.settings import settings
    
    print(f"\n현재 설정:")
    print(f"  - 데이터 소스 모드: {settings.DATA_SOURCE_MODE}")
    print(f"  - 데이터 디렉토리: {settings.DATA_DIR}")
    print(f"  - 파일 포맷: {settings.REVIEW_FILE_FORMAT}")
    
    if settings.DATA_SOURCE_MODE in ["database", "hybrid"]:
        print(f"  - DB 호스트: {settings.DB_HOST}")
        print(f"  - DB 포트: {settings.DB_PORT}")
        print(f"  - DB 이름: {settings.DB_NAME}")
        print(f"  - DB 사용자: {settings.DB_USER}")
        print(f"  - 컨넥션 풀: {settings.DB_POOL_MIN_SIZE}~{settings.DB_POOL_MAX_SIZE}")
    
    # Settings 기반 데이터 소스 생성
    from backend.app.infra.database import get_data_source
    
    data_source = get_data_source(use_settings=True)
    
    print(f"\n✓ 데이터 소스 생성 완료: {type(data_source).__name__}")
    
    # 헬스체크
    is_healthy = data_source.health_check()
    print(f"✓ 헬스체크: {'정상' if is_healthy else '오류'}")
    
    # 리뷰 조회 테스트
    try:
        reviews_df = data_source.get_reviews_by_category(
            category="coffee_machine",
            limit=5
        )
        print(f"✓ 리뷰 조회 테스트: {len(reviews_df)}건")
    except Exception as e:
        print(f"⚠️  리뷰 조회 테스트 실패: {e}")


def example_config_inspection():
    """설정 상세 조회"""
    print("\n" + "="*80)
    print("설정 상세 조회")
    print("="*80)
    
    from backend.app.infra.database.config import DataSourceConfig
    
    # Settings에서 설정 로드
    config = DataSourceConfig.from_settings()
    
    print(f"\n{config.get_summary()}")
    
    # 유효성 검증
    is_valid = config.validate()
    print(f"\n✓ 설정 유효성: {'정상' if is_valid else '오류'}")


def example_dynamic_mode_switch():
    """동적 모드 전환 예시"""
    print("\n" + "="*80)
    print("동적 모드 전환 (테스트 환경)")
    print("="*80)
    
    from backend.app.infra.database import DataSourceFactory, set_data_source
    from backend.app.core.settings import settings
    
    print(f"\n현재 모드: {settings.DATA_SOURCE_MODE}")
    
    # 파일 모드로 강제 전환 (테스트용)
    print("\n파일 모드로 전환...")
    file_source = DataSourceFactory.create(
        mode="file",
        data_dir=settings.DATA_DIR,
        file_format=settings.REVIEW_FILE_FORMAT
    )
    set_data_source(file_source)
    print("✓ 파일 모드 전환 완료")
    
    # DB 연결이 가능하면 DB 모드로 전환
    try:
        from backend.app.infra.database import db_pool
        
        db_pool.initialize(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD
        )
        
        if db_pool.health_check():
            print("\n✓ DB 연결 확인됨")
            
            # 하이브리드 모드로 전환
            print("\n하이브리드 모드로 전환...")
            hybrid_source = DataSourceFactory.create(
                mode="hybrid",
                data_dir=settings.DATA_DIR,
                file_format=settings.REVIEW_FILE_FORMAT,
                db_config={
                    "host": settings.DB_HOST,
                    "port": settings.DB_PORT,
                    "database": settings.DB_NAME,
                    "user": settings.DB_USER,
                    "password": settings.DB_PASSWORD,
                    "min_size": settings.DB_POOL_MIN_SIZE,
                    "max_size": settings.DB_POOL_MAX_SIZE
                }
            )
            set_data_source(hybrid_source)
            print("✓ 하이브리드 모드 전환 완료")
        
        db_pool.close()
        
    except Exception as e:
        print(f"\n⚠️  DB 연결 불가: {e}")
        print("파일 모드 유지")


def main():
    """모든 예시 실행"""
    print("\n" + "="*80)
    print("Settings 기반 데이터 소스 사용 예시")
    print("="*80)
    
    try:
        # 1. Settings 기반 사용 (권장)
        example_settings_based()
        
        # 2. 설정 상세 조회
        example_config_inspection()
        
        # 3. 동적 모드 전환
        example_dynamic_mode_switch()
        
        print("\n" + "="*80)
        print("✓ 모든 예시 완료")
        print("="*80)
        print("\n💡 .env 파일을 수정하여 설정 변경 가능")
        print("   - DATA_SOURCE_MODE: file / database / hybrid")
        print("   - DB_HOST, DB_PORT, DB_NAME 등 DB 설정")
        print("")
        
    except Exception as e:
        logger.error(f"예시 실행 중 오류: {e}", exc_info=True)


if __name__ == "__main__":
    main()
