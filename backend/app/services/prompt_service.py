"""프롬프트 서비스 - LLM context 및 프롬프트 생성 (Service Layer)"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PromptService:
    """LLM 프롬프트 및 context 생성"""
    
    def __init__(self, version: str = "v2"):
        """
        Args:
            version: context schema version
        """
        self.version = version
        
    def build_llm_context(
        self,
        session_id: str,
        category: str,
        product_name: str,
        top_factors: List[Dict[str, Any]],
        evidence_reviews: List[Dict[str, Any]],
        next_questions: List[str],
        user_message: str = ""
    ) -> Dict[str, Any]:
        """LLM context JSON 생성
        
        Args:
            session_id: 세션 ID
            category: 제품 카테고리
            product_name: 제품명
            top_factors: 상위 factors [{"factor_key": str, "score": float, "display_name": str}]
            evidence_reviews: 증거 리뷰 [{"excerpt": str, "label": str, "reason": str}]
            next_questions: 다음 질문 후보
            user_message: 사용자 메시지
            
        Returns:
            LLM context JSON
        """
        logger.info(f"LLM context 생성: {session_id}, factors={len(top_factors)}, reviews={len(evidence_reviews)}")
        
        context = {
            "meta": {
                "run_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "version": self.version,
                "category": category,
                "product_name": product_name
            },
            "top_factors": [
                {
                    "factor_key": f["factor_key"],
                    "score": f["score"],
                    "display_name": f.get("display_name", f["factor_key"])
                }
                for f in top_factors
            ],
            "evidence_reviews": [
                {
                    "excerpt": r["excerpt"],
                    "label": r.get("label", "RELEVANT"),
                    "reason": r.get("reason", "")
                }
                for r in evidence_reviews
            ],
            "next_questions_to_ask": next_questions,
            "user_context": {
                "last_message": user_message
            },
            "safety_rules": self._get_safety_rules()
        }
        
        return context
    
    def build_prompt(
        self,
        llm_context: Dict[str, Any],
        instruction: str = "사용자의 구매 고민을 분석하고 적절한 질문을 생성하세요."
    ) -> str:
        """LLM 프롬프트 텍스트 생성
        
        Args:
            llm_context: build_llm_context() 결과
            instruction: 시스템 지시사항
            
        Returns:
            프롬프트 텍스트
        """
        import json
        
        prompt = f"""# Task
{instruction}

# Context
{json.dumps(llm_context, ensure_ascii=False, indent=2)}

# Instructions
1. 상위 factors를 바탕으로 사용자의 우선순위를 파악하세요
2. evidence_reviews를 참고하여 제품의 장단점을 이해하세요
3. next_questions에서 적절한 질문을 선택하거나, 새로운 질문을 생성하세요
4. 사용자에게 도움이 되는 응답을 생성하세요

# Safety Rules
{chr(10).join('- ' + rule for rule in llm_context.get('safety_rules', []))}
"""
        
        return prompt
    
    def _get_safety_rules(self) -> List[str]:
        """안전 규칙 반환"""
        return [
            "제품에 대한 허위 정보를 생성하지 마세요",
            "리뷰에 없는 내용을 추가하지 마세요",
            "사용자를 특정 제품 구매로 유도하지 마세요",
            "개인정보를 요구하거나 저장하지 마세요",
            "리뷰 작성자를 특정하지 마세요"
        ]
    
    def format_analysis_response(
        self,
        llm_response: str,
        top_factors: List[Dict[str, Any]],
        evidence_count: int
    ) -> Dict[str, Any]:
        """LLM 응답을 분석 결과로 포맷팅
        
        Args:
            llm_response: LLM 원본 응답
            top_factors: 상위 factors
            evidence_count: 증거 리뷰 개수
            
        Returns:
            포맷된 분석 결과
        """
        return {
            "message": llm_response,
            "top_priorities": [
                {
                    "name": f.get("display_name", f["factor_key"]),
                    "score": f["score"]
                }
                for f in top_factors[:3]
            ],
            "evidence_count": evidence_count,
            "timestamp": datetime.now().isoformat()
        }
