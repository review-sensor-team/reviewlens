#!/usr/bin/env python3
"""
LLM 클라이언트 리팩토링 스크립트
프롬프트 로직을 Base 클래스로 통합하고, 각 클라이언트는 API 호출만 담당
"""

import os
from pathlib import Path

# Base 클래스 코드
BASE_CODE = '''"""
LLM 클라이언트 베이스 클래스
"""
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class PromptBuilder:
    """프롬프트 구성 유틸리티 - 모든 LLM 클라이언트에서 공통 사용"""
    
    @staticmethod
    def build_system_prompt() -> str:
        """시스템 프롬프트 생성"""
        return """당신은 제품 리뷰 분석 전문가입니다. 
구매자들의 후회 요인을 분석하여 실용적이고 구체적인 조언을 제공합니다.
친근하지만 전문적인 톤으로, JSON 형식의 구조화된 분석 결과를 작성합니다."""
    
    @staticmethod
    def build_user_prompt(
        top_factors: List[tuple],
        evidence_reviews: List[Dict[str, Any]],
        total_turns: int,
        category_name: str,
        product_name: str,
        dialogue_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """유저 프롬프트 생성"""
        # 상위 요인 정리
        factors_text = "\\n".join([
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
            dialogue_text = "\\n".join(dialogue_lines)
        
        # 증거 리뷰 정리
        evidence_text = ""
        for i, rev in enumerate(evidence_reviews, 1):
            label = rev.get('label', 'NEU')
            rating = rev.get('rating', 0)
            excerpt = rev.get('excerpt', '')
            evidence_text += f"{i}. [{label}] {rating}점 - {excerpt}\\n"
        
        # User Prompt 구성
        user_prompt_parts = [
            "**제품 정보**",
            f"- 카테고리: {category_name}",
            f"- 제품명: {product_name}",
            f"- 분석 대화 턴: {total_turns}턴",
            ""
        ]
        
        if dialogue_text:
            user_prompt_parts.extend([
                "**대화 내용**",
                dialogue_text,
                ""
            ])
        
        user_prompt_parts.extend([
            "**주요 후회 요인 (상위 5개)**",
            factors_text,
            "",
            f"**증거 리뷰 전체 ({len(evidence_reviews)}개)**",
            evidence_text,
            "",
            "다음 JSON 형식으로 최종 분석 결과를 작성해주세요:",
            "{",
            '  "summary": "핵심 후회 요인 설명 (2-3문장)",',
            '  "key_findings": [',
            '    {',
            '      "factor": "요인명",',
            '      "risk_level": "high|mid|low",',
            '      "what_users_say": "구매자들이 말하는 내용 (2-3문장)"',
            '    }',
            '  ],',
            '  "balanced_view": {',
            '    "pros": [{"point": "장점"}],',
            '    "cons": [{"point": "단점"}],',
            '    "mixed": [{"point": "상황에 따라 다름"}]',
            '  },',
            '  "decision_rule": {',
            '    "if_buy": ["구매를 고려해도 좋은 경우"],',
            '    "if_hold": ["보류가 나은 경우"]',
            '  },',
            '  "final_recommendation": "구매|보류|조건부 추천",',
            '  "one_line_tip": "한 줄 조언"',
            "}",
            "",
            "**중요**: 반드시 유효한 JSON 형식으로만 응답하세요. 추가 설명이나 마크다운은 포함하지 마세요."
        ])
        
        return "\\n".join(user_prompt_parts)
    
    @staticmethod
    def get_fallback_summary(
        top_factors: List[tuple],
        category_name: str,
        product_name: str
    ) -> str:
        """API 실패 시 기본 요약"""
        factors_text = ", ".join([f"{key}" for key, _ in top_factors[:3]])
        
        return f"""{{
  "summary": "{product_name}의 주요 후회 요인은 {factors_text}입니다.",
  "key_findings": [
    {{
      "factor": "{top_factors[0][0] if top_factors else '알 수 없음'}",
      "risk_level": "mid",
      "what_users_say": "구매자들이 이 부분에서 아쉬움을 느끼고 있습니다."
    }}
  ],
  "balanced_view": {{
    "pros": [{{"point": "전반적인 품질은 양호합니다"}}],
    "cons": [{{"point": "{factors_text} 관련 불만이 있습니다"}}],
    "mixed": []
  }},
  "decision_rule": {{
    "if_buy": ["해당 요인이 본인에게 중요하지 않은 경우"],
    "if_hold": ["해당 요인이 본인에게 중요한 경우"]
  }},
  "final_recommendation": "조건부 추천",
  "one_line_tip": "후회 요인을 미리 알고 구매하면 실망을 줄일 수 있습니다!"
}}"""


class BaseLLMClient(ABC):
    """LLM 클라이언트 베이스 클래스 - 템플릿 메서드 패턴 사용"""
    
    def __init__(self, api_key: str, model: str, temperature: float, max_tokens: int):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    def generate_summary(
        self, 
        top_factors: List[tuple],
        evidence_reviews: List[Dict[str, Any]],
        total_turns: int,
        category_name: str,
        product_name: str = "이 제품",
        dialogue_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        최종 분석 요약 생성 (템플릿 메서드)
        
        Args:
            top_factors: [(factor_key, score), ...] 상위 후회 요인
            evidence_reviews: 증거 리뷰 리스트
            total_turns: 총 대화 턴 수
            category_name: 제품 카테고리명
            product_name: 제품명
            dialogue_history: 대화 내역
            
        Returns:
            str: 생성된 분석 요약 (JSON 형식)
        """
        # 프롬프트 구성 (공통 로직)
        system_prompt = PromptBuilder.build_system_prompt()
        user_prompt = PromptBuilder.build_user_prompt(
            top_factors, evidence_reviews, total_turns,
            category_name, product_name, dialogue_history
        )
        
        # 프롬프트 저장 (OpenAI만)
        if self.__class__.__name__ == "OpenAIClient":
            self._save_prompt(system_prompt, user_prompt)
        
        # API 호출 (각 구현체에서 정의)
        try:
            return self._call_api(system_prompt, user_prompt)
        except Exception as e:
            logger.error(f"{self.__class__.__name__} API 호출 실패: {e}")
            return PromptBuilder.get_fallback_summary(top_factors, category_name, product_name)
    
    @abstractmethod
    def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        """
        실제 LLM API 호출 (각 구현체에서 구현)
        
        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 유저 프롬프트
            
        Returns:
            str: LLM 응답
        """
        pass
    
    def _save_prompt(self, system_prompt: str, user_prompt: str):
        """프롬프트 저장 (OpenAI 전용, 다른 클라이언트는 override 불필요)"""
        pass
'''

