#!/usr/bin/env python3
"""
LLM 응답 평가 데이터 분석 스크립트

평가 데이터를 수집하여 전략별 통계를 제공하고,
최적의 프롬프트 전략을 추천합니다.
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple
import sys


def load_rating_data(out_dir: Path) -> Tuple[Dict[str, List[int]], Dict[str, List[str]]]:
    """평가 데이터 로드
    
    Returns:
        (ratings, feedbacks): 전략별 평점 리스트와 피드백 리스트
    """
    ratings = defaultdict(list)
    feedbacks = defaultdict(list)
    
    response_files = list(out_dir.glob("llm_response_*.json"))
    
    if not response_files:
        print(f"⚠️  경고: {out_dir}에 응답 파일이 없습니다")
        return ratings, feedbacks
    
    print(f"📁 {len(response_files)}개 응답 파일 발견\n")
    
    for response_file in response_files:
        try:
            with open(response_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 메타데이터에서 전략 확인
            strategy = data.get("_metadata", {}).get("strategy", "default")
            
            # 평가 데이터 추출
            user_ratings = data.get("_user_rating", {})
            
            for strat, rating_data in user_ratings.items():
                rating = rating_data.get("rating")
                if rating is not None:
                    ratings[strat].append(rating)
                    
                    if "feedback" in rating_data:
                        feedbacks[strat].append(rating_data["feedback"])
        
        except Exception as e:
            print(f"⚠️  경고: {response_file.name} 로드 실패: {e}")
    
    return ratings, feedbacks


def calculate_statistics(ratings: List[int]) -> Dict:
    """통계 계산"""
    if not ratings:
        return {
            "count": 0,
            "avg": 0.0,
            "max": 0,
            "min": 0,
            "distribution": {}
        }
    
    distribution = {i: ratings.count(i) for i in range(1, 6)}
    
    return {
        "count": len(ratings),
        "avg": sum(ratings) / len(ratings),
        "max": max(ratings),
        "min": min(ratings),
        "distribution": distribution
    }


def print_statistics(ratings: Dict[str, List[int]], feedbacks: Dict[str, List[str]]):
    """통계 출력"""
    if not ratings:
        print("❌ 평가 데이터가 없습니다")
        return
    
    print("=" * 70)
    print("📊 LLM 응답 평가 통계")
    print("=" * 70)
    print()
    
    # 전략별 통계
    stats = {}
    for strategy in sorted(ratings.keys()):
        rating_list = ratings[strategy]
        feedback_list = feedbacks.get(strategy, [])
        
        stats[strategy] = calculate_statistics(rating_list)
        
        print(f"🎯 전략: {strategy}")
        print(f"   {'평가 수:':15} {stats[strategy]['count']}")
        print(f"   {'평균 별점:':15} {stats[strategy]['avg']:.2f} ⭐")
        print(f"   {'최고 별점:':15} {stats[strategy]['max']}")
        print(f"   {'최저 별점:':15} {stats[strategy]['min']}")
        print(f"   {'피드백 수:':15} {len(feedback_list)}")
        
        # 별점 분포
        print(f"   별점 분포:")
        for star in range(5, 0, -1):
            count = stats[strategy]['distribution'].get(star, 0)
            percentage = (count / stats[strategy]['count'] * 100) if stats[strategy]['count'] > 0 else 0
            bar = "█" * int(percentage / 5)
            print(f"      {star}⭐: {bar:20} {count:3}개 ({percentage:5.1f}%)")
        
        print()
    
    # 최고 전략 추천
    if stats:
        best_strategy = max(stats.keys(), key=lambda s: stats[s]['avg'])
        best_avg = stats[best_strategy]['avg']
        
        print("=" * 70)
        print(f"✅ 추천 전략: {best_strategy}")
        print(f"   평균 별점: {best_avg:.2f} ⭐")
        print(f"   평가 수: {stats[best_strategy]['count']}")
        print("=" * 70)
        print()
        
        # 대표 피드백
        if feedbacks.get(best_strategy):
            print(f"💬 '{best_strategy}' 전략 대표 피드백:")
            for i, feedback in enumerate(feedbacks[best_strategy][:5], 1):
                print(f"   {i}. \"{feedback}\"")
            print()


def print_comparison_table(ratings: Dict[str, List[int]]):
    """전략 비교 테이블 출력"""
    if len(ratings) < 2:
        return
    
    print("=" * 70)
    print("📈 전략 비교")
    print("=" * 70)
    print()
    
    strategies = sorted(ratings.keys())
    
    # 헤더
    print(f"{'전략':15} {'평가 수':>10} {'평균':>10} {'최고':>8} {'최저':>8}")
    print("-" * 70)
    
    # 각 전략
    for strategy in strategies:
        stats = calculate_statistics(ratings[strategy])
        print(f"{strategy:15} {stats['count']:>10} {stats['avg']:>10.2f} {stats['max']:>8} {stats['min']:>8}")
    
    print()


def export_to_csv(ratings: Dict[str, List[int]], feedbacks: Dict[str, List[str]], output_file: Path):
    """CSV로 내보내기"""
    try:
        import csv
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['전략', '평가 수', '평균 별점', '최고 별점', '최저 별점', '피드백 수'])
            
            for strategy in sorted(ratings.keys()):
                stats = calculate_statistics(ratings[strategy])
                feedback_count = len(feedbacks.get(strategy, []))
                
                writer.writerow([
                    strategy,
                    stats['count'],
                    f"{stats['avg']:.2f}",
                    stats['max'],
                    stats['min'],
                    feedback_count
                ])
        
        print(f"💾 CSV 파일 저장: {output_file}")
        
    except Exception as e:
        print(f"⚠️  CSV 저장 실패: {e}")


def main():
    """메인 함수"""
    out_dir = Path("out")
    
    if not out_dir.exists():
        print(f"❌ 오류: {out_dir} 디렉토리가 없습니다")
        sys.exit(1)
    
    # 데이터 로드
    ratings, feedbacks = load_rating_data(out_dir)
    
    if not ratings:
        print("\n❌ 평가 데이터가 없습니다")
        print("\n사용법:")
        print("1. LLM 응답 생성 (analyze-product API 호출)")
        print("2. 응답 평가 (rate-response API 호출)")
        print("3. 이 스크립트 실행")
        sys.exit(0)
    
    # 통계 출력
    print_statistics(ratings, feedbacks)
    
    # 비교 테이블
    print_comparison_table(ratings)
    
    # CSV 내보내기
    csv_file = out_dir / "rating_statistics.csv"
    export_to_csv(ratings, feedbacks, csv_file)
    
    print()
    print("✨ 분석 완료!")


if __name__ == "__main__":
    main()
