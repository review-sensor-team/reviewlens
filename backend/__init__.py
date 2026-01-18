"""Backend package for ReviewLens"""

# Re-export commonly used components for backward compatibility
from .app.adapters.persistence.reg.store import load_csvs, parse_factors, Factor
from .app.domain.rules.review.normalize import normalize_review, sha1_of_text, dedupe_reviews
from .app.domain.rules.review.scoring import score_text_against_factor, compute_review_factor_scores, select_top_factors_from_question
from .app.domain.rules.review.retrieval import retrieve_evidence_reviews
from .app.usecases.dialogue.session import DialogueSession, BotTurn

__all__ = [
    # reg_store
    "load_csvs",
    "parse_factors",
    "Factor",
    # ingest
    "normalize",
    "sha1_of_text",
    "dedupe_reviews",
    # sensor
    "score_text_against_factor",
    "compute_review_factor_scores",
    "select_top_factors_from_question",
    # retrieval
    "retrieve_evidence_reviews",
    # prompt_builder
    "write_llm_context",
    "write_debug_report",
    # dialogue
    "DialogueSession",
    "BotTurn",
]