# OpenAI 클라이언트 코드
OPENAI_CODE = '''"""
OpenAI LLM 클라이언트
"""
import logging
from .llm_base import BaseLLMClient

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLMClient):
    """OpenAI API 클라이언트"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", temperature: float = 0.7, max_tokens: int = 2000):
        super().__init__(api_key, model, temperature, max_tokens)
        
        if not api_key:
            logger.warning("OpenAI API key가 설정되지 않았습니다.")
            self.client = None
        else:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key)
                logger.info(f"OpenAI 클라이언트 초기화 완료: model={model}")
            except Exception as e:
                logger.error(f"OpenAI 클라이언트 초기화 실패: {e}")
                self.client = None
    
    def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        """OpenAI API 호출"""
        if not self.client:
            raise RuntimeError("OpenAI 클라이언트가 초기화되지 않았습니다")
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        summary = response.choices[0].message.content.strip()
        logger.info(f"OpenAI 요약 생성 완료: {len(summary)}자")
        return summary
    
    def _save_prompt(self, system_prompt: str, user_prompt: str):
        """프롬프트를 파일로 저장"""
        try:
            from datetime import datetime
            from pathlib import Path
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = Path("out")
            out_dir.mkdir(exist_ok=True)
            
            prompt_file = out_dir / f"llm_prompt_{timestamp}.txt"
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\\n")
                f.write("SYSTEM PROMPT\\n")
                f.write("=" * 80 + "\\n")
                f.write(system_prompt)
                f.write("\\n\\n")
                f.write("=" * 80 + "\\n")
                f.write("USER PROMPT\\n")
                f.write("=" * 80 + "\\n")
                f.write(user_prompt)
                f.write("\\n")
            
            logger.info(f"[LLM 프롬프트 저장] {prompt_file}")
        except Exception as e:
            logger.error(f"프롬프트 저장 실패: {e}")
'''

