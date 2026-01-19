"""Data Source Abstraction

파일 기반과 DB 기반 데이터 소스를 추상화하여 점진적 마이그레이션 지원
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class DataSource(ABC):
    """데이터 소스 추상 인터페이스
    
    파일 시스템과 데이터베이스 간 전환을 위한 공통 인터페이스
    """
    
    @abstractmethod
    def get_reviews_by_category(
        self,
        category: str,
        vendor: Optional[str] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """카테고리별 리뷰 조회"""
        pass
    
    @abstractmethod
    def get_reviews_by_product(
        self,
        product_id: str,
        vendor: Optional[str] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """제품별 리뷰 조회"""
        pass
    
    @abstractmethod
    def get_factors_by_category(
        self,
        category: str,
        version: Optional[str] = None
    ) -> pd.DataFrame:
        """카테고리별 요인(factor) 조회"""
        pass
    
    @abstractmethod
    def get_questions_by_category(
        self,
        category: str,
        version: Optional[str] = None
    ) -> pd.DataFrame:
        """카테고리별 질문 조회"""
        pass
    
    @abstractmethod
    def save_reviews(
        self,
        reviews_df: pd.DataFrame,
        metadata: Dict[str, Any]
    ) -> bool:
        """리뷰 저장"""
        pass
    
    @abstractmethod
    def save_analysis_result(
        self,
        session_id: str,
        result_data: Dict[str, Any]
    ) -> bool:
        """분석 결과 저장"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """데이터 소스 상태 확인"""
        pass


class FileDataSource(DataSource):
    """파일 기반 데이터 소스
    
    기존 CSV/JSON 파일 시스템과 호환
    """
    
    def __init__(
        self,
        data_dir: Union[str, Path],
        file_format: str = "json"
    ):
        self.data_dir = Path(data_dir)
        self.file_format = file_format.lower()
        
        # 기존 로더 재사용
        from ..loaders.loader_factory import ReviewLoaderFactory
        self.review_loader = ReviewLoaderFactory.create(
            data_dir=self.data_dir,
            file_format=self.file_format
        )
        
        logger.info(f"파일 데이터 소스 초기화: {self.data_dir}, 포맷={self.file_format}")
    
    def get_reviews_by_category(
        self,
        category: str,
        vendor: Optional[str] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """카테고리별 리뷰 조회 (파일)"""
        df = self.review_loader.load_by_category(
            category=category,
            vendor=vendor,
            latest=True
        )
        
        if df is None:
            return pd.DataFrame()
        
        if limit:
            df = df.head(limit)
        
        return df
    
    def get_reviews_by_product(
        self,
        product_id: str,
        vendor: Optional[str] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """제품별 리뷰 조회 (파일)"""
        df = self.review_loader.load_by_product(
            product_id=product_id,
            vendor=vendor,
            latest=True
        )
        
        if df is None:
            return pd.DataFrame()
        
        if limit:
            df = df.head(limit)
        
        return df
    
    def get_factors_by_category(
        self,
        category: str,
        version: Optional[str] = None
    ) -> pd.DataFrame:
        """카테고리별 요인 조회 (파일)"""
        from ...adapters.persistence.reg.store import load_csvs
        
        _, factors_df, _ = load_csvs(self.data_dir)
        
        # 카테고리 필터링
        if 'category' in factors_df.columns:
            factors_df = factors_df[factors_df['category'] == category]
        
        return factors_df
    
    def get_questions_by_category(
        self,
        category: str,
        version: Optional[str] = None
    ) -> pd.DataFrame:
        """카테고리별 질문 조회 (파일)"""
        from ...adapters.persistence.reg.store import load_csvs
        
        _, _, questions_df = load_csvs(self.data_dir)
        
        # 카테고리 필터링 (factors에서 category 매핑)
        _, factors_df, _ = load_csvs(self.data_dir)
        if 'category' in factors_df.columns:
            category_factors = factors_df[
                factors_df['category'] == category
            ]['factor_key'].unique()
            
            questions_df = questions_df[
                questions_df['factor_key'].isin(category_factors)
            ]
        
        return questions_df
    
    def save_reviews(
        self,
        reviews_df: pd.DataFrame,
        metadata: Dict[str, Any]
    ) -> bool:
        """리뷰 저장 (파일)"""
        try:
            from ..storage.csv_storage import CSVStorage
            storage = CSVStorage(self.data_dir, self.file_format)
            
            storage.save_reviews(
                reviews_df=reviews_df,
                vendor=metadata.get('vendor', 'unknown'),
                product_id=metadata.get('product_id', 'unknown')
            )
            return True
        except Exception as e:
            logger.error(f"리뷰 저장 실패 (파일): {e}", exc_info=True)
            return False
    
    def save_analysis_result(
        self,
        session_id: str,
        result_data: Dict[str, Any]
    ) -> bool:
        """분석 결과 저장 (파일)"""
        try:
            from ..persistence.session_repo import SessionPersistence
            persistence = SessionPersistence(self.data_dir)
            persistence.save_session(session_id, result_data)
            return True
        except Exception as e:
            logger.error(f"분석 결과 저장 실패 (파일): {e}", exc_info=True)
            return False
    
    def health_check(self) -> bool:
        """파일 시스템 상태 확인"""
        return self.data_dir.exists() and self.data_dir.is_dir()


class DatabaseDataSource(DataSource):
    """DB 기반 데이터 소스
    
    PostgreSQL 데이터베이스 사용
    """
    
    def __init__(self, connection_pool):
        """
        Args:
            connection_pool: DatabaseConnectionPool 인스턴스
        """
        if connection_pool is None:
            raise RuntimeError("DatabaseConnectionPool이 필요합니다. psycopg가 설치되어 있는지 확인하세요.")
        self.pool = connection_pool
        logger.info("DB 데이터 소스 초기화")
    
    def get_reviews_by_category(
        self,
        category: str,
        vendor: Optional[str] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """카테고리별 리뷰 조회 (DB)"""
        query = """
            SELECT 
                r.review_pk,
                r.external_review_id as review_id,
                r.rating,
                r.text,
                r.created_at,
                r.meta,
                p.product_name,
                c.category_slug,
                s.shop_key as vendor
            FROM review r
            LEFT JOIN product p ON r.product_id = p.product_id
            LEFT JOIN category c ON r.category_id = c.category_id
            LEFT JOIN shop s ON p.shop_id = s.shop_id
            WHERE c.category_slug = %(category)s
        """
        
        params = {"category": category}
        
        if vendor:
            query += " AND s.shop_key = %(vendor)s"
            params["vendor"] = vendor
        
        query += " ORDER BY r.created_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        try:
            results = self.pool.execute_query(query, params, fetch="all")
            return pd.DataFrame(results) if results else pd.DataFrame()
        except Exception as e:
            logger.error(f"리뷰 조회 실패 (DB): {e}", exc_info=True)
            return pd.DataFrame()
    
    def get_reviews_by_product(
        self,
        product_id: str,
        vendor: Optional[str] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """제품별 리뷰 조회 (DB)"""
        query = """
            SELECT 
                r.review_pk,
                r.external_review_id as review_id,
                r.rating,
                r.text,
                r.created_at,
                r.meta,
                p.product_name,
                c.category_slug,
                s.shop_key as vendor
            FROM review r
            LEFT JOIN product p ON r.product_id = p.product_id
            LEFT JOIN category c ON r.category_id = c.category_id
            LEFT JOIN shop s ON p.shop_id = s.shop_id
            WHERE p.external_product_id = %(product_id)s
        """
        
        params = {"product_id": product_id}
        
        if vendor:
            query += " AND s.shop_key = %(vendor)s"
            params["vendor"] = vendor
        
        query += " ORDER BY r.created_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        try:
            results = self.pool.execute_query(query, params, fetch="all")
            return pd.DataFrame(results) if results else pd.DataFrame()
        except Exception as e:
            logger.error(f"리뷰 조회 실패 (DB): {e}", exc_info=True)
            return pd.DataFrame()
    
    def get_factors_by_category(
        self,
        category: str,
        version: Optional[str] = None
    ) -> pd.DataFrame:
        """카테고리별 요인 조회 (DB)"""
        query = """
            SELECT 
                rf.reg_factor_id,
                rf.factor_key,
                rf.display_name,
                rf.weight,
                rf.anchor_terms,
                rf.context_terms,
                rf.negation_terms,
                rs.version_tag,
                c.category_slug,
                c.category_name
            FROM reg_factor rf
            JOIN reg_set rs ON rf.reg_set_id = rs.reg_set_id
            JOIN category c ON rs.category_id = c.category_id
            WHERE c.category_slug = %(category)s
        """
        
        params = {"category": category}
        
        if version:
            query += " AND rs.version_tag = %(version)s"
            params["version"] = version
        else:
            # 최신 버전 선택
            query += """
                AND rs.reg_set_id = (
                    SELECT reg_set_id 
                    FROM reg_set 
                    WHERE category_id = c.category_id 
                    ORDER BY created_at DESC 
                    LIMIT 1
                )
            """
        
        try:
            results = self.pool.execute_query(query, params, fetch="all")
            return pd.DataFrame(results) if results else pd.DataFrame()
        except Exception as e:
            logger.error(f"요인 조회 실패 (DB): {e}", exc_info=True)
            return pd.DataFrame()
    
    def get_questions_by_category(
        self,
        category: str,
        version: Optional[str] = None
    ) -> pd.DataFrame:
        """카테고리별 질문 조회 (DB)"""
        query = """
            SELECT 
                rq.reg_question_id as question_id,
                rq.factor_key,
                rq.question_text,
                rq.priority,
                rq.is_active,
                rs.version_tag,
                c.category_slug
            FROM reg_question rq
            JOIN reg_set rs ON rq.reg_set_id = rs.reg_set_id
            JOIN category c ON rs.category_id = c.category_id
            WHERE c.category_slug = %(category)s
            AND rq.is_active = TRUE
        """
        
        params = {"category": category}
        
        if version:
            query += " AND rs.version_tag = %(version)s"
            params["version"] = version
        else:
            query += """
                AND rs.reg_set_id = (
                    SELECT reg_set_id 
                    FROM reg_set 
                    WHERE category_id = c.category_id 
                    ORDER BY created_at DESC 
                    LIMIT 1
                )
            """
        
        query += " ORDER BY rq.priority ASC"
        
        try:
            results = self.pool.execute_query(query, params, fetch="all")
            return pd.DataFrame(results) if results else pd.DataFrame()
        except Exception as e:
            logger.error(f"질문 조회 실패 (DB): {e}", exc_info=True)
            return pd.DataFrame()
    
    def save_reviews(
        self,
        reviews_df: pd.DataFrame,
        metadata: Dict[str, Any]
    ) -> bool:
        """리뷰 저장 (DB)"""
        try:
            # ingestion_job 먼저 생성
            job_query = """
                INSERT INTO ingestion_job (
                    shop_id, product_id, category_id,
                    source_type, source_ref, meta
                )
                VALUES (
                    (SELECT shop_id FROM shop WHERE shop_key = %(vendor)s),
                    (SELECT product_id FROM product WHERE external_product_id = %(product_id)s),
                    (SELECT category_id FROM category WHERE category_slug = %(category)s),
                    %(source_type)s,
                    %(source_ref)s,
                    %(meta)s::jsonb
                )
                RETURNING job_id
            """
            
            job_params = {
                "vendor": metadata.get("vendor"),
                "product_id": metadata.get("product_id"),
                "category": metadata.get("category"),
                "source_type": metadata.get("source_type", "file"),
                "source_ref": metadata.get("source_ref", ""),
                "meta": "{}"
            }
            
            with self.pool.get_cursor(commit=False) as cur:
                cur.execute(job_query, job_params)
                job_id = cur.fetchone()["job_id"]
                
                # 리뷰 배치 삽입
                review_query = """
                    INSERT INTO review (
                        job_id, product_id, category_id,
                        external_review_id, rating, text, created_at,
                        norm_text, norm_sha1
                    )
                    VALUES (
                        %(job_id)s,
                        (SELECT product_id FROM product WHERE external_product_id = %(product_id)s),
                        (SELECT category_id FROM category WHERE category_slug = %(category)s),
                        %(review_id)s,
                        %(rating)s,
                        %(text)s,
                        %(created_at)s,
                        %(norm_text)s,
                        %(norm_sha1)s
                    )
                    ON CONFLICT (job_id, external_review_id) DO NOTHING
                """
                
                import hashlib
                for _, row in reviews_df.iterrows():
                    text = str(row.get("text", ""))
                    norm_text = text.lower().strip()
                    norm_sha1 = hashlib.sha1(norm_text.encode()).hexdigest()
                    
                    review_params = {
                        "job_id": job_id,
                        "product_id": metadata.get("product_id"),
                        "category": metadata.get("category"),
                        "review_id": row.get("review_id", ""),
                        "rating": row.get("rating"),
                        "text": text,
                        "created_at": row.get("created_at"),
                        "norm_text": norm_text,
                        "norm_sha1": norm_sha1
                    }
                    
                    cur.execute(review_query, review_params)
                
                cur.connection.commit()
            
            logger.info(f"리뷰 {len(reviews_df)}건 저장 완료 (DB)")
            return True
            
        except Exception as e:
            logger.error(f"리뷰 저장 실패 (DB): {e}", exc_info=True)
            return False
    
    def save_analysis_result(
        self,
        session_id: str,
        result_data: Dict[str, Any]
    ) -> bool:
        """분석 결과 저장 (DB)"""
        try:
            with self.pool.get_cursor(commit=True) as cur:
                # analysis_run 저장
                run_query = """
                    INSERT INTO analysis_run (
                        session_id, reg_set_id, top_factors,
                        llm_context, llm_prompt, model_name, model_meta
                    )
                    VALUES (
                        %(session_id)s::uuid,
                        %(reg_set_id)s,
                        %(top_factors)s::jsonb,
                        %(llm_context)s::jsonb,
                        %(llm_prompt)s,
                        %(model_name)s,
                        %(model_meta)s::jsonb
                    )
                    RETURNING run_id
                """
                
                import json
                run_params = {
                    "session_id": session_id,
                    "reg_set_id": result_data.get("reg_set_id"),
                    "top_factors": json.dumps(result_data.get("top_factors", [])),
                    "llm_context": json.dumps(result_data.get("llm_context", {})),
                    "llm_prompt": result_data.get("llm_prompt", ""),
                    "model_name": result_data.get("model_name", ""),
                    "model_meta": json.dumps(result_data.get("model_meta", {}))
                }
                
                cur.execute(run_query, run_params)
                run_id = cur.fetchone()["run_id"]
                
                logger.info(f"분석 결과 저장 완료 (DB): run_id={run_id}")
                return True
                
        except Exception as e:
            logger.error(f"분석 결과 저장 실패 (DB): {e}", exc_info=True)
            return False
    
    def health_check(self) -> bool:
        """DB 연결 상태 확인"""
        return self.pool.health_check()
