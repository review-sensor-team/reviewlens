#!/usr/bin/env python3
"""
LLM 평가 시스템 테스트 스크립트

평가 API 엔드포인트를 테스트합니다.
"""

import json
import requests
from pathlib import Path
from datetime import datetime


def create_test_response_files():
    """테스트용 응답 파일 생성"""
    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 단일 전략 테스트 파일
    single_file = out_dir / f"llm_response_{timestamp}.json"
    single_data = {
        "analysis_summary": "이 제품은 음질과 착용감이 뛰어나지만 배터리 수명이 짧습니다.",
        "key_factors": [
            {"factor": "sound_quality", "score": 0.85},
            {"factor": "comfort", "score": 0.78}
        ],
        "_metadata": {
            "product_name": "테스트 이어폰",
            "timestamp": timestamp,
            "model": "claude-3-5-sonnet",
            "provider": "ClaudeLLMClient"
        }
    }
    
    with open(single_file, 'w', encoding='utf-8') as f:
        json.dump(single_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 단일 전략 테스트 파일 생성: {single_file.name}")
    
    # 다중 전략 테스트 파일
    strategies = ["default", "friendly", "concise"]
    multi_files = []
    
    for strategy in strategies:
        multi_file = out_dir / f"llm_response_{strategy}_{timestamp}.json"
        multi_data = {
            "analysis_summary": f"[{strategy}] 테스트 요약",
            "key_factors": [{"factor": "test", "score": 0.9}],
            "_metadata": {
                "product_name": "테스트 제품",
                "timestamp": timestamp,
                "model": "claude-3-5-sonnet",
                "provider": "ClaudeLLMClient",
                "strategy": strategy
            }
        }
        
        with open(multi_file, 'w', encoding='utf-8') as f:
            json.dump(multi_data, f, ensure_ascii=False, indent=2)
        
        multi_files.append(multi_file.name)
        print(f"✅ 다중 전략 테스트 파일 생성: {multi_file.name}")
    
    return single_file.name, multi_files


def test_rate_endpoint(base_url="http://localhost:8000"):
    """평가 API 엔드포인트 테스트"""
    
    print("\n" + "="*70)
    print("🧪 평가 API 테스트 시작")
    print("="*70 + "\n")
    
    # 1. 테스트 파일 생성
    print("1️⃣  테스트 응답 파일 생성 중...")
    single_file, multi_files = create_test_response_files()
    print()
    
    # 2. 단일 전략 평가 테스트
    print("2️⃣  단일 전략 평가 테스트...")
    rate_url = f"{base_url}/api/v2/reviews/rate-response"
    
    payload = {
        "response_file": single_file,
        "rating": 5,
        "feedback": "매우 명확하고 유용한 분석이었습니다"
    }
    
    try:
        response = requests.post(rate_url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ 성공: {result['message']}")
            print(f"   파일: {result['response_file']}")
            print(f"   별점: {result['rating']} ⭐")
        else:
            print(f"   ❌ 실패 (HTTP {response.status_code}): {response.text}")
    
    except requests.exceptions.ConnectionError:
        print(f"   ⚠️  서버 연결 실패: {base_url}")
        print(f"   서버가 실행 중인지 확인하세요")
    except Exception as e:
        print(f"   ❌ 오류: {e}")
    
    print()
    
    # 3. 다중 전략 평가 테스트
    print("3️⃣  다중 전략 평가 테스트...")
    
    for i, (file_name, strategy) in enumerate(zip(multi_files, ["default", "friendly", "concise"]), 1):
        payload = {
            "response_file": file_name,
            "rating": i + 2,  # 3, 4, 5
            "strategy": strategy,
            "feedback": f"{strategy} 전략 테스트 피드백"
        }
        
        try:
            response = requests.post(rate_url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ {strategy}: {result['rating']} ⭐")
            else:
                print(f"   ❌ {strategy}: HTTP {response.status_code}")
        
        except Exception as e:
            print(f"   ❌ {strategy}: {e}")
    
    print()
    
    # 4. 파일 검증
    print("4️⃣  평가 데이터 검증...")
    
    out_dir = Path("out")
    single_path = out_dir / single_file
    
    with open(single_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if "_user_rating" in data:
        rating_data = data["_user_rating"].get("default", {})
        print(f"   ✅ 평가 저장 확인: {rating_data.get('rating')} ⭐")
        print(f"   피드백: \"{rating_data.get('feedback')}\"")
    else:
        print(f"   ❌ 평가 데이터 없음")
    
    print()
    print("="*70)
    print("✨ 테스트 완료")
    print("="*70)


def test_invalid_requests(base_url="http://localhost:8000"):
    """잘못된 요청 테스트"""
    
    print("\n" + "="*70)
    print("🧪 오류 처리 테스트")
    print("="*70 + "\n")
    
    rate_url = f"{base_url}/api/v2/reviews/rate-response"
    
    test_cases = [
        {
            "name": "존재하지 않는 파일",
            "payload": {
                "response_file": "nonexistent.json",
                "rating": 5
            },
            "expected": 404
        },
        {
            "name": "잘못된 별점 (범위 초과)",
            "payload": {
                "response_file": "test.json",
                "rating": 10
            },
            "expected": 400
        },
        {
            "name": "잘못된 별점 (0)",
            "payload": {
                "response_file": "test.json",
                "rating": 0
            },
            "expected": 400
        }
    ]
    
    for test_case in test_cases:
        print(f"테스트: {test_case['name']}")
        
        try:
            response = requests.post(rate_url, json=test_case['payload'])
            
            if response.status_code == test_case['expected']:
                print(f"   ✅ 예상대로 HTTP {response.status_code} 반환")
            else:
                print(f"   ⚠️  예상: {test_case['expected']}, 실제: {response.status_code}")
        
        except Exception as e:
            print(f"   ❌ 오류: {e}")
        
        print()


if __name__ == "__main__":
    import sys
    
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    test_rate_endpoint(base_url)
    # test_invalid_requests(base_url)
