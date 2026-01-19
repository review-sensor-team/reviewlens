"""데이터 소스 사용 예시

파일 기반 → DB 기반 → 하이브리드 모드 전환 예시
"""
import logging
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def example_file_mode():
    """파일 모드 예시 - 기존 방식"""
    print("\n" + "="*80)
    print("1. 파일 모드 (기존 방식)")
    print("="*80)
    
    from backend.app.infra.database import DataSourceFactory
    
    # 파일 기반 데이터 소스 생성
    data_source = DataSourceFactory.create(
        mode="file",
        data_dir="backend/data",
        file_format="json"
    )
    
    # 리뷰 조회
    reviews_df = data_source.get_reviews_by_category(
        category="coffee_machine",
        limit=10
    )
    
    print(f"✓ 리뷰 조회: {len(reviews_df)}건")
    
    # 요인 조회
    factors_df = data_source.get_factors_by_category(category="coffee_machine")
    print(f"✓ 요인 조회: {len(factors_df)}건")
    
    # 헬스체크
    is_healthy = data_source.health_check()
    print(f"✓ 헬스체크: {'정상' if is_healthy else '오류'}")


def example_database_mode():
    """DB 모드 예시 - 완전 전환"""
    print("\n" + "="*80)
    print("2. DB 모드 (완전 전환)")
    print("="*80)
    
    from backend.app.infra.database import DataSourceFactory
    
    # DB 기반 데이터 소스 생성
    data_source = DataSourceFactory.create(
        mode="database",
        db_config={
            "host": "localhost",
            "port": 5432,
            "database": "reviewlens",
            "user": "reviewlens",
            "password": "reviewlens",
            "min_size": 2,
            "max_size": 10
        }
    )
    
    # 리뷰 조회
    reviews_df = data_source.get_reviews_by_category(
        category="coffee_machine",
        limit=10
    )
    
    print(f"✓ 리뷰 조회: {len(reviews_df)}건")
    
    # 요인 조회
    factors_df = data_source.get_factors_by_category(
        category="coffee_machine",
        version="v4"  # 특정 버전 지정 가능
    )
    print(f"✓ 요인 조회: {len(factors_df)}건")
    
    # 헬스체크
    is_healthy = data_source.health_check()
    print(f"✓ 헬스체크: {'정상' if is_healthy else '오류'}")


def example_hybrid_mode():
    """하이브리드 모드 예시 - 안전한 마이그레이션"""
    print("\n" + "="*80)
    print("3. 하이브리드 모드 (마이그레이션 중)")
    print("="*80)
    
    from backend.app.infra.database import DataSourceFactory
    
    # 하이브리드 데이터 소스 생성 (파일 + DB)
    data_source = DataSourceFactory.create(
        mode="hybrid",
        data_dir="backend/data",
        file_format="json",
        db_config={
            "host": "localhost",
            "port": 5432,
            "database": "reviewlens",
            "user": "reviewlens",
            "password": "reviewlens"
        }
    )
    
    print("✓ 하이브리드 데이터 소스 생성 완료")
    print("  - 읽기: DB 우선, 실패시 파일 폴백")
    print("  - 쓰기: 파일과 DB 모두 저장")
    
    # 리뷰 조회 (DB 우선, 실패시 파일)
    reviews_df = data_source.get_reviews_by_category(
        category="coffee_machine",
        limit=10
    )
    print(f"\n✓ 리뷰 조회: {len(reviews_df)}건")
    
    # 리뷰 저장 (파일 + DB 동시 저장)
    if len(reviews_df) > 0:
        result = data_source.save_reviews(
            reviews_df=reviews_df.head(5),
            metadata={
                "vendor": "smartstore",
                "product_id": "test_product",
                "category": "coffee_machine",
                "source_type": "test"
            }
        )
        print(f"✓ 리뷰 저장: {'성공' if result else '실패'}")
    
    # 헬스체크 (파일 또는 DB 중 하나라도 정상이면 OK)
    is_healthy = data_source.health_check()
    print(f"✓ 헬스체크: {'정상' if is_healthy else '오류'}")


def example_env_based():
    """환경 변수 기반 설정 예시"""
    print("\n" + "="*80)
    print("4. 환경 변수 기반 설정")
    print("="*80)
    
    import os
    
    # 환경 변수 설정
    os.environ["DATA_SOURCE_MODE"] = "hybrid"
    os.environ["DATA_DIR"] = "backend/data"
    os.environ["FILE_FORMAT"] = "json"
    os.environ["DB_HOST"] = "localhost"
    os.environ["DB_NAME"] = "reviewlens"
    os.environ["DB_USER"] = "reviewlens"
    os.environ["DB_PASSWORD"] = "reviewlens"
    
    from backend.app.infra.database import get_data_source
    
    # 환경 변수에서 자동으로 설정 로드
    data_source = get_data_source()
    
    print("✓ 환경 변수 기반 데이터 소스 생성 완료")
    print(f"  - 모드: {os.environ['DATA_SOURCE_MODE']}")
    print(f"  - 데이터 디렉토리: {os.environ['DATA_DIR']}")
    print(f"  - DB: {os.environ['DB_HOST']}/{os.environ['DB_NAME']}")
    
    # 헬스체크
    is_healthy = data_source.health_check()
    print(f"\n✓ 헬스체크: {'정상' if is_healthy else '오류'}")


