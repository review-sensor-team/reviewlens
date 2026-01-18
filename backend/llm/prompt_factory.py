"""
프롬프트 팩토리 - 다양한 프롬프트 전략을 쉽게 전환할 수 있게 해주는 모듈

사용 예시:
    # 기본 전략 사용
    factory = PromptFactory.create()
    system_prompt = factory.build_system_prompt()
    
    # 다른 전략으로 전환
    factory = PromptFactory.create(strategy="detailed")
    
    # 커스텀 전략 파일 사용
    factory = PromptFactory.create(strategy_file="custom_prompt.yaml")
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml

logger = logging.getLogger(__name__)


class PromptStrategy:
    """프롬프트 전략 클래스 - YAML 템플릿 기반"""
    
    def __init__(self, template_data: Dict[str, Any]):
        """
        Args:
            template_data: YAML에서 로드된 템플릿 데이터
        """
        self.name = template_data.get("name", "unknown")
        self.description = template_data.get("description", "")
        self.version = template_data.get("version", "1.0")
        self.system_prompt_template = template_data.get("system_prompt", "")
        self.user_prompt_template = template_data.get("user_prompt_template", "")
        self.fallback_template = template_data.get("fallback_template", "")
    
    def build_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        return self.system_prompt_template.strip()
    
    def build_user_prompt(
        self,
        top_factors: List[tuple],
        evidence_reviews: List[Dict[str, Any]],
        total_turns: int,
        category_name: str,
        product_name: str,
        dialogue_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """유저 프롬프트 생성
        
        Args:
            top_factors: [(factor_key, score), ...] 상위 후회 요인
            evidence_reviews: 증거 리뷰 리스트
            total_turns: 총 대화 턴 수
            category_name: 제품 카테고리명
            product_name: 제품명
            dialogue_history: 대화 내역
            
        Returns:
            생성된 유저 프롬프트
        """
        # 1) factors_list 포맷팅
        factors_list = self._format_factors(top_factors)
        
        # 2) dialogue_section 포맷팅
        dialogue_section = self._format_dialogue(dialogue_history) if dialogue_history else ""
        
        # 3) evidence_reviews 포맷팅
        evidence_text = self._format_evidence(evidence_reviews)
        
        # 4) 템플릿에 데이터 주입
        user_prompt = self.user_prompt_template.format(
            category_name=category_name,
            product_name=product_name,
            total_turns=total_turns,
            factors_list=factors_list,
            evidence_reviews=evidence_text,
            evidence_count=len(evidence_reviews),
            dialogue_section=dialogue_section
        )
        
        return user_prompt.strip()
    
    def build_fallback(
        self,
        top_factors: List[tuple],
        category_name: str,
        product_name: str
    ) -> str:
        """API 실패 시 기본 요약
        
        Args:
            top_factors: 상위 후회 요인
            category_name: 카테고리명
            product_name: 제품명
            
        Returns:
            Fallback 응답
        """
        factors_text = ", ".join([f"{key}" for key, _ in top_factors[:3]])
        top_factor = top_factors[0][0] if top_factors else "알 수 없음"
        
        fallback = self.fallback_template.format(
            product_name=product_name,
            category_name=category_name,
            factors_text=factors_text,
            top_factor=top_factor
        )
        
        return fallback.strip()
    
    def _format_factors(self, top_factors: List[tuple]) -> str:
        """상위 요인 포맷팅"""
        return "\n".join([
            f"{i+1}. {factor_key} (점수: {score:.2f})"
            for i, (factor_key, score) in enumerate(top_factors[:5])
        ])
    
    def _format_dialogue(self, dialogue_history: List[Dict[str, str]]) -> str:
        """대화 내용 포맷팅"""
        if not dialogue_history:
            return ""
        
        dialogue_lines = []
        for turn in dialogue_history:
            role = turn.get('role', '')
            text = turn.get('message', '')
            if role == 'user':
                dialogue_lines.append(f"사용자: {text}")
            elif role == 'assistant':
                dialogue_lines.append(f"어시스턴트: {text}")
        
        dialogue_text = "\n".join(dialogue_lines)
        return f"**대화 내용**\n{dialogue_text}\n"
    
    def _format_evidence(self, evidence_reviews: List[Dict[str, Any]]) -> str:
        """증거 리뷰 포맷팅"""
        evidence_lines = []
        for i, rev in enumerate(evidence_reviews, 1):
            label = rev.get('label', 'NEU')
            rating = rev.get('rating', 0)
            excerpt = rev.get('excerpt', '')
            evidence_lines.append(f"{i}. [{label}] {rating}점 - {excerpt}")
        
        return "\n".join(evidence_lines)


class PromptFactory:
    """프롬프트 팩토리 - 다양한 전략을 쉽게 생성"""
    
    # 기본 프롬프트 디렉토리
    DEFAULT_PROMPTS_DIR = Path(__file__).parent / "prompts"
    
    @classmethod
    def create(
        cls,
        strategy: str = "default",
        strategy_file: Optional[str] = None,
        prompts_dir: Optional[Path] = None
    ) -> PromptStrategy:
        """프롬프트 전략 생성
        
        Args:
            strategy: 전략 이름 (default|concise|detailed|friendly)
            strategy_file: 커스텀 전략 파일 경로 (YAML)
            prompts_dir: 프롬프트 디렉토리 경로
            
        Returns:
            PromptStrategy 인스턴스
        """
        # 1) 파일 경로 결정
        if strategy_file:
            template_path = Path(strategy_file)
        else:
            template_dir = prompts_dir or cls.DEFAULT_PROMPTS_DIR
            template_path = template_dir / f"{strategy}.yaml"
        
        # 2) YAML 로드
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = yaml.safe_load(f)
            
            logger.info(f"[PromptFactory] 전략 로드: {template_data.get('name', 'unknown')} v{template_data.get('version', '1.0')}")
            logger.info(f"  - 설명: {template_data.get('description', 'N/A')}")
            logger.info(f"  - 파일: {template_path}")
            
            return PromptStrategy(template_data)
            
        except FileNotFoundError:
            logger.error(f"[PromptFactory] 전략 파일 없음: {template_path}")
            logger.info(f"  - 사용 가능한 전략: {cls.list_available_strategies()}")
            logger.info(f"  - 기본 전략으로 fallback")
            
            # Fallback to default
            return cls._create_default_strategy()
        
        except yaml.YAMLError as e:
            logger.error(f"[PromptFactory] YAML 파싱 오류: {e}")
            return cls._create_default_strategy()
    
    @classmethod
    def list_available_strategies(cls, prompts_dir: Optional[Path] = None) -> List[str]:
        """사용 가능한 전략 목록 조회
        
        Args:
            prompts_dir: 프롬프트 디렉토리 경로
            
        Returns:
            전략 이름 리스트
        """
        template_dir = prompts_dir or cls.DEFAULT_PROMPTS_DIR
        
        if not template_dir.exists():
            return []
        
        strategies = []
        for yaml_file in template_dir.glob("*.yaml"):
            strategies.append(yaml_file.stem)
        
        return sorted(strategies)
    
    @classmethod
    def _create_default_strategy(cls) -> PromptStrategy:
        """하드코딩된 기본 전략 (파일 없을 때 fallback)"""
        default_template = {
            "name": "hardcoded_default",
            "description": "하드코딩된 기본 프롬프트 (fallback)",
            "version": "1.0",
            "system_prompt": """당신은 제품 리뷰 분석 전문가입니다. 
