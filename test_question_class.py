#!/usr/bin/env python3
"""Test Question class implementation"""

from backend.pipeline.reg_store import Question, parse_questions, load_csvs
from pathlib import Path

# Load CSVs
data_dir = Path("backend/data")
_, _, questions_df = load_csvs(data_dir)

# Parse questions
questions = parse_questions(questions_df)

print(f"✅ Successfully parsed {len(questions)} questions")
print(f"\nSample questions:")
for q in questions[:5]:
    print(f"  Q{q.question_id} (Factor ID: {q.factor_id}, Key: {q.factor_key})")
    print(f"    {q.question_text}")
    print(f"    Type: {q.answer_type}, Choices: {q.choices or '(none)'}")
    print()

# Test filtering
print(f"Questions for factor_id=1: {len([q for q in questions if q.factor_id == 1])}")
print(f"Questions for factor_key='water_control': {len([q for q in questions if q.factor_key == 'water_control'])}")
