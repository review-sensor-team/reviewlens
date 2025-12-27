"""Session storage service"""
from pathlib import Path
from typing import Dict, Optional
import uuid

from backend.pipeline.dialogue import DialogueSession


class SessionStore:
    """세션 저장소 (메모리 기반)"""
    
    def __init__(self):
        self._sessions: Dict[str, DialogueSession] = {}
    
    def create_session(self, category: str, data_dir: Path) -> str:
        """새 세션 생성"""
        session_id = str(uuid.uuid4())
        session = DialogueSession(category=category, data_dir=data_dir)
        self._sessions[session_id] = session
        return session_id
    
    def get_session(self, session_id: str) -> Optional[DialogueSession]:
        """세션 조회"""
        return self._sessions.get(session_id)
    
    def delete_session(self, session_id: str):
        """세션 삭제"""
        if session_id in self._sessions:
            del self._sessions[session_id]
