"""Factor 분석 모듈"""
import logging
import re
import csv
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger("collector.factor_analyzer")


def find_latest_versioned_file(root: Path, base_pattern: str) -> Path:
    """
    버전 번호가 포함된 파일 중 최신 버전을 찾음
    예: reg_factor_v4.csv, reg_factor_v3.csv -> reg_factor_v4.csv 선택
    """
    # 패턴에서 확장자 분리
    if base_pattern.endswith('.csv'):
        base_name = base_pattern[:-4]  # .csv 제거
        extension = '.csv'
    else:
        base_name = base_pattern
        extension = ''
    
    # 버전 없는 파일과 버전 있는 파일 모두 찾기
    pattern = f"{base_name}*.csv" if extension else f"{base_name}*"
    all_matches = list(root.rglob(pattern))
    
    if not all_matches:
        raise FileNotFoundError(f"No files found matching pattern: {pattern}")
    
    # 버전 정보 추출 및 정렬
    versioned_files = []
    base_file = None
    
    # 버전 패턴: _v숫자 형태
    version_pattern = re.compile(r'_v(\d+)(?:\.\w+)?$')
    
    for file_path in all_matches:
        stem = file_path.stem  # 확장자 제외한 파일명
        match = version_pattern.search(stem)
        
        if match:
            version = int(match.group(1))
            versioned_files.append((version, file_path))
        elif stem == base_name:
            base_file = file_path
    
    # 버전 파일이 있으면 최신 버전 반환
    if versioned_files:
        versioned_files.sort(key=lambda x: x[0], reverse=True)
        latest = versioned_files[0][1]
        logger.info(f"최신 버전 파일 선택: {latest.name} (v{versioned_files[0][0]})")
        return latest
    
    # 버전 파일이 없으면 기본 파일 반환
    if base_file:
        logger.info(f"기본 파일 사용: {base_file.name}")
        return base_file
    
    raise FileNotFoundError(f"No suitable file found for pattern: {base_pattern}")


class FactorAnalyzer:
    """리뷰에서 factor별 anchor_terms를 포함한 문장 추출"""
    
    def __init__(self, category: str, data_dir: Path = Path("backend/data")):
        logger.info(f"[FactorAnalyzer 초기화] category={category}")
        self.category = category
        self.factors = self._load_factors(data_dir)
        logger.debug(f"  - 로드된 factors: {len(self.factors)}개")
    
    def _load_factors(self, data_dir: Path) -> List[Dict[str, Any]]:
        """reg_factor.csv에서 해당 카테고리의 factor 로드 (최신 버전 자동 선택)"""
        factor_dir = data_dir / "factor"
        factor_file = find_latest_versioned_file(factor_dir, "reg_factor.csv")
        logger.info(f"  - factor 파일: {factor_file.name}")
        factors = []
        
        with open(factor_file, 'r', encoding='utf-8-sig') as f:  # BOM 제거를 위해 utf-8-sig 사용
            reader = csv.DictReader(f)
            for row in reader:
                # 빈 행 건너뛰기
                if not row or not row.get('category'):
                    continue
                    
                if row.get('category', '').strip() == self.category:
                    factor_id = row.get('factor_id', '').strip()
                    factor_key = row.get('factor_key', '').strip()
                    logger.debug(f"  로드: factor_id='{factor_id}', factor_key='{factor_key}', display_name='{row.get('display_name', '')}'")
                    factors.append({
                        'factor_id': int(factor_id) if factor_id else 0,
                        'factor_key': factor_key,
                        'display_name': row.get('display_name', '').strip(),
                        'anchor_terms': [t.strip() for t in row.get('anchor_terms', '').split('|') if t.strip()],
                        'context_terms': [t.strip() for t in row.get('context_terms', '').split('|') if t.strip()],
                        'weight': float(row.get('weight', 1.0))
                    })
        
        logger.info(f"  로드 완료: {len(factors)}개, 예시 factor_keys={[f['factor_key'] for f in factors[:3]]}")
        return factors
    
    def extract_sentences(self, text: str) -> List[str]:
        """텍스트를 문장 단위로 분리"""
        # 문장 구분자: 마침표, 느낌표, 물음표, 줄바꿈
        sentences = re.split(r'[.!?\n]+', text)
        # 빈 문장 제거 및 앞뒤 공백 제거
        return [s.strip() for s in sentences if s.strip()]
    
    def analyze_review(self, review_text: str) -> List[Dict[str, Any]]:
        """
        리뷰에서 각 factor별 anchor_terms를 포함한 문장 추출 (앞뒤 문장 포함, 최대 200자)
        
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
        logger.debug(f"[리뷰 분석] text_length={len(review_text)}")
        sentences = self.extract_sentences(review_text)
        results = []
        
        for factor in self.factors:
            matched_indices = set()
            matched_terms = set()
            
            # 1단계: 매칭되는 문장의 인덱스 찾기
            for idx, sentence in enumerate(sentences):
                # anchor_terms가 있는지 확인
                has_anchor = False
                for term in factor['anchor_terms']:
                    if term in sentence:
                        has_anchor = True
                        matched_terms.add(term)
                        break
                
                # anchor_term이 있으면 context_term도 체크
                if has_anchor:
                    # context_terms가 있는 경우만 context 체크 (없으면 anchor만으로 매칭)
                    if factor['context_terms']:
                        has_context = any(ctx in sentence for ctx in factor['context_terms'])
                        if has_context:
                            matched_indices.add(idx)
                    else:
                        # context_terms가 없으면 anchor만으로 매칭
                        matched_indices.add(idx)
            
            # 2단계: 매칭된 문장이 있으면 앞뒤 문장도 포함하여 최대 200자까지 수집
            if matched_indices:
                extended_sentences = []
                current_length = 0
                max_length = 200
                
                # 매칭된 인덱스를 정렬
                sorted_indices = sorted(matched_indices)
                
                # 각 매칭 그룹별로 앞뒤 문장 포함
                for matched_idx in sorted_indices:
                    group_sentences = []
                    group_length = 0
                    
                    # 매칭된 문장 먼저 추가
                    matched_sent = sentences[matched_idx]
                    group_sentences.append(matched_sent)
                    group_length += len(matched_sent)
                    
                    # 앞 문장 추가 (있으면)
                    if matched_idx > 0 and group_length < max_length:
                        prev_sent = sentences[matched_idx - 1]
                        if group_length + len(prev_sent) <= max_length:
                            group_sentences.insert(0, prev_sent)
                            group_length += len(prev_sent)
                    
                    # 뒷 문장 추가 (여유 있으면)
                    if matched_idx < len(sentences) - 1 and group_length < max_length:
                        next_sent = sentences[matched_idx + 1]
                        if group_length + len(next_sent) <= max_length:
                            group_sentences.append(next_sent)
                            group_length += len(next_sent)
                    
                    # 전체 문장 리스트에 추가 (중복 방지)
                    for sent in group_sentences:
                        if sent not in extended_sentences and current_length + len(sent) <= max_length:
                            extended_sentences.append(sent)
                            current_length += len(sent)
                
                results.append({
                    'factor_id': factor['factor_id'],
                    'factor_key': factor['factor_key'],
                    'display_name': factor['display_name'],
                    'sentences': extended_sentences,
                    'matched_terms': list(matched_terms),
                    'weight': factor['weight']
                })
        
        logger.debug(f"  - 매칭된 factors: {len(results)}개")
        return results
