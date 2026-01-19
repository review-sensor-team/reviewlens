#!/usr/bin/env python3
"""데이터 소스 빠른 테스트"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_data_source():
    """데이터 소스 기본 테스트"""
    print("=" * 80)
    print("데이터 소스 테스트")
    print("=" * 80)
    
    try:
        # Settings 로드
        print("\n1. Settings 로드 중...")
        from backend.app.core.settings import settings
        print(f"   ✓ 데이터 소스 모드: {settings.DATA_SOURCE_MODE}")
        print(f"   ✓ 데이터 디렉토리: {settings.DATA_DIR}")
        
        # 데이터 소스 생성
        print("\n2. 데이터 소스 생성 중...")
        from backend.app.infra.database import get_data_source
        data_source = get_data_source(use_settings=True)
        print(f"   ✓ 데이터 소스 타입: {type(data_source).__name__}")
        
        # 헬스체크
        print("\n3. 헬스체크 중...")
        is_healthy = data_source.health_check()
        print(f"   {'✓' if is_healthy else '✗'} 헬스체크: {'정상' if is_healthy else '오류'}")
        
        # 카테고리 예시로 데이터 조회
        print("\n4. 샘플 데이터 조회 중...")
        categories = ["coffee_machine", "electronics", "desk"]
        
        for category in categories:
            try:
                # Factors 조회
                factors_df = data_source.get_factors_by_category(category=category)
                if factors_df is not None and not factors_df.empty:
                    print(f"   ✓ {category}: {len(factors_df)}개 factors")
                    break
            except Exception as e:
                print(f"   - {category}: 조회 실패 ({e})")
        
        print("\n" + "=" * 80)
        print("✓ 테스트 완료")
        print("=" * 80)
        return True
        
    except Exception as e:
        print(f"\n✗ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_data_source()
    sys.exit(0 if success else 1)
