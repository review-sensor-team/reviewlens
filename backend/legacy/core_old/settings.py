"""
애플리케이션 설정
"""
import os
from pathlib import Path
from typing import Literal
from dotenv import load_dotenv

# .env 파일 로드
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# 프로젝트 루트 디렉토리
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# LLM 설정
LLM_PROVIDER: Literal["gemini", "openai", "claude"] = os.getenv("LLM_PROVIDER", "openai")

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# LLM 모델 설정
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

# LLM 파라미터
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2000"))

# 모니터링 설정
MONITORING_MODE: Literal["local", "docker", "cloud"] = os.getenv("MONITORING_MODE", "local")
# local: 로컬 바이너리 Prometheus (개발용)
# docker: Docker Compose Prometheus (스테이징/프로덕션)
# cloud: CloudWatch/Grafana Cloud (프로덕션 대규모)

# CORS 설정
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# 로깅 설정
LOG_DIR = BASE_DIR / "logs"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
