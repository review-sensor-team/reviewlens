"""세션 데이터 영속화 (JSON 파일 기반)"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import pandas as pd

logger = logging.getLogger("session.persistence")


class SessionPersistence:
    """세션 데이터를 JSON 파일로 저장/로드"""
    
    def __init__(self, storage_dir: Path = None):
        """
        Args:
            storage_dir: 세션 파일을 저장할 디렉토리 (기본: out/sessions)
        """
        if storage_dir is None:
            storage_dir = Path("out/sessions")
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"[세션 저장소] 디렉토리: {self.storage_dir.absolute()}")
    
    def _get_session_path(self, session_id: str) -> Path:
        """세션 ID로 파일 경로 생성"""
        return self.storage_dir / f"{session_id}.json"
    
    def save_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """세션 데이터를 JSON 파일로 저장
        
        Args:
            session_id: 세션 ID
            session_data: 저장할 세션 데이터
                - dialogue: Dialogue 객체
                - product_url: 상품 URL
                - product_name: 상품명
                - reviews_df: 리뷰 DataFrame
                - category: 카테고리
                - created_at: 생성 시간
        
        Returns:
            저장 성공 여부
        """
        try:
            file_path = self._get_session_path(session_id)
            
            # 저장할 데이터 구조화
            save_data = {
                "session_id": session_id,
                "product_url": session_data.get("product_url"),
                "product_name": session_data.get("product_name"),
                "category": session_data.get("category"),
                "llm_config": session_data.get("llm_config"),
                "created_at": session_data.get("created_at", datetime.now().isoformat()),
                "updated_at": datetime.now().isoformat(),
            }
            
            # Dialogue 객체 정보 저장
            dialogue = session_data.get("dialogue")
            if dialogue:
                save_data["dialogue_state"] = {
                    "turn_count": dialogue.turn_count,
                    "stability_hits": dialogue.stability_hits,
                    "cumulative_scores": dialogue.cumulative_scores,
                    "prev_top3": dialogue.prev_top3,
                    "dialogue_history": dialogue.dialogue_history,
                }
            
            # 리뷰 데이터 저장 (DataFrame -> dict)
            reviews_df = session_data.get("reviews_df")
            if reviews_df is not None and not reviews_df.empty:
                save_data["reviews"] = reviews_df.to_dict(orient="records")
            
            # 파일 저장
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[세션 저장 완료] {session_id} -> {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"[세션 저장 실패] {session_id}: {str(e)}", exc_info=True)
            return False
    
    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """JSON 파일에서 세션 데이터 로드
        
        Args:
            session_id: 세션 ID
        
        Returns:
            세션 데이터 또는 None
        """
        try:
            file_path = self._get_session_path(session_id)
            
            if not file_path.exists():
                logger.debug(f"[세션 파일 없음] {session_id}")
                return None
            
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # DataFrame 복원
            if "reviews" in data and data["reviews"]:
                data["reviews_df"] = pd.DataFrame(data["reviews"])
                del data["reviews"]
            else:
                data["reviews_df"] = pd.DataFrame()
            
            logger.info(f"[세션 로드 완료] {session_id}: {len(data.get('reviews_df', pd.DataFrame()))}건 리뷰")
            return data
            
        except Exception as e:
            logger.error(f"[세션 로드 실패] {session_id}: {str(e)}", exc_info=True)
            return None
    
    def delete_session(self, session_id: str) -> bool:
        """세션 파일 삭제
        
        Args:
            session_id: 세션 ID
        
        Returns:
            삭제 성공 여부
        """
        try:
            file_path = self._get_session_path(session_id)
            
            if file_path.exists():
                file_path.unlink()
                logger.info(f"[세션 삭제 완료] {session_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"[세션 삭제 실패] {session_id}: {str(e)}", exc_info=True)
            return False
    
    def list_sessions(self) -> List[str]:
        """저장된 모든 세션 ID 목록 반환"""
        try:
            session_files = self.storage_dir.glob("*.json")
            session_ids = [f.stem for f in session_files]
            logger.info(f"[세션 목록] {len(session_ids)}개 세션 발견")
            return session_ids
            
        except Exception as e:
            logger.error(f"[세션 목록 조회 실패] {str(e)}", exc_info=True)
            return []
    
    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """오래된 세션 파일 정리
        
        Args:
            max_age_hours: 유지할 최대 시간 (시간)
        
        Returns:
            삭제된 세션 수
        """
        try:
            deleted_count = 0
            now = datetime.now()
            
            for session_file in self.storage_dir.glob("*.json"):
                try:
                    with open(session_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    # updated_at 또는 created_at 확인
                    timestamp_str = data.get("updated_at") or data.get("created_at")
                    if timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str)
                        age_hours = (now - timestamp).total_seconds() / 3600
                        
                        if age_hours > max_age_hours:
                            session_file.unlink()
                            deleted_count += 1
                            logger.info(f"[오래된 세션 삭제] {session_file.stem} (나이: {age_hours:.1f}시간)")
                
                except Exception as e:
                    logger.warning(f"[세션 파일 확인 실패] {session_file}: {str(e)}")
                    continue
            
            if deleted_count > 0:
                logger.info(f"[세션 정리 완료] {deleted_count}개 세션 삭제")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"[세션 정리 실패] {str(e)}", exc_info=True)
            return 0
