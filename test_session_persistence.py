"""세션 영속화 테스트"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.session.session_persistence import SessionPersistence
from backend.app.session.session_store import SessionStore
import pandas as pd

def test_persistence():
    print("=" * 60)
    print("세션 영속화 테스트")
    print("=" * 60)
    
    # SessionStore 생성
    print("\n1. SessionStore 생성 (영속화 활성화)")
    store = SessionStore(enable_persistence=True)
    print(f"   ✓ Persistence 활성화: {store.enable_persistence}")
    print(f"   ✓ 저장 디렉토리: {store.persistence.storage_dir.absolute()}")
    
    # 테스트 세션 생성
    print("\n2. 테스트 세션 생성")
    test_reviews = [
        {
            "review_id": "test1",
            "text": "좋아요",
            "rating": 5,
            "factor_matches": []
        },
        {
            "review_id": "test2",
            "text": "별로예요",
            "rating": 1,
            "factor_matches": []
        }
    ]
    
    session_id = store.create_session(
        category="test_category",
        data_dir=Path("backend/data"),
        reviews=test_reviews,
        product_name="테스트 상품",
        product_url="https://test.com/product/123"
    )
    
    print(f"   ✓ 세션 ID: {session_id}")
    
    # 파일 확인
    print("\n3. 저장 파일 확인")
    session_file = store.persistence.storage_dir / f"{session_id}.json"
    if session_file.exists():
        print(f"   ✓ 파일 생성됨: {session_file}")
        print(f"   ✓ 파일 크기: {session_file.stat().st_size} bytes")
        
        # 파일 내용 확인
        import json
        with open(session_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"   ✓ 저장된 데이터:")
        print(f"      - session_id: {data.get('session_id')}")
        print(f"      - product_name: {data.get('product_name')}")
        print(f"      - product_url: {data.get('product_url')}")
        print(f"      - category: {data.get('category')}")
        print(f"      - reviews: {len(data.get('reviews', []))}건")
    else:
        print(f"   ✗ 파일 없음: {session_file}")
    
    # 세션 복원 테스트
    print("\n4. 세션 복원 테스트")
    new_store = SessionStore(enable_persistence=True)
    restored_session = new_store.get_session(session_id)
    
    if restored_session:
        print(f"   ✓ 세션 복원 성공")
        print(f"      - 리뷰 수: {len(new_store._reviews.get(session_id, []))}")
        print(f"      - 메타데이터: {new_store._metadata.get(session_id)}")
    else:
        print(f"   ✗ 세션 복원 실패")
    
    # 정리
    print("\n5. 테스트 세션 삭제")
    store.persistence.delete_session(session_id)
    if not session_file.exists():
        print(f"   ✓ 파일 삭제됨")
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)

if __name__ == "__main__":
    test_persistence()
