"""Backend package for ReviewLens"""

# Re-export commonly used components for backward compatibility
from .dialogue.reg_store import load_csvs, parse_factors, Factor
from .dialogue.ingest import normalize, sha1_of_text, dedupe_reviews
from .dialogue.sensor import score_text_against_factor, compute_review_factor_scores, select_top_factors_from_question
from .dialogue.retrieval import retrieve_evidence_reviews
from .dialogue.prompt_builder import write_llm_context, write_debug_report
from .dialogue.dialogue import DialogueSession, BotTurn

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