# Gemini 클라이언트 코드
GEMINI_CODE = '''"""
Gemini LLM 클라이언트
"""
import logging
from .llm_base import BaseLLMClient

logger = logging.getLogger(__name__)


class GeminiClient(BaseLLMClient):
    """Google Gemini API 클라이언트"""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash", temperature: float = 0.7, max_tokens: int = 2000):
        super().__init__(api_key, model, temperature, max_tokens)
        
        if not api_key:
            logger.warning("Gemini API key가 설정되지 않았습니다.")
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
    
    def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        """Gemini API 호출"""
        if not self.client:
            raise RuntimeError("Gemini 클라이언트가 초기화되지 않았습니다")
        
        # Gemini는 system_prompt와 user_prompt를 합쳐서 전달
        combined_prompt = f"{system_prompt}\\n\\n{user_prompt}"
        
        response = self.client.generate_content(
            combined_prompt,
            generation_config={
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
            }
        )
        
        summary = response.text.strip()
        logger.info(f"Gemini 요약 생성 완료: {len(summary)}자")
        return summary
'''

# Claude 클라이언트 코드
CLAUDE_CODE = '''"""
Anthropic Claude LLM 클라이언트
"""
import logging
from .llm_base import BaseLLMClient

logger = logging.getLogger(__name__)


class ClaudeClient(BaseLLMClient):
    """Anthropic Claude API 클라이언트"""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022", temperature: float = 0.7, max_tokens: int = 2000):
        super().__init__(api_key, model, temperature, max_tokens)
        
        if not api_key:
            logger.warning("Anthropic API key가 설정되지 않았습니다.")
            self.client = None
        else:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=api_key)
                logger.info(f"Claude 클라이언트 초기화 완료: model={model}")
            except Exception as e:
                logger.error(f"Claude 클라이언트 초기화 실패: {e}")
                self.client = None
    
    def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        """Claude API 호출"""
        if not self.client:
            raise RuntimeError("Claude 클라이언트가 초기화되지 않았습니다")
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        summary = response.content[0].text.strip()
        logger.info(f"Claude 요약 생성 완료: {len(summary)}자")
        return summary
'''

def main():
    """리팩토링 실행"""
    llm_dir = Path(__file__).parent / "backend" / "llm"
    
    # 파일 작성
    files = {
        "llm_base.py": BASE_CODE,
        "llm_openai.py": OPENAI_CODE,
        "llm_gemini.py": GEMINI_CODE,
        "llm_claude.py": CLAUDE_CODE
    }
    
    for filename, code in files.items():
        filepath = llm_dir / filename
        print(f"✍️  {filename} 작성 중...")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        print(f"✅ {filename} 완료")
    
    print("\n🎉 LLM 클라이언트 리팩토링 완료!")
    print("📝 변경 사항:")
    print("  - PromptBuilder 클래스를 llm_base.py에 추가")
    print("  - 각 LLM 클라이언트는 _call_api() 메서드만 구현")
    print("  - 프롬프트 구성 로직이 중복 제거됨")
    print("  - 템플릿 메서드 패턴 적용")

if __name__ == "__main__":
    main()