def example_connection_pool_direct():
    """컨넥션 풀 직접 사용 예시"""
    print("\n" + "="*80)
    print("5. 컨넥션 풀 직접 사용")
    print("="*80)
    
    from backend.app.infra.database import db_pool
    
    # 컨넥션 풀 초기화
    db_pool.initialize(
        host="localhost",
        port=5432,
        database="reviewlens",
        user="reviewlens",
        password="reviewlens",
        min_size=2,
        max_size=10
    )
    
    print("✓ 컨넥션 풀 초기화 완료")
    
    # 헬스체크
    is_healthy = db_pool.health_check()
    print(f"✓ 헬스체크: {'정상' if is_healthy else '오류'}")
    
    # 풀 통계
    stats = db_pool.get_pool_stats()
    print(f"✓ 풀 통계: {stats}")
    
    # 직접 쿼리 실행
    try:
        results = db_pool.execute_query(
            "SELECT category_slug, category_name FROM category LIMIT 5",
            fetch="all"
        )
        print(f"\n✓ 카테고리 조회: {len(results)}건")
        for row in results:
            print(f"  - {row['category_slug']}: {row['category_name']}")
    except Exception as e:
        print(f"✗ 쿼리 실행 실패: {e}")
    
    # 컨텍스트 관리자로 안전한 커넥션 사용
    try:
        with db_pool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) as cnt FROM review")
                row = cur.fetchone()
                print(f"\n✓ 전체 리뷰 수: {row['cnt']}건")
    except Exception as e:
        print(f"✗ 커넥션 사용 실패: {e}")
    
    # 컨넥션 풀 종료
    db_pool.close()
    print("\n✓ 컨넥션 풀 종료 완료")


def example_migration_scenario():
    """마이그레이션 시나리오 예시"""
    print("\n" + "="*80)
    print("6. 마이그레이션 시나리오")
    print("="*80)
    
    from backend.app.infra.database import DataSourceFactory, set_data_source
    
    # Phase 1: 파일만 사용 (현재 상태)
    print("\n[Phase 1] 파일만 사용 (현재)")
    file_source = DataSourceFactory.create(
        mode="file",
        data_dir="backend/data",
        file_format="json"
    )
    set_data_source(file_source)
    print("✓ 파일 기반 운영 중")
    
    # Phase 2: 하이브리드 모드로 전환 (마이그레이션 시작)
    print("\n[Phase 2] 하이브리드 모드 (마이그레이션 중)")
    hybrid_source = DataSourceFactory.create(
        mode="hybrid",
        data_dir="backend/data",
        file_format="json",
        db_config={
            "host": "localhost",
            "database": "reviewlens",
            "user": "reviewlens",
            "password": "reviewlens"
        }
    )
    set_data_source(hybrid_source)
    print("✓ 하이브리드 모드 전환 완료")
    print("  - 기존 파일 데이터 유지")
    print("  - 새 데이터는 파일 + DB 동시 저장")
    print("  - DB 우선 조회, 실패시 파일 폴백")
    
    # Phase 3: DB만 사용 (마이그레이션 완료)
    print("\n[Phase 3] DB만 사용 (마이그레이션 완료)")
    db_source = DataSourceFactory.create(
        mode="database",
        db_config={
            "host": "localhost",
            "database": "reviewlens",
            "user": "reviewlens",
            "password": "reviewlens"
        }
    )
    set_data_source(db_source)
    print("✓ DB 기반 전환 완료")
    print("  - 모든 데이터 DB에서 조회")
    print("  - 파일 시스템은 백업용으로만 사용")


def main():
    """모든 예시 실행"""
    print("\n" + "="*80)
    print("데이터 소스 사용 예시")
    print("="*80)
    
    try:
        # 1. 파일 모드
        example_file_mode()
        
        # 2. DB 모드 (DB가 없으면 스킵)
        try:
            example_database_mode()
        except Exception as e:
            print(f"\n⚠️  DB 모드 스킵 (DB 미설정): {e}")
        
        # 3. 하이브리드 모드
        try:
            example_hybrid_mode()
        except Exception as e:
            print(f"\n⚠️  하이브리드 모드 스킵: {e}")
        
        # 4. 환경 변수 기반
        example_env_based()
        
        # 5. 컨넥션 풀 직접 사용
        try:
            example_connection_pool_direct()
        except Exception as e:
            print(f"\n⚠️  컨넥션 풀 예시 스킵: {e}")
        
        # 6. 마이그레이션 시나리오
        example_migration_scenario()
        
        print("\n" + "="*80)
        print("✓ 모든 예시 완료")
        print("="*80)
        
    except Exception as e:
        logger.error(f"예시 실행 중 오류: {e}", exc_info=True)


if __name__ == "__main__":
    main()
