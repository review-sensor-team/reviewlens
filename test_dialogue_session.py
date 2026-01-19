#!/usr/bin/env python3
"""DialogueSession 데이터 소스 통합 테스트"""

def test_dialogue_session():
    """DialogueSession이 데이터 소스를 올바르게 사용하는지 테스트"""
    print("=" * 80)
    print("DialogueSession 데이터 소스 통합 테스트")
    print("=" * 80)
    
    try:
        # Settings 로드
        print("\n1. Settings 로드 중...")
        from backend.app.core.settings import settings
        print(f"   ✓ 데이터 소스 모드: {settings.DATA_SOURCE_MODE}")
        print(f"   ✓ 데이터 디렉토리: {settings.DATA_DIR}")
        
        # DialogueSession import
        print("\n2. DialogueSession 임포트 중...")
        from backend.app.usecases.dialogue.session import DialogueSession
        print("   ✓ DialogueSession 임포트 성공")
        
        # 데이터 소스로 데이터 확인
        print("\n3. 데이터 소스에서 데이터 확인 중...")
        from backend.app.infra.database import get_data_source
        data_source = get_data_source()
        
        category = "coffee_machine"
        factors_df = data_source.get_factors_by_category(category)
        questions_df = data_source.get_questions_by_category(category)
        print(f"   ✓ {category}: {len(factors_df)}개 factors, {len(questions_df)}개 questions")
        
        # DialogueSession 생성 (리뷰 없이)
        print("\n4. DialogueSession 생성 중 (리뷰 없음)...")
        session = DialogueSession(
            category=category,
            data_dir=settings.DATA_DIR
        )
        print(f"   ✓ 세션 생성 성공")
        print(f"   ✓ Factors: {len(session.factors)}개")
        print(f"   ✓ Questions: {len(session.questions)}개")
        print(f"   ✓ Reviews: {len(session.reviews_df)}건")
        
        # Factor 데이터 검증
        print("\n5. Factor 데이터 검증 중...")
        if session.factors:
            sample_factor = session.factors[0]
            print(f"   ✓ 샘플 factor_key: {sample_factor.factor_key}")
            print(f"   ✓ 샘플 display_name: {sample_factor.display_name}")
            print(f"   ✓ 샘플 category: {sample_factor.category}")
        
        # Question 데이터 검증
        print("\n6. Question 데이터 검증 중...")
        if session.questions:
            sample_question = session.questions[0]
            print(f"   ✓ 샘플 question_text: {sample_question.question_text[:50]}...")
            print(f"   ✓ 샘플 factor_id: {sample_question.factor_id}")
        
        print("\n" + "=" * 80)
        print("✓ 테스트 완료 - DialogueSession이 데이터 소스를 정상적으로 사용합니다")
        print("=" * 80)
        
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"✗ 테스트 실패: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_dialogue_session()
    exit(0 if success else 1)
