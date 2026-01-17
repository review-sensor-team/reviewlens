"""
Gemini LLM 클라이언트
"""
import logging
from typing import List, Dict, Any, Optional
from .llm_base import BaseLLMClient

logger = logging.getLogger(__name__)


class GeminiClient(BaseLLMClient):
    """Google Gemini API 클라이언트"""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash", temperature: float = 0.7, max_tokens: int = 2000):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        if not api_key:
            logger.warning("Gemini API key가 설정되지 않았습니다. 기본 메시지를 반환합니다.")
            self.client = None
        else:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.client = genai.GenerativeModel(model)
                logger.info(f"Gemini 클라이언트 초기화 완료: model={model}")
            except Exception as e:
                logger.error(f"Gemini 클라이언트 초기화 실패: {e}")
                self.client = None
    
    def generate_summary(
        self, 
        top_factors: List[tuple],
        evidence_reviews: List[Dict[str, Any]],
        total_turns: int,
        category_name: str,
        product_name: str = "이 제품",
        dialogue_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """최종 분석 요약 생성"""
        
        if not self.client:
            return self._get_fallback_summary(top_factors, category_name, product_name)
        
        # 프롬프트 구성
        prompt = self._build_prompt(top_factors, evidence_reviews, total_turns, category_name, product_name, dialogue_history)
        
        try:
            response = self.client.generate_content(
                prompt,
                generation_config={
                    "temperature": self.temperature,
                    "max_output_tokens": self.max_tokens,
                }
            )
            
            summary = response.text.strip()
            logger.info(f"Gemini 요약 생성 완료: {len(summary)}자")
            return summary
            
        except Exception as e:
            logger.error(f"Gemini API 호출 실패: {e}")
            return self._get_fallback_summary(top_factors, category_name, product_name)
    
    def _build_prompt(
        self,
        top_factors: List[tuple],
        evidence_reviews: List[Dict[str, Any]],
        total_turns: int,
        category_name: str,
        product_name: str,
        dialogue_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """프롬프트 구성"""
        
        # 상위 요인 정리
        factors_text = "\n".join([
            f"{i+1}. {factor_key} (점수: {score:.2f})"
            for i, (factor_key, score) in enumerate(top_factors[:5])
        ])
        
        # 대화 내용 정리
        dialogue_text = ""
        if dialogue_history:
            dialogue_lines = []
            for turn in dialogue_history:
                role = turn.get('role', '')
                text = turn.get('message', '')
                if role == 'user':
                    dialogue_lines.append(f"사용자: {text}")
                elif role == 'assistant':
                    dialogue_lines.append(f"어시스턴트: {text}")
            dialogue_text = "\n".join(dialogue_lines)
        
        # 모든 증거 리뷰 포함 (상위 5개가 아닌 전체)
        evidence_text = ""
        for i, rev in enumerate(evidence_reviews, 1):
            label = rev.get('label', 'NEU')
            rating = rev.get('rating', 0)
            excerpt = rev.get('excerpt', '')  # 전체 리뷰 내용 사용
            evidence_text += f"{i}. [{label}] {rating}점 - {excerpt}\n"
        
        # Prompt 구성
        prompt_parts = [
            "당신은 제품 리뷰 분석 전문가입니다.",
            "",
            "**제품 정보**",
            f"- 카테고리: {category_name}",
            f"- 제품명: {product_name}",
            f"- 분석 대화 턴: {total_turns}턴",
            ""
        ]
        
        if dialogue_text:
            prompt_parts.extend([
                "**대화 내용**",
                dialogue_text,
                ""
            ])
        
        prompt_parts.extend([
            "**주요 후회 요인 (상위 5개)**",
            factors_text,
            "",
            f"**증거 리뷰 전체 ({len(evidence_reviews)}개)**",
            evidence_text,
            "",
            "위 분석 결과를 바탕으로 **구매자에게 도움이 되는 최종 요약**을 작성해주세요.",
            "",
            "다음 형식으로 작성:",
            "1. 핵심 후회 요인 설명 (2-3문장)",
            "2. 구매 전 체크포인트 (3-5개 항목, 각 1-2문장)",
            "3. 한 줄 조언",
            "",
            "**톤앤매너**: 친근하지만 전문적, 구체적이고 실용적",
            "**길이**: 300-500자"
        ])
        
        prompt = "\n".join(prompt_parts)
        return prompt
    
    def _get_fallback_summary(self, top_factors: List[tuple], category_name: str, product_name: str) -> str:
        """API 실패 시 기본 요약"""
        
        factors_text = ", ".join([f"{key}" for key, _ in top_factors[:3]])
        
        return f"""🔍 **{product_name} 분석 완료**

**주요 후회 요인**: {factors_text}

위 요인들이 실제 구매자들이 가장 많이 후회한 부분입니다.

**구매 전 체크포인트**:
1. 해당 요인들이 본인에게 중요한지 확인하세요
2. 낮은 평점 리뷰에서 구체적인 불만 내용을 확인하세요
3. 유사 제품과 비교해보세요

💡 **조언**: 후회 요인을 미리 알고 구매하면 실망을 줄일 수 있습니다!
"""
