"""Factor 분석 모듈"""
import re
import csv
from pathlib import Path
from typing import List, Dict, Any


class FactorAnalyzer:
    """리뷰에서 factor별 anchor_terms를 포함한 문장 추출"""
    
    def __init__(self, category: str, data_dir: Path = Path("backend/data")):
        self.category = category
        self.factors = self._load_factors(data_dir)
    
    def _load_factors(self, data_dir: Path) -> List[Dict[str, Any]]:
        """reg_factor.csv에서 해당 카테고리의 factor 로드"""
        factor_file = data_dir / "factor" / "reg_factor.csv"
        factors = []
        
        with open(factor_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['category'] == self.category:
                    factors.append({
                        'factor_key': row['factor_key'],
                        'display_name': row['display_name'],
                        'anchor_terms': row['anchor_terms'].split('|'),
                        'weight': float(row.get('weight', 1.0))
                    })
        
        return factors
    
    def extract_sentences(self, text: str) -> List[str]:
        """텍스트를 문장 단위로 분리"""
        # 문장 구분자: 마침표, 느낌표, 물음표, 줄바꿈
        sentences = re.split(r'[.!?\n]+', text)
        # 빈 문장 제거 및 앞뒤 공백 제거
        return [s.strip() for s in sentences if s.strip()]
    
    def analyze_review(self, review_text: str) -> List[Dict[str, Any]]:
        """
        리뷰에서 각 factor별 anchor_terms를 포함한 문장 추출
        
        Returns:
            [
                {
                    'factor_key': 'noise_sleep',
                    'display_name': '수면 중 소음/눈부심',
                    'sentences': ['소음이 심해요', '잠잘 때 시끄러워요'],
                    'matched_terms': ['소음', '시끄럽']
                },
                ...
            ]
        """
        sentences = self.extract_sentences(review_text)
        results = []
        
        for factor in self.factors:
            matched_sentences = []
            matched_terms = set()
            
            for sentence in sentences:
                # 해당 문장에 anchor_terms가 있는지 확인
                for term in factor['anchor_terms']:
                    if term in sentence:
                        matched_sentences.append(sentence)
                        matched_terms.add(term)
                        break  # 한 문장은 한 번만 추가
            
            if matched_sentences:
                results.append({
                    'factor_key': factor['factor_key'],
                    'display_name': factor['display_name'],
                    'sentences': matched_sentences,
                    'matched_terms': list(matched_terms),
                    'weight': factor['weight']
                })
        
        return results