구매자들의 후회 요인을 분석하여 실용적이고 구체적인 조언을 제공합니다.
친근하지만 전문적인 톤으로, JSON 형식의 구조화된 분석 결과를 작성합니다.""",
            "user_prompt_template": """**제품 정보**
- 카테고리: {category_name}
- 제품명: {product_name}
- 분석 대화 턴: {total_turns}턴

{dialogue_section}

**주요 후회 요인 (상위 5개)**
{factors_list}

**증거 리뷰 전체 ({evidence_count}개)**
{evidence_reviews}

다음 JSON 형식으로 최종 분석 결과를 작성해주세요:
{{
  "summary": "핵심 후회 요인 설명 (2-3문장)",
  "key_findings": [
    {{
      "factor": "요인명",
      "risk_level": "high|mid|low",
      "what_users_say": "구매자들이 말하는 내용 (2-3문장)"
    }}
  ],
  "balanced_view": {{
    "pros": [{{"point": "장점"}}],
    "cons": [{{"point": "단점"}}],
    "mixed": [{{"point": "상황에 따라 다름"}}]
  }},
  "decision_rule": {{
    "if_buy": ["구매를 고려해도 좋은 경우"],
    "if_hold": ["보류가 나은 경우"]
  }},
  "final_recommendation": "구매|보류|조건부 추천",
  "one_line_tip": "한 줄 조언"
}}

**중요**: 반드시 유효한 JSON 형식으로만 응답하세요.""",
            "fallback_template": """{{
  "summary": "{product_name}의 주요 후회 요인은 {factors_text}입니다.",
  "key_findings": [{{"factor": "{top_factor}", "risk_level": "mid", "what_users_say": "구매자들이 이 부분에서 아쉬움을 느끼고 있습니다."}}],
  "balanced_view": {{"pros": [{{"point": "전반적인 품질은 양호합니다"}}], "cons": [{{"point": "{factors_text} 관련 불만이 있습니다"}}], "mixed": []}},
  "decision_rule": {{"if_buy": ["해당 요인이 본인에게 중요하지 않은 경우"], "if_hold": ["해당 요인이 본인에게 중요한 경우"]}},
  "final_recommendation": "조건부 추천",
  "one_line_tip": "후회 요인을 미리 알고 구매하면 실망을 줄일 수 있습니다!"
}}"""
        }
        
        return PromptStrategy(default_template)
